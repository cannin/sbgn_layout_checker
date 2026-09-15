#!/usr/bin/env python3
"""Benchmark many fCoSE layouts against original SBGN checker counts."""

import argparse
import json
import math
import os
import statistics
import subprocess
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from relayout_sbgn_fcose import (
    FCOSE_SCRIPT,
    Placement,
    apply_placements,
    fcose_payload,
    reroute_arcs,
)
from render_sbgn_py.renderer import Arc, Glyph, parse_sbgnml

from sbgn_layout_checker.analyze_sbgn_layout import (
    analyze_sbgn_file,
    build_renderer_lookups,
    checked_node_rectangles,
    collect_sbgn_files,
    find_arc_crossings,
    find_arc_node_overlaps,
    resolve_arc_paths,
)

DEFAULT_INPUT_DIRECTORY = Path("examples/sbgn_examples")
DEFAULT_REPORT_PATH = Path("reports/fcose_1000_trials_report.md")
DEFAULT_TRIAL_COUNT = 1000
DEFAULT_SEED_START = 20261001
DEFAULT_CHUNK_SIZE = 25
DEFAULT_WORKERS = min(8, os.cpu_count() or 4)


@dataclass(frozen=True)
class TrialCounts:
    """Aggregate checker counts for one fCoSE seed across all diagrams."""

    seed: int
    arc_crossings: int
    arc_node_overlaps: int


