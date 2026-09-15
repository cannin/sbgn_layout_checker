#!/usr/bin/env python3
"""Analyze SBGN layouts for arc crossings and arc-node overlaps."""

import argparse
import math
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from render_sbgn_py.renderer import (
    Arc,
    Glyph,
    PixelRect,
    Point,
    is_js_hidden_glyph_class,
    js_arc_line_path,
    js_arc_path,
    parse_sbgnml,
    sbgnviz_manifest_rect,
)

GEOMETRY_EPSILON = 1e-9
PARSER_SOURCE = (
    "https://github.com/cannin/render_sbgn/tree/"
    "f0b98cfc92ad1db353aaf4aa495e488740b88c1d/python"
)
DEFAULT_INPUT_PATH = Path("examples/sbgn_examples")
DEFAULT_REPORT_PATH = Path("reports/sbgn_layout_report.md")


@dataclass(frozen=True)
class ResolvedArc:
    """Arc geometry resolved by render_sbgn_py."""

    id: str
    class_name: str
    points: tuple[Point, ...]
    source_id: str
    target_id: str


@dataclass(frozen=True)
class ArcCrossing:
    """One proper intersection between two arc path segments."""

    first_arc_id: str
    second_arc_id: str
    point: Point


@dataclass(frozen=True)
class ArcNodeOverlap:
    """One arc whose centerline enters a non-endpoint node rectangle."""

    arc_id: str
    glyph_id: str
    glyph_class: str


@dataclass(frozen=True)
class FileAnalysis:
    """Checker counts and findings for one SBGN file."""

    path: Path
    parsed_glyph_count: int
    checked_node_count: int
    parsed_arc_count: int
    resolved_arc_count: int
    arc_pair_count: int
    arc_crossings: tuple[ArcCrossing, ...]
    crossing_arc_pair_count: int
    arc_node_pair_count: int
    arc_node_overlaps: tuple[ArcNodeOverlap, ...]


def cross_product(first: Point, second: Point, third: Point) -> float:
    """Calculate the signed cross product for three points.

    Args:
        first: Origin point for both vectors.
        second: Endpoint of the first vector.
        third: Endpoint of the second vector.

    Returns:
        Signed two-dimensional cross product.
    """

    return (second.x - first.x) * (third.y - first.y) - (second.y - first.y) * (
        third.x - first.x
    )


def proper_segment_intersection(
    first_start: Point,
    first_end: Point,
    second_start: Point,
    second_end: Point,
) -> Point | None:
    """Find a proper interior intersection between two line segments.

    Endpoint contacts, tangent touches, and collinear overlaps are deliberately
    excluded because they are not visual crossings.

    Args:
        first_start: Start of the first segment.
        first_end: End of the first segment.
        second_start: Start of the second segment.
        second_end: End of the second segment.

    Returns:
        The crossing point, or None when the segments do not properly cross.
    """

    first_side_start = cross_product(first_start, first_end, second_start)
    first_side_end = cross_product(first_start, first_end, second_end)
    second_side_start = cross_product(second_start, second_end, first_start)
    second_side_end = cross_product(second_start, second_end, first_end)

    crosses_first = (first_side_start > GEOMETRY_EPSILON) != (
        first_side_end > GEOMETRY_EPSILON
    )
    crosses_second = (second_side_start > GEOMETRY_EPSILON) != (
        second_side_end > GEOMETRY_EPSILON
    )
    away_from_boundaries = all(
        abs(value) > GEOMETRY_EPSILON
        for value in (
            first_side_start,
            first_side_end,
            second_side_start,
            second_side_end,
        )
    )
    if not (crosses_first and crosses_second and away_from_boundaries):
        return None

    first_dx = first_end.x - first_start.x
    first_dy = first_end.y - first_start.y
    second_dx = second_end.x - second_start.x
    second_dy = second_end.y - second_start.y
    denominator = first_dx * second_dy - first_dy * second_dx
    if abs(denominator) <= GEOMETRY_EPSILON:
        return None

    offset_x = second_start.x - first_start.x
    offset_y = second_start.y - first_start.y
    first_parameter = (offset_x * second_dy - offset_y * second_dx) / denominator
    return Point(
        x=first_start.x + first_parameter * first_dx,
        y=first_start.y + first_parameter * first_dy,
    )


