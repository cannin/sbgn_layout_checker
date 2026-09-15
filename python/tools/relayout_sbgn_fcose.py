#!/usr/bin/env python3
"""Relayout SBGN files with fCoSE and compare layout checker counts."""

import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from render_sbgn_py.renderer import (
    Arc,
    BBox,
    Glyph,
    Point,
    Port,
    is_js_hidden_glyph_class,
    js_arc_line_path,
    js_arc_path,
    parse_sbgnml,
    sbgnviz_manifest_rect,
    strip_tag,
)

from sbgn_layout_checker.analyze_sbgn_layout import (
    FileAnalysis,
    analyze_sbgn_file,
    build_renderer_lookups,
    collect_sbgn_files,
    markdown_report,
)

DEFAULT_INPUT_DIRECTORY = Path("examples/sbgn_examples")
DEFAULT_OUTPUT_DIRECTORY = Path("examples/sbgn_examples_fcose")
DEFAULT_LAYOUT_REPORT = Path("reports/sbgn_layout_report_fcose.md")
DEFAULT_COMPARISON_REPORT = Path("reports/fcose_comparison_report.md")
FCOSE_SCRIPT = Path(__file__).parents[2] / "fcose_layout.mjs"
DEFAULT_SEED = 20260831


@dataclass(frozen=True)
class Placement:
    """A node center and dimensions returned by fCoSE."""

    x: float
    y: float
    width: float
    height: float


def rectangle_contains_center(container: Glyph, child: Glyph) -> bool:
    """Check whether a child's center lies inside a compartment rectangle.

    Args:
        container: Candidate compartment glyph.
        child: Candidate child glyph.

    Returns:
        True when both glyphs have boxes and the child center is contained.
    """

    if container.bbox is None or child.bbox is None:
        return False
    center_x = child.bbox.x + child.bbox.w / 2.0
    center_y = child.bbox.y + child.bbox.h / 2.0
    return (
        container.bbox.x <= center_x <= container.bbox.x + container.bbox.w
        and container.bbox.y <= center_y <= container.bbox.y + container.bbox.h
    )


def infer_layout_parents(glyphs: Sequence[Glyph]) -> dict[str, str]:
    """Infer fCoSE compound parents without altering SBGN semantics.

    Explicit parsed parents take precedence. For top-level nodes, the smallest
    original compartment containing the node center is used only in the fCoSE
    graph because these Reactome exports omit compartmentRef attributes.

    Args:
        glyphs: Unique visible glyphs with bounding boxes.

    Returns:
        Mapping from child glyph IDs to fCoSE parent glyph IDs.
    """

    visible_ids = {glyph.id for glyph in glyphs}
    compartments = [glyph for glyph in glyphs if glyph.class_name == "compartment"]
    parents: dict[str, str] = {}
    for glyph in glyphs:
        if glyph.class_name == "compartment":
            continue
        if glyph.parent_id in visible_ids:
            parents[glyph.id] = str(glyph.parent_id)
            continue
        containing_compartments = [
            compartment
            for compartment in compartments
            if rectangle_contains_center(compartment, glyph)
        ]
        if not containing_compartments:
            continue
        parent = min(
            containing_compartments,
            key=lambda compartment: compartment.bbox.w * compartment.bbox.h,
        )
        parents[glyph.id] = parent.id
    return parents


def fcose_payload(
    glyphs: Sequence[Glyph], arcs: Sequence[Arc], seed: str
) -> dict[str, object]:
    """Build the graph payload consumed by the Node fCoSE adapter.

    Args:
        glyphs: Parsed SBGN glyphs.
        arcs: Parsed SBGN arcs.
        seed: Deterministic random seed for this diagram.

    Returns:
        JSON-serializable nodes, edges, and seed.
    """

    glyph_lookup, port_parent_lookup = build_renderer_lookups(glyphs)
    visible_glyphs = [
        glyph
        for glyph in glyphs
        if glyph_lookup.get(glyph.id) is glyph
        and glyph.bbox is not None
        and not is_js_hidden_glyph_class(glyph.class_name)
    ]
    parent_by_id = infer_layout_parents(visible_glyphs)
    active_compartment_ids = set(parent_by_id.values())
    layout_glyphs = [
        glyph
        for glyph in visible_glyphs
        if glyph.class_name != "compartment" or glyph.id in active_compartment_ids
    ]
    layout_ids = {glyph.id for glyph in layout_glyphs}

    nodes = []
    for glyph in layout_glyphs:
        rectangle = sbgnviz_manifest_rect(glyph)
        node = {
            "id": glyph.id,
            "x": rectangle.center.x,
            "y": rectangle.center.y,
            "width": max(rectangle.width, 1.0),
            "height": max(rectangle.height, 1.0),
        }
        parent_id = parent_by_id.get(glyph.id)
        if parent_id in layout_ids:
            node["parent"] = parent_id
        nodes.append(node)

    edges = []
    for index, arc in enumerate(arcs, start=1):
        resolved = js_arc_path(arc, glyph_lookup, port_parent_lookup)
        if resolved is None:
            continue
        _, source_id, target_id = resolved
        if source_id not in layout_ids or target_id not in layout_ids:
            continue
        edges.append(
            {
                "id": f"layout-edge-{index}",
                "source": source_id,
                "target": target_id,
            }
        )

    return {"seed": seed, "nodes": nodes, "edges": edges}