def parse_batch_placements(
    payload: dict[str, object], expected_count: int
) -> tuple[dict[str, Placement], ...]:
    """Run a batch of fCoSE seeds and parse all returned placements.

    Args:
        payload: Graph payload containing a ``seeds`` list.
        expected_count: Number of placement runs expected in the response.

    Returns:
        Placement mapping for each seed in input order.

    Raises:
        RuntimeError: If Node fails or returns malformed output.
    """

    completed = subprocess.run(
        ["node", str(FCOSE_SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"fCoSE batch failed with exit code {completed.returncode}: "
            f"{completed.stderr.strip()}"
        )
    try:
        output = json.loads(completed.stdout)
        runs = output["runs"]
        placements = tuple(
            {
                node["id"]: Placement(
                    x=float(node["x"]),
                    y=float(node["y"]),
                    width=float(node["width"]),
                    height=float(node["height"]),
                )
                for node in run["nodes"]
            }
            for run in runs
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("fCoSE batch returned malformed JSON") from error
    if len(placements) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} fCoSE runs, received {len(placements)}"
        )
    return placements


def checker_counts_for_placement(
    original_glyphs: Sequence[Glyph],
    original_arcs: Sequence[Arc],
    placements: dict[str, Placement],
) -> tuple[int, int]:
    """Evaluate one in-memory fCoSE placement with the standard checker.

    Args:
        original_glyphs: Parsed original glyphs.
        original_arcs: Parsed original arcs.
        placements: fCoSE node placements for one seed.

    Returns:
        Arc-crossing and arc-node-overlap counts.
    """

    glyphs = deepcopy(original_glyphs)
    arcs = deepcopy(original_arcs)
    apply_placements(glyphs, placements)
    routes = reroute_arcs(glyphs, arcs)
    for arc in arcs:
        route = routes.get(arc.id)
        if route is not None:
            arc.points = list(route)

    glyph_lookup, port_parent_lookup = build_renderer_lookups(glyphs)
    resolved_arcs = resolve_arc_paths(arcs, glyph_lookup, port_parent_lookup)
    node_rectangles = checked_node_rectangles(glyphs, glyph_lookup)
    crossings, _ = find_arc_crossings(resolved_arcs)
    overlaps, _ = find_arc_node_overlaps(resolved_arcs, node_rectangles)
    return len(crossings), len(overlaps)


def evaluate_diagram_batch(
    path: Path, seeds: Sequence[int]
) -> tuple[tuple[int, int], ...]:
    """Run and score a batch of fCoSE seeds for one SBGN diagram.

    Args:
        path: Original SBGN file.
        seeds: Numeric trial seeds.

    Returns:
        Crossing and overlap counts aligned with the seed order.
    """

    glyphs, arcs, _ = parse_sbgnml(path)
    payload = fcose_payload(glyphs, arcs, str(seeds[0]))
    payload.pop("seed", None)
    payload["seeds"] = [f"{seed}:{path.name}" for seed in seeds]
    placement_runs = parse_batch_placements(payload, len(seeds))
    return tuple(
        checker_counts_for_placement(glyphs, arcs, placements)
        for placements in placement_runs
    )


def run_benchmark(
    paths: Sequence[Path],
    seeds: Sequence[int],
    chunk_size: int,
    workers: int,
) -> tuple[TrialCounts, ...]:
    """Run fCoSE trials across all diagrams with bounded parallelism.

    Args:
        paths: Original SBGN files.
        seeds: Numeric trial seeds.
        chunk_size: Number of seeds sent to each Node process at once.
        workers: Maximum concurrent diagram processes.

    Returns:
        Aggregate checker counts for every seed.
    """

    all_counts: list[TrialCounts] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for chunk_start in range(0, len(seeds), chunk_size):
            chunk = seeds[chunk_start : chunk_start + chunk_size]
            per_diagram = tuple(
                executor.map(
                    evaluate_diagram_batch,
                    paths,
                    (chunk for _ in paths),
                )
            )
            for index, seed in enumerate(chunk):
                all_counts.append(
                    TrialCounts(
                        seed=seed,
                        arc_crossings=sum(
                            diagram_counts[index][0] for diagram_counts in per_diagram
                        ),
                        arc_node_overlaps=sum(
                            diagram_counts[index][1] for diagram_counts in per_diagram
                        ),
                    )
                )
            print(
                f"Completed {min(chunk_start + len(chunk), len(seeds))} / "
                f"{len(seeds)} trials",
                flush=True,
            )
    return tuple(all_counts)


def percentile(values: Sequence[int], percentile_value: float) -> float:
    """Calculate a linearly interpolated percentile.

    Args:
        values: Integer observations.
        percentile_value: Percentile from zero through one.

    Returns:
        Interpolated percentile value.
    """

    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return float(ordered[lower_index])
    weight = position - lower_index
    return ordered[lower_index] * (1.0 - weight) + ordered[upper_index] * weight


def comparison_counts(values: Sequence[int], original: int) -> tuple[int, int, int]:
    """Count trial values below, equal to, and above an original value.

    Args:
        values: Trial metric values.
        original: Original layout metric value.

    Returns:
        Counts of lower, equal, and higher trials.
    """

    return (
        sum(value < original for value in values),
        sum(value == original for value in values),
        sum(value > original for value in values),
    )


def benchmark_report(
    trial_counts: Sequence[TrialCounts],
    original_crossings: int,
    original_overlaps: int,
    diagram_count: int,
    seed_start: int,
) -> str:
    """Build a Markdown report for the multi-seed fCoSE benchmark.

    Args:
        trial_counts: Aggregate counts for every fCoSE trial.
        original_crossings: Aggregate crossing count in original files.
        original_overlaps: Aggregate overlap count in original files.
        diagram_count: Number of diagrams evaluated per trial.
        seed_start: First numeric seed in the benchmark.

    Returns:
        Complete Markdown benchmark report.
    """

    crossing_values = [trial.arc_crossings for trial in trial_counts]
    overlap_values = [trial.arc_node_overlaps for trial in trial_counts]
    crossing_comparison = comparison_counts(crossing_values, original_crossings)
    overlap_comparison = comparison_counts(overlap_values, original_overlaps)
    both_lower = sum(
        trial.arc_crossings < original_crossings
        and trial.arc_node_overlaps < original_overlaps
        for trial in trial_counts
    )
    either_lower = sum(
        trial.arc_crossings < original_crossings
        or trial.arc_node_overlaps < original_overlaps
        for trial in trial_counts
    )
    crossing_minimum = min(crossing_values)
    overlap_minimum = min(overlap_values)
    best_crossing_trial = min(
        trial_counts,
        key=lambda trial: (trial.arc_crossings, trial.arc_node_overlaps),
    )
    best_overlap_trial = min(
        trial_counts,
        key=lambda trial: (trial.arc_node_overlaps, trial.arc_crossings),
    )
    seed_end = seed_start + len(trial_counts) - 1

    return "\n".join(
        [
            f"# fCoSE {len(trial_counts):,}-trial benchmark",
            "",
            (
                f"Ran **{len(trial_counts):,} deterministic fCoSE trials** over "
                f"the same **{diagram_count} SBGN files** using seeds "
                f"`{seed_start}` through `{seed_end}`."
            ),
            "",
            "## How often fCoSE beat the originals",
            "",
            "| Comparison | Trials | Percentage |",
            "|---|---:|---:|",
            (
                f"| Fewer arc crossings than {original_crossings} | "
                f"{crossing_comparison[0]:,} | "
                f"{100.0 * crossing_comparison[0] / len(trial_counts):.1f}% |"
            ),
            (
                f"| Fewer arc-node overlaps than {original_overlaps} | "
                f"{overlap_comparison[0]:,} | "
                f"{100.0 * overlap_comparison[0] / len(trial_counts):.1f}% |"
            ),
            (
                f"| Fewer on both metrics | {both_lower:,} | "
                f"{100.0 * both_lower / len(trial_counts):.1f}% |"
            ),
            (
                f"| Fewer on at least one metric | {either_lower:,} | "
                f"{100.0 * either_lower / len(trial_counts):.1f}% |"
            ),
            "",
            "## Comparison counts",
            "",
            "| Metric | Original | Lower | Equal | Higher |",
            "|---|---:|---:|---:|---:|",
            (
                f"| Arc crossings | {original_crossings} | "
                f"{crossing_comparison[0]:,} | {crossing_comparison[1]:,} | "
                f"{crossing_comparison[2]:,} |"
            ),
            (
                f"| Arc-node overlaps | {original_overlaps} | "
                f"{overlap_comparison[0]:,} | {overlap_comparison[1]:,} | "
                f"{overlap_comparison[2]:,} |"
            ),
            "",
            "## Trial distribution",
            "",
            (
                "| Metric | Minimum | 5th percentile | Median | Mean | "
                "95th percentile | Maximum |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|",
            (
                f"| Arc crossings | {crossing_minimum} | "
                f"{percentile(crossing_values, 0.05):.1f} | "
                f"{statistics.median(crossing_values):.1f} | "
                f"{statistics.mean(crossing_values):.1f} | "
                f"{percentile(crossing_values, 0.95):.1f} | "
                f"{max(crossing_values)} |"
            ),
            (
                f"| Arc-node overlaps | {overlap_minimum} | "
                f"{percentile(overlap_values, 0.05):.1f} | "
                f"{statistics.median(overlap_values):.1f} | "
                f"{statistics.mean(overlap_values):.1f} | "
                f"{percentile(overlap_values, 0.95):.1f} | "
                f"{max(overlap_values)} |"
            ),
            "",
            "## Best observed trials",
            "",
            (
                f"- Lowest crossings: seed `{best_crossing_trial.seed}` with "
                f"{best_crossing_trial.arc_crossings} crossings and "
                f"{best_crossing_trial.arc_node_overlaps} overlaps."
            ),
            (
                f"- Lowest overlaps: seed `{best_overlap_trial.seed}` with "
                f"{best_overlap_trial.arc_crossings} crossings and "
                f"{best_overlap_trial.arc_node_overlaps} overlaps."
            ),
            "",
            "## Method",
            "",
            (
                "Each trial used plain Cytoscape.js fCoSE node placement with "
                "`quality: proof`, deterministic randomization, preserved node "
                "sizes, inferred compound compartments, translated ports and "
                "auxiliary glyphs, and straight rerouted arcs. No trial was "
                "selected or tuned using checker feedback."
            ),
            "",
            (
                "Run `uv run --project python python python/tools/benchmark_fcose.py` "
                "from the project root "
                "to reproduce the benchmark."
            ),
            "",
        ]
    )


def main() -> None:
    """Parse arguments, run the fCoSE benchmark, and write its report."""

    parser = argparse.ArgumentParser(
        description="Run many fCoSE layouts and compare them with original SBGN files."
    )
    parser.add_argument(
        "-i",
        "--input-directory",
        type=Path,
        default=DEFAULT_INPUT_DIRECTORY,
        help=f"Original SBGN directory (default: {DEFAULT_INPUT_DIRECTORY})",
    )
    parser.add_argument(
        "-n",
        "--trials",
        type=int,
        default=DEFAULT_TRIAL_COUNT,
        help=f"Number of fCoSE trials (default: {DEFAULT_TRIAL_COUNT})",
    )
    parser.add_argument(
        "--seed-start",
        type=int,
        default=DEFAULT_SEED_START,
        help=f"First deterministic seed (default: {DEFAULT_SEED_START})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Seeds per Node batch (default: {DEFAULT_CHUNK_SIZE})",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Concurrent diagram workers (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Markdown report path (default: {DEFAULT_REPORT_PATH})",
    )
    args = parser.parse_args()

    if args.trials <= 0:
        parser.error("--trials must be positive")
    if args.chunk_size <= 0:
        parser.error("--chunk-size must be positive")
    if args.workers <= 0:
        parser.error("--workers must be positive")

    paths = collect_sbgn_files([args.input_directory])
    original_results = tuple(analyze_sbgn_file(path) for path in paths)
    original_crossings = sum(len(result.arc_crossings) for result in original_results)
    original_overlaps = sum(
        len(result.arc_node_overlaps) for result in original_results
    )
    seeds = tuple(range(args.seed_start, args.seed_start + args.trials))
    trial_counts = run_benchmark(
        paths,
        seeds,
        chunk_size=args.chunk_size,
        workers=args.workers,
    )
    report = benchmark_report(
        trial_counts,
        original_crossings,
        original_overlaps,
        diagram_count=len(paths),
        seed_start=args.seed_start,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {len(trial_counts):,}-trial report to {args.output}")


if __name__ == "__main__":
    main()