def points_are_close(first: Point, second: Point) -> bool:
    """Check whether two points represent the same geometric event.

    Args:
        first: First point.
        second: Second point.

    Returns:
        True when both coordinates are equal within the checker tolerance.
    """

    return math.isclose(
        first.x,
        second.x,
        rel_tol=0.0,
        abs_tol=GEOMETRY_EPSILON,
    ) and math.isclose(
        first.y,
        second.y,
        rel_tol=0.0,
        abs_tol=GEOMETRY_EPSILON,
    )


def arc_pair_crossings(
    first_arc: ResolvedArc, second_arc: ResolvedArc
) -> tuple[Point, ...]:
    """Find unique proper crossings between two polyline arcs.

    Args:
        first_arc: First resolved polyline arc.
        second_arc: Second resolved polyline arc.

    Returns:
        Unique crossing points in segment traversal order.
    """

    crossings: list[Point] = []
    for first_start, first_end in zip(first_arc.points, first_arc.points[1:]):
        for second_start, second_end in zip(second_arc.points, second_arc.points[1:]):
            crossing = proper_segment_intersection(
                first_start,
                first_end,
                second_start,
                second_end,
            )
            if crossing is None:
                continue
            if not any(points_are_close(crossing, seen) for seen in crossings):
                crossings.append(crossing)
    return tuple(crossings)


def open_axis_interval(
    start: float, delta: float, lower: float, upper: float
) -> tuple[float, float] | None:
    """Find parameter values placing one segment axis inside open bounds.

    Args:
        start: Segment coordinate at parameter zero.
        delta: Coordinate change over the segment.
        lower: Lower rectangle boundary.
        upper: Upper rectangle boundary.

    Returns:
        Open parameter interval, or None if the axis never enters the bounds.
    """

    if upper - lower <= GEOMETRY_EPSILON:
        return None
    if abs(delta) <= GEOMETRY_EPSILON:
        if lower < start < upper:
            return (-math.inf, math.inf)
        return None
    first_parameter = (lower - start) / delta
    second_parameter = (upper - start) / delta
    return (
        min(first_parameter, second_parameter),
        max(first_parameter, second_parameter),
    )


def segment_enters_rectangle_interior(
    start: Point, end: Point, rectangle: PixelRect
) -> bool:
    """Check whether a segment enters a rectangle's open interior.

    Merely touching or following the rectangle boundary is not an overlap.

    Args:
        start: Segment start point.
        end: Segment end point.
        rectangle: Rectangle to check.

    Returns:
        True when at least one segment point lies strictly inside the rectangle.
    """

    x_interval = open_axis_interval(
        start.x,
        end.x - start.x,
        rectangle.x0,
        rectangle.x0 + rectangle.width,
    )
    y_interval = open_axis_interval(
        start.y,
        end.y - start.y,
        rectangle.y0,
        rectangle.y0 + rectangle.height,
    )
    if x_interval is None or y_interval is None:
        return False

    lower_parameter = max(0.0, x_interval[0], y_interval[0])
    upper_parameter = min(1.0, x_interval[1], y_interval[1])
    return upper_parameter - lower_parameter > GEOMETRY_EPSILON


def build_renderer_lookups(
    glyphs: Sequence[Glyph],
) -> tuple[dict[str, Glyph], dict[str, str]]:
    """Build the ID lookups expected by render_sbgn_py arc helpers.

    Args:
        glyphs: Parsed glyphs.

    Returns:
        Unique glyph lookup and port-to-parent-glyph lookup.
    """

    glyph_lookup: dict[str, Glyph] = {}
    port_parent_lookup: dict[str, str] = {}
    for glyph in glyphs:
        if not glyph.id or glyph.id in glyph_lookup:
            continue
        glyph_lookup[glyph.id] = glyph
        for port in glyph.ports:
            if port.id:
                port_parent_lookup[port.id] = glyph.id
    return glyph_lookup, port_parent_lookup