def run_fcose(payload: dict[str, object]) -> dict[str, Placement]:
    """Run the Node fCoSE adapter and parse its node placements.

    Args:
        payload: JSON-compatible fCoSE graph payload.

    Returns:
        Mapping from glyph IDs to fCoSE placements.

    Raises:
        RuntimeError: If the fCoSE subprocess fails or returns malformed output.
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
            f"fCoSE failed with exit code {completed.returncode}: "
            f"{completed.stderr.strip()}"
        )
    try:
        output = json.loads(completed.stdout)
        return {
            node["id"]: Placement(
                x=float(node["x"]),
                y=float(node["y"]),
                width=float(node["width"]),
                height=float(node["height"]),
            )
            for node in output["nodes"]
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("fCoSE returned malformed JSON") from error


def nearest_placed_ancestor(
    glyph: Glyph,
    glyph_lookup: dict[str, Glyph],
    placements: dict[str, Placement],
) -> Glyph | None:
    """Find the nearest parent glyph that received an fCoSE placement.

    Args:
        glyph: Glyph whose ancestor is needed.
        glyph_lookup: Unique glyph lookup.
        placements: fCoSE placements by glyph ID.

    Returns:
        Nearest placed ancestor, or None.
    """

    parent_id = glyph.parent_id
    seen_ids: set[str] = set()
    while parent_id and parent_id not in seen_ids:
        seen_ids.add(parent_id)
        parent = glyph_lookup.get(parent_id)
        if parent is None:
            return None
        if parent.id in placements:
            return parent
        parent_id = parent.parent_id
    return None


def apply_placements(
    glyphs: Sequence[Glyph], placements: dict[str, Placement]
) -> dict[str, tuple[float, float]]:
    """Apply fCoSE positions to parsed glyph boxes and ports.

    Hidden auxiliary glyphs follow their nearest placed parent. Leaf node sizes
    remain unchanged; fCoSE-computed dimensions are used for compound nodes.

    Args:
        glyphs: Parsed SBGN glyphs to update in memory.
        placements: fCoSE placements by glyph ID.

    Returns:
        Per-glyph coordinate translations for XML label updates.
    """

    glyph_lookup, _ = build_renderer_lookups(glyphs)
    original_centers = {
        glyph.id: Point(
            glyph.bbox.x + glyph.bbox.w / 2.0,
            glyph.bbox.y + glyph.bbox.h / 2.0,
        )
        for glyph in glyphs
        if glyph.bbox is not None and glyph_lookup.get(glyph.id) is glyph
    }
    deltas: dict[str, tuple[float, float]] = {}

    for glyph in glyphs:
        if glyph.bbox is None or glyph_lookup.get(glyph.id) is not glyph:
            continue
        placement = placements.get(glyph.id)
        if placement is not None:
            old_center = original_centers[glyph.id]
            delta_x = placement.x - old_center.x
            delta_y = placement.y - old_center.y
            width = glyph.bbox.w
            height = glyph.bbox.h
            if glyph.class_name == "compartment":
                width = placement.width
                height = placement.height
            glyph.bbox = BBox(
                x=placement.x - width / 2.0,
                y=placement.y - height / 2.0,
                w=width,
                h=height,
            )
            glyph.ports = [
                Port(id=port.id, x=port.x + delta_x, y=port.y + delta_y)
                for port in glyph.ports
            ]
            deltas[glyph.id] = (delta_x, delta_y)

    for glyph in glyphs:
        if glyph.bbox is None or glyph.id in deltas:
            continue
        ancestor = nearest_placed_ancestor(glyph, glyph_lookup, placements)
        if ancestor is None or ancestor.id not in deltas:
            continue
        delta_x, delta_y = deltas[ancestor.id]
        glyph.bbox = BBox(
            x=glyph.bbox.x + delta_x,
            y=glyph.bbox.y + delta_y,
            w=glyph.bbox.w,
            h=glyph.bbox.h,
        )
        glyph.ports = [
            Port(id=port.id, x=port.x + delta_x, y=port.y + delta_y)
            for port in glyph.ports
        ]
        deltas[glyph.id] = (delta_x, delta_y)
    return deltas


def reroute_arcs(
    glyphs: Sequence[Glyph], arcs: Sequence[Arc]
) -> dict[str, tuple[Point, Point]]:
    """Replace arc bends with straight paths between updated endpoints.

    Args:
        glyphs: Glyphs after fCoSE placement.
        arcs: Parsed SBGN arcs.

    Returns:
        Mapping from arc IDs to new start and end points.
    """

    glyph_lookup, port_parent_lookup = build_renderer_lookups(glyphs)
    routes: dict[str, tuple[Point, Point]] = {}
    for arc in arcs:
        original_points = arc.points
        arc.points = []
        resolved = js_arc_path(arc, glyph_lookup, port_parent_lookup)
        arc.points = original_points
        if resolved is None:
            continue
        path_points, _, _ = resolved
        line_points = js_arc_line_path(
            arc,
            path_points,
            glyph_lookup,
            port_parent_lookup,
        )
        routes[arc.id] = (line_points[0], line_points[-1])
    return routes


def direct_child(element: ET.Element, tag_name: str) -> ET.Element | None:
    """Find the first direct child with a namespace-independent tag.

    Args:
        element: XML parent element.
        tag_name: Local tag name to find.

    Returns:
        Matching child, or None.
    """

    return next(
        (child for child in element if strip_tag(child.tag) == tag_name),
        None,
    )


def set_xy(element: ET.Element, x: float, y: float) -> None:
    """Set stable decimal x and y attributes on an XML element.

    Args:
        element: XML element to update.
        x: New x coordinate.
        y: New y coordinate.

    Returns:
        None.
    """

    element.set("x", f"{x:.6f}")
    element.set("y", f"{y:.6f}")


def translate_nested_bbox(
    element: ET.Element,
    delta_x: float,
    delta_y: float,
    *,
    include_direct: bool = False,
) -> None:
    """Translate nested label boxes and optionally the direct body box.

    Args:
        element: Glyph XML element.
        delta_x: Horizontal translation.
        delta_y: Vertical translation.
        include_direct: Whether to translate the element's direct body bbox.

    Returns:
        None.
    """

    if include_direct:
        bbox_elements = [
            descendant
            for descendant in element.iter()
            if strip_tag(descendant.tag) == "bbox"
        ]
    else:
        bbox_elements = [
            descendant
            for child in element
            if strip_tag(child.tag) == "label"
            for descendant in child.iter()
            if strip_tag(descendant.tag) == "bbox"
        ]
    for descendant in bbox_elements:
        x = descendant.get("x")
        y = descendant.get("y")
        if x is not None and y is not None:
            set_xy(descendant, float(x) + delta_x, float(y) + delta_y)


def write_relaid_sbgn(
    source_path: Path,
    output_path: Path,
    glyphs: Sequence[Glyph],
    arcs: Sequence[Arc],
    deltas: dict[str, tuple[float, float]],
    routes: dict[str, tuple[Point, Point]],
) -> None:
    """Write updated glyph and arc geometry to a new SBGN file.

    Args:
        source_path: Original SBGN file.
        output_path: Destination SBGN file.
        glyphs: Glyphs with updated positions.
        arcs: Original parsed arcs.
        deltas: Glyph translations by ID.
        routes: Straight updated routes by arc ID.

    Returns:
        None.
    """

    tree = ET.parse(source_path)
    root = tree.getroot()
    if root.tag.startswith("{"):
        ET.register_namespace("", root.tag.split("}", maxsplit=1)[0][1:])
    glyph_lookup, _ = build_renderer_lookups(glyphs)
    arc_lookup = {arc.id: arc for arc in arcs}

    for element in root.iter():
        if strip_tag(element.tag) != "glyph":
            continue
        glyph = glyph_lookup.get(element.get("id", ""))
        if glyph is None or glyph.bbox is None:
            continue
        bbox_element = direct_child(element, "bbox")
        if bbox_element is not None:
            set_xy(bbox_element, glyph.bbox.x, glyph.bbox.y)
            bbox_element.set("w", f"{glyph.bbox.w:.6f}")
            bbox_element.set("h", f"{glyph.bbox.h:.6f}")
        delta = deltas.get(glyph.id)
        if delta is not None:
            translate_nested_bbox(element, *delta)
        ports_by_id = {port.id: port for port in glyph.ports}
        for child in element:
            if strip_tag(child.tag) != "port":
                continue
            port = ports_by_id.get(child.get("id", ""))
            if port is not None:
                set_xy(child, port.x, port.y)

    for element in root.iter():
        if strip_tag(element.tag) != "arc":
            continue
        arc_id = element.get("id", "")
        route = routes.get(arc_id)
        arc = arc_lookup.get(arc_id)
        if route is None or arc is None:
            continue
        start_element = direct_child(element, "start")
        end_element = direct_child(element, "end")
        if start_element is None or end_element is None:
            continue
        old_midpoint = Point(
            x=(arc.points[0].x + arc.points[-1].x) / 2.0,
            y=(arc.points[0].y + arc.points[-1].y) / 2.0,
        )
        new_midpoint = Point(
            x=(route[0].x + route[1].x) / 2.0,
            y=(route[0].y + route[1].y) / 2.0,
        )
        set_xy(start_element, route[0].x, route[0].y)
        set_xy(end_element, route[1].x, route[1].y)
        for endpoint in (start_element, end_element):
            for child in list(endpoint):
                if strip_tag(child.tag) == "point":
                    endpoint.remove(child)
        for child in list(element):
            if strip_tag(child.tag) == "next":
                element.remove(child)
            elif strip_tag(child.tag) == "glyph":
                translate_nested_bbox(
                    child,
                    new_midpoint.x - old_midpoint.x,
                    new_midpoint.y - old_midpoint.y,
                    include_direct=True,
                )

    ET.indent(tree, space="    ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def relayout_file(source_path: Path, output_path: Path, seed: int) -> None:
    """Relayout one SBGN file and write it to a separate path.

    Args:
        source_path: Original SBGN file.
        output_path: Destination for the relaid-out file.
        seed: Base deterministic random seed.

    Returns:
        None.
    """

    glyphs, arcs, _ = parse_sbgnml(source_path)
    payload = fcose_payload(glyphs, arcs, f"{seed}:{source_path.name}")
    placements = run_fcose(payload)
    deltas = apply_placements(glyphs, placements)
    routes = reroute_arcs(glyphs, arcs)
    write_relaid_sbgn(source_path, output_path, glyphs, arcs, deltas, routes)


def change_label(before: int, after: int) -> str:
    """Describe whether a checker count improved or worsened.

    Args:
        before: Original count.
        after: fCoSE count.

    Returns:
        Human-readable direction and signed difference.
    """

    difference = after - before
    if difference < 0:
        return f"better ({difference})"
    if difference > 0:
        return f"worse (+{difference})"
    return "unchanged (0)"


def comparison_report(
    before_results: Sequence[FileAnalysis],
    after_results: Sequence[FileAnalysis],
    seed: int,
) -> str:
    """Build a Markdown comparison of original and fCoSE checker counts.

    Args:
        before_results: Checker results for original files.
        after_results: Checker results for fCoSE output files.
        seed: fCoSE random seed used for reproducibility.

    Returns:
        Complete Markdown comparison report.
    """

    before_by_name = {result.path.name: result for result in before_results}
    after_by_name = {result.path.name: result for result in after_results}
    names = sorted(before_by_name.keys() & after_by_name.keys())
    before_crossings = sum(len(before_by_name[name].arc_crossings) for name in names)
    after_crossings = sum(len(after_by_name[name].arc_crossings) for name in names)
    before_overlaps = sum(len(before_by_name[name].arc_node_overlaps) for name in names)
    after_overlaps = sum(len(after_by_name[name].arc_node_overlaps) for name in names)

    lines = [
        "# Original versus fCoSE layout",
        "",
        f"Compared **{len(names)} matched SBGN files** using fCoSE seed `{seed}`.",
        "",
        "## Overall result",
        "",
        "| Checker | Original | fCoSE | Assessment |",
        "|---|---:|---:|---|",
        (
            f"| Arc-crossing events | {before_crossings} | {after_crossings} | "
            f"{change_label(before_crossings, after_crossings)} |"
        ),
        (
            f"| Arc-node overlaps | {before_overlaps} | {after_overlaps} | "
            f"{change_label(before_overlaps, after_overlaps)} |"
        ),
        "",
        "## Per-file comparison",
        "",
        (
            "| File | Crossings: original | Crossings: fCoSE | Delta | "
            "Overlaps: original | Overlaps: fCoSE | Delta |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in names:
        before = before_by_name[name]
        after = after_by_name[name]
        before_file_crossings = len(before.arc_crossings)
        after_file_crossings = len(after.arc_crossings)
        before_file_overlaps = len(before.arc_node_overlaps)
        after_file_overlaps = len(after.arc_node_overlaps)
        lines.append(
            f"| `{name}` | {before_file_crossings} | {after_file_crossings} | "
            f"{after_file_crossings - before_file_crossings:+d} | "
            f"{before_file_overlaps} | {after_file_overlaps} | "
            f"{after_file_overlaps - before_file_overlaps:+d} |"
        )
    lines.extend(
        [
            "",
            "## Method",
            "",
            (
                "- Node placement uses Cytoscape.js fCoSE with `quality: proof`, "
                "its other force-layout defaults, and a deterministic seed."
            ),
            (
                "- Original node sizes are preserved. Compound compartment "
                "membership is inferred from original geometric containment "
                "when `compartmentRef` is absent."
            ),
            (
                "- Ports and nested auxiliary glyphs move with their nodes. Old "
                "arc bends are removed and arcs are routed as straight lines "
                "between their updated SBGN endpoints."
            ),
            (
                "- The same checker implementation and definitions are used "
                "before and after. Original files are not modified."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    """Parse arguments, relayout files, and write analysis reports."""

    parser = argparse.ArgumentParser(
        description="Relayout SBGN files with fCoSE and compare checker counts."
    )
    parser.add_argument(
        "-i",
        "--input-directory",
        type=Path,
        default=DEFAULT_INPUT_DIRECTORY,
        help=f"Original SBGN directory (default: {DEFAULT_INPUT_DIRECTORY})",
    )
    parser.add_argument(
        "-o",
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help=f"Relayout output directory (default: {DEFAULT_OUTPUT_DIRECTORY})",
    )
    parser.add_argument(
        "--layout-report",
        type=Path,
        default=DEFAULT_LAYOUT_REPORT,
        help=f"fCoSE-only checker report (default: {DEFAULT_LAYOUT_REPORT})",
    )
    parser.add_argument(
        "--comparison-report",
        type=Path,
        default=DEFAULT_COMPARISON_REPORT,
        help=f"Comparison report (default: {DEFAULT_COMPARISON_REPORT})",
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic fCoSE seed (default: {DEFAULT_SEED})",
    )
    args = parser.parse_args()

    source_files = collect_sbgn_files([args.input_directory])
    if args.output_directory.resolve() == args.input_directory.resolve():
        raise ValueError("Output directory must differ from input directory")

    output_files = []
    for source_path in source_files:
        output_path = args.output_directory / source_path.name
        relayout_file(source_path, output_path, args.seed)
        output_files.append(output_path)

    before_results = tuple(analyze_sbgn_file(path) for path in source_files)
    after_results = tuple(analyze_sbgn_file(path) for path in output_files)
    args.layout_report.parent.mkdir(parents=True, exist_ok=True)
    args.layout_report.write_text(
        markdown_report(
            after_results,
            reproduction_command=(
                "uv run --project python sbgn-layout-checker-py "
                f"{args.output_directory} -o {args.layout_report}"
            ),
        ),
        encoding="utf-8",
    )
    args.comparison_report.parent.mkdir(parents=True, exist_ok=True)
    args.comparison_report.write_text(
        comparison_report(before_results, after_results, args.seed),
        encoding="utf-8",
    )
    print(
        f"Relayout complete: {len(output_files)} files in {args.output_directory}; "
        f"comparison written to {args.comparison_report}"
    )


if __name__ == "__main__":
    main()