def resolve_arc_paths(
    arcs: Sequence[Arc],
    glyph_lookup: dict[str, Glyph],
    port_parent_lookup: dict[str, str],
) -> tuple[ResolvedArc, ...]:
    """Resolve parsed arcs to the line paths used by render_sbgn_py.

    Args:
        arcs: Parsed SBGN arcs.
        glyph_lookup: Unique glyph lookup.
        port_parent_lookup: Port-to-parent-glyph lookup.

    Returns:
        Arcs with usable rendered polyline geometry.
    """

    resolved_arcs: list[ResolvedArc] = []
    for index, arc in enumerate(arcs, start=1):
        resolved = js_arc_path(arc, glyph_lookup, port_parent_lookup)
        if resolved is None:
            continue
        path_points, source_id, target_id = resolved
        line_points = js_arc_line_path(
            arc,
            path_points,
            glyph_lookup,
            port_parent_lookup,
        )
        if len(line_points) < 2:
            continue
        resolved_arcs.append(
            ResolvedArc(
                id=arc.id or f"unnamed-arc-{index}",
                class_name=arc.class_name,
                points=tuple(line_points),
                source_id=source_id,
                target_id=target_id,
            )
        )
    return tuple(resolved_arcs)


def checked_node_rectangles(
    glyphs: Sequence[Glyph], glyph_lookup: dict[str, Glyph]
) -> dict[str, tuple[Glyph, PixelRect]]:
    """Select rendered node glyphs and obtain their effective rectangles.

    Compartment backgrounds and glyph classes hidden as standalone nodes are
    excluded. Duplicate IDs use the same first-occurrence rule as the renderer.

    Args:
        glyphs: Parsed SBGN glyphs.
        glyph_lookup: Unique glyph lookup.

    Returns:
        Mapping from checked node IDs to glyphs and rendered rectangles.
    """

    rectangles: dict[str, tuple[Glyph, PixelRect]] = {}
    for glyph in glyphs:
        if glyph_lookup.get(glyph.id) is not glyph:
            continue
        if glyph.bbox is None or glyph.class_name == "compartment":
            continue
        if is_js_hidden_glyph_class(glyph.class_name):
            continue
        rectangle = sbgnviz_manifest_rect(glyph)
        if rectangle.width <= 0.0 or rectangle.height <= 0.0:
            continue
        rectangles[glyph.id] = (glyph, rectangle)
    return rectangles


def find_arc_crossings(
    arcs: Sequence[ResolvedArc],
) -> tuple[tuple[ArcCrossing, ...], int]:
    """Find all proper crossings and the number of affected arc pairs.

    Args:
        arcs: Resolved arc paths.

    Returns:
        Crossing events and the number of arc pairs with at least one crossing.
    """

    crossings: list[ArcCrossing] = []
    crossing_pair_count = 0
    for first_arc, second_arc in combinations(arcs, 2):
        pair_points = arc_pair_crossings(first_arc, second_arc)
        if pair_points:
            crossing_pair_count += 1
        crossings.extend(
            ArcCrossing(
                first_arc_id=first_arc.id,
                second_arc_id=second_arc.id,
                point=point,
            )
            for point in pair_points
        )
    return tuple(crossings), crossing_pair_count


def find_arc_node_overlaps(
    arcs: Sequence[ResolvedArc],
    node_rectangles: dict[str, tuple[Glyph, PixelRect]],
) -> tuple[tuple[ArcNodeOverlap, ...], int]:
    """Find arc paths entering non-endpoint node rectangle interiors.

    Each arc-node relationship is counted at most once, even if several path
    segments enter the same node.

    Args:
        arcs: Resolved arc paths.
        node_rectangles: Checked node glyphs and their rectangles.

    Returns:
        Arc-node overlap findings and the eligible relationship count.
    """

    overlaps: list[ArcNodeOverlap] = []
    eligible_pair_count = 0
    for arc in arcs:
        endpoint_ids = {arc.source_id, arc.target_id}
        for glyph_id, (glyph, rectangle) in node_rectangles.items():
            if glyph_id in endpoint_ids:
                continue
            eligible_pair_count += 1
            if any(
                segment_enters_rectangle_interior(start, end, rectangle)
                for start, end in zip(arc.points, arc.points[1:])
            ):
                overlaps.append(
                    ArcNodeOverlap(
                        arc_id=arc.id,
                        glyph_id=glyph_id,
                        glyph_class=glyph.class_name,
                    )
                )
    return tuple(overlaps), eligible_pair_count


def analyze_sbgn_file(path: Path) -> FileAnalysis:
    """Analyze one SBGN file with the two layout checks.

    Args:
        path: SBGN-ML file to analyze.

    Returns:
        Checker counts and findings for the file.
    """

    glyphs, arcs, _ = parse_sbgnml(path)
    glyph_lookup, port_parent_lookup = build_renderer_lookups(glyphs)
    resolved_arcs = resolve_arc_paths(arcs, glyph_lookup, port_parent_lookup)
    node_rectangles = checked_node_rectangles(glyphs, glyph_lookup)
    arc_crossings, crossing_arc_pair_count = find_arc_crossings(resolved_arcs)
    arc_node_overlaps, arc_node_pair_count = find_arc_node_overlaps(
        resolved_arcs, node_rectangles
    )
    return FileAnalysis(
        path=path,
        parsed_glyph_count=len(glyphs),
        checked_node_count=len(node_rectangles),
        parsed_arc_count=len(arcs),
        resolved_arc_count=len(resolved_arcs),
        arc_pair_count=math.comb(len(resolved_arcs), 2),
        arc_crossings=arc_crossings,
        crossing_arc_pair_count=crossing_arc_pair_count,
        arc_node_pair_count=arc_node_pair_count,
        arc_node_overlaps=arc_node_overlaps,
    )


def collect_sbgn_files(input_paths: Sequence[Path]) -> tuple[Path, ...]:
    """Collect unique SBGN files from file and directory arguments.

    Args:
        input_paths: SBGN files or directories to search recursively.

    Returns:
        Sorted unique SBGN file paths.

    Raises:
        FileNotFoundError: If an input path does not exist.
        ValueError: If no SBGN files are found.
    """

    files: set[Path] = set()
    for input_path in input_paths:
        if not input_path.exists():
            raise FileNotFoundError(f"Input path does not exist: {input_path}")
        if input_path.is_file():
            if input_path.suffix.lower() == ".sbgn":
                files.add(input_path)
            continue
        files.update(input_path.rglob("*.sbgn"))
    if not files:
        raise ValueError("No .sbgn files found")
    return tuple(sorted(files, key=lambda path: str(path)))


def percentage(numerator: int, denominator: int) -> str:
    """Format a count as a percentage of its denominator.

    Args:
        numerator: Count of matching events or relationships.
        denominator: Count of opportunities.

    Returns:
        Percentage with two decimal places, or "n/a" for a zero denominator.
    """

    if denominator == 0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.2f}%"


def markdown_report(
    results: Sequence[FileAnalysis],
    reproduction_command: str = "uv run --project python sbgn-layout-checker-py",
) -> str:
    """Build a Markdown report from file analysis results.

    Args:
        results: Per-file checker results.
        reproduction_command: Command that regenerates this specific report.

    Returns:
        Complete Markdown report text.
    """

    total_glyphs = sum(result.parsed_glyph_count for result in results)
    total_nodes = sum(result.checked_node_count for result in results)
    total_arcs = sum(result.parsed_arc_count for result in results)
    total_resolved_arcs = sum(result.resolved_arc_count for result in results)
    total_arc_pairs = sum(result.arc_pair_count for result in results)
    total_crossings = sum(len(result.arc_crossings) for result in results)
    total_crossing_pairs = sum(result.crossing_arc_pair_count for result in results)
    total_arc_node_pairs = sum(result.arc_node_pair_count for result in results)
    total_arc_node_overlaps = sum(len(result.arc_node_overlaps) for result in results)

    lines = [
        "# SBGN layout checker report",
        "",
        f"Analyzed **{len(results)} SBGN files**.",
        "",
        "## Summary",
        "",
        "| Metric | Count | Rate |",
        "|---|---:|---:|",
        f"| Parsed glyphs | {total_glyphs} | - |",
        f"| Node glyphs checked | {total_nodes} | - |",
        f"| Parsed arcs | {total_arcs} | - |",
        f"| Arc paths checked | {total_resolved_arcs} | - |",
        f"| Arc-crossing events | {total_crossings} | - |",
        (
            f"| Arc pairs with crossings | {total_crossing_pairs} / "
            f"{total_arc_pairs} | "
            f"{percentage(total_crossing_pairs, total_arc_pairs)} |"
        ),
        (
            f"| Arc-node overlaps | {total_arc_node_overlaps} / "
            f"{total_arc_node_pairs} | "
            f"{percentage(total_arc_node_overlaps, total_arc_node_pairs)} |"
        ),
        "",
        "## Per-file counts",
        "",
        (
            "| File | Nodes checked | Arcs checked | Arc pairs | "
            "Crossing events | Crossing pairs | Arc-node pairs | "
            "Arc-node overlaps |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| `{result.path.name}` | {result.checked_node_count} | "
            f"{result.resolved_arc_count} | {result.arc_pair_count} | "
            f"{len(result.arc_crossings)} | {result.crossing_arc_pair_count} | "
            f"{result.arc_node_pair_count} | "
            f"{len(result.arc_node_overlaps)} |"
        )

    lines.extend(
        [
            "",
            "## Checker definitions",
            "",
            (
                "- SBGN parsing, port-aware path resolution, line endpoint "
                f"adjustment, hidden-node filtering, and rendered node rectangles "
                f"come from [`render_sbgn_py`]({PARSER_SOURCE})."
            ),
            (
                "- **Arc crossing:** a proper intersection inside two polyline "
                "segments. Shared endpoints, boundary touches, tangent contacts, "
                "and collinear overlaps are not counted. A pair can contribute "
                "more than one crossing event."
            ),
            (
                "- **Arc-node overlap:** an arc centerline enters the open interior "
                "of a rendered node bounding rectangle. The arc's source and "
                "target nodes are excluded, as are compartment backgrounds and "
                "glyph classes hidden as standalone renderer nodes. Each arc-node "
                "pair is counted at most once."
            ),
            (
                "- Rates use arc pairs within each file and eligible non-endpoint "
                "arc-node pairs as their denominators."
            ),
            "",
            "## Interpretation",
            "",
            (
                "Both checks are geometric layout checks, not SBGN semantic "
                "validation. Node overlap uses rendered bounding rectangles, so "
                "it is intentionally conservative around rounded or irregular "
                "glyph corners."
            ),
            "",
            "## Reproduction",
            "",
            f"Run `{reproduction_command}` from the project root.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    """Parse command-line arguments, analyze SBGN files, and write a report."""

    parser = argparse.ArgumentParser(
        description=(
            "Count proper arc crossings and non-endpoint arc-node overlaps in "
            "SBGN-ML files."
        )
    )
    parser.add_argument(
        "input_paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_INPUT_PATH],
        help=(
            "SBGN file or directory to analyze recursively "
            f"(default: {DEFAULT_INPUT_PATH})"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Markdown report path (default: {DEFAULT_REPORT_PATH})",
    )
    args = parser.parse_args()

    files = collect_sbgn_files(args.input_paths)
    results = tuple(analyze_sbgn_file(path) for path in files)
    reproduction_command = shlex.join(
        [
            "uv",
            "run",
            "--project",
            "python",
            "sbgn-layout-checker-py",
            *(str(path) for path in args.input_paths),
            "--output",
            str(args.output),
        ]
    )
    report = markdown_report(results, reproduction_command)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Analyzed {len(results)} files and wrote {args.output}")


if __name__ == "__main__":
    main()
