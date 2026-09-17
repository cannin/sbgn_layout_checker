#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pillow>=12.0.0",
# ]
# ///
"""Render annotated PNG examples for every implemented Chapter 4 rule."""

import argparse
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ERROR_COLOR = "#d62728"
WARNING_COLOR = "#e67e22"
SECONDARY_ERROR_COLOR = "#7b2cbf"
SECONDARY_WARNING_COLOR = "#0077b6"
TEXT_COLOR = "#111111"
HEADER_HEIGHT = 82
LEGEND_HEIGHT = 120
MINIMUM_WIDTH = 900
DIAGRAM_SCALE = 2.5
EDGE_LENGTH_TARGET = 3.0
EDGE_LENGTH_TOLERANCE = 0.15
STRETCH_SEARCH_STEPS = 12
TARGET_RULES = (
    "4.2.1",
    "4.2.3",
    "4.2.4",
    "4.2.5",
    "4.2.6",
    "4.2.7",
    "4.2.8",
    "4.2.9",
    "4.3.1",
    "4.3.2",
    "4.3.3",
    "4.3.5",
)
FONT_PATH = Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf")
BOLD_FONT_PATH = Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf")


def run_json(command: list[str]) -> dict[str, Any]:
    """Run a command and decode its JSON output.

    Args:
        command: Command and arguments to execute.

    Returns:
        Parsed JSON object.
    """

    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def choose_examples(
    reports: list[dict[str, Any]],
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    """Select one deterministic finding example for every implemented rule.

    Args:
        reports: Checker file reports.

    Returns:
        Rule-to-report-and-finding mapping.
    """

    selected: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for report in sorted(reports, key=lambda item: item["path"]):
        for finding in report.get("findings", []):
            rule = finding["rule"]
            if rule in TARGET_RULES and rule not in selected:
                selected[rule] = (report, finding)
    missing = sorted(set(TARGET_RULES) - set(selected))
    if missing:
        raise RuntimeError(
            f"no checker finding example for rules: {', '.join(missing)}"
        )
    return selected


def local_name(element: ET.Element) -> str:
    """Return an XML element's namespace-independent name.

    Args:
        element: XML element to inspect.

    Returns:
        Local element name.
    """

    return element.tag.rsplit("}", 1)[-1]


def direct_child(element: ET.Element, name: str) -> ET.Element | None:
    """Return the first direct child with a local name.

    Args:
        element: Parent XML element.
        name: Namespace-independent child name.

    Returns:
        Matching child, or None.
    """

    return next((child for child in element if local_name(child) == name), None)


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Merge overlapping occupied coordinate intervals.

    Args:
        intervals: Coordinate intervals to merge.

    Returns:
        Sorted, non-overlapping intervals.
    """

    merged: list[tuple[float, float]] = []
    for start, end in sorted((min(a, b), max(a, b)) for a, b in intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def axis_transform(
    occupied: list[tuple[float, float]], gap_factor: float
) -> tuple[Any, list[float]]:
    """Build a map that expands whitespace while preserving occupied spans.

    Args:
        occupied: Occupied intervals on one coordinate axis.
        gap_factor: Multiplier applied only to whitespace gaps.

    Returns:
        Coordinate mapping callable and its piecewise boundaries.
    """

    merged = merge_intervals(occupied)
    if not merged:
        return lambda value: value, []
    origin = merged[0][0]

    def transform(value: float) -> float:
        if value < origin:
            return origin - (origin - value) * gap_factor
        occupied_length = sum(
            max(0.0, min(value, end) - start) for start, end in merged if start < value
        )
        total_length = value - origin
        gap_length = max(0.0, total_length - occupied_length)
        return origin + occupied_length + gap_length * gap_factor

    boundaries = sorted({coordinate for interval in merged for coordinate in interval})
    return transform, boundaries


def bbox_values(element: ET.Element) -> tuple[float, float, float, float]:
    """Read x, y, width, and height from an SBGN bounding box.

    Args:
        element: Bounding-box XML element.

    Returns:
        Numeric bounding-box values.
    """

    return (
        float(element.attrib["x"]),
        float(element.attrib["y"]),
        float(element.attrib["w"]),
        float(element.attrib["h"]),
    )


def occupied_intervals(
    root: ET.Element,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Collect rigid diagram spans used to isolate expandable whitespace.

    Compartment boxes are excluded because they enclose most diagram whitespace.

    Args:
        root: Parsed SBGN document.

    Returns:
        Occupied X and Y intervals.
    """

    x_intervals: list[tuple[float, float]] = []
    y_intervals: list[tuple[float, float]] = []
    for glyph in (element for element in root.iter() if local_name(element) == "glyph"):
        if glyph.attrib.get("class") == "compartment":
            continue
        bbox = direct_child(glyph, "bbox")
        if bbox is None:
            continue
        x, y, width, height = bbox_values(bbox)
        x_values = [x, x + width]
        y_values = [y, y + height]
        for child in glyph:
            if local_name(child) == "port":
                x_values.append(float(child.attrib["x"]))
                y_values.append(float(child.attrib["y"]))
            elif local_name(child) == "label":
                label_bbox = direct_child(child, "bbox")
                if label_bbox is not None:
                    lx, ly, lw, lh = bbox_values(label_bbox)
                    x_values.extend((lx, lx + lw))
                    y_values.extend((ly, ly + lh))
        x_intervals.append((min(x_values), max(x_values)))
        y_intervals.append((min(y_values), max(y_values)))
    return x_intervals, y_intervals


def split_segment(
    start: tuple[float, float],
    end: tuple[float, float],
    x_boundaries: list[float],
    y_boundaries: list[float],
) -> list[tuple[float, float]]:
    """Split a segment where a piecewise coordinate transform changes slope.

    Args:
        start: Segment start point.
        end: Segment end point.
        x_boundaries: Vertical transform boundaries.
        y_boundaries: Horizontal transform boundaries.

    Returns:
        Ordered segment points including both endpoints.
    """

    x0, y0 = start
    x1, y1 = end
    parameters: set[float] = {0.0, 1.0}
    if x1 != x0:
        parameters.update(
            (boundary - x0) / (x1 - x0)
            for boundary in x_boundaries
            if 0.0 < (boundary - x0) / (x1 - x0) < 1.0
        )
    if y1 != y0:
        parameters.update(
            (boundary - y0) / (y1 - y0)
            for boundary in y_boundaries
            if 0.0 < (boundary - y0) / (y1 - y0) < 1.0
        )
    return [
        (x0 + (x1 - x0) * parameter, y0 + (y1 - y0) * parameter)
        for parameter in sorted(parameters)
    ]


def stretch_fixture(source: Path, destination: Path, gap_factor: float) -> None:
    """Write a topology-preserving copy with expanded diagram whitespace.

    Args:
        source: Canonical SBGN fixture.
        destination: Temporary stretched SBGN path.
        gap_factor: Multiplier applied to unoccupied coordinate gaps.
    """

    tree = ET.parse(source)
    root = tree.getroot()
    namespace = root.tag.removeprefix("{").split("}", 1)[0]
    ET.register_namespace("", namespace)
    x_intervals, y_intervals = occupied_intervals(root)
    transform_x, x_boundaries = axis_transform(x_intervals, gap_factor)
    transform_y, y_boundaries = axis_transform(y_intervals, gap_factor)

    for bbox in (element for element in root.iter() if local_name(element) == "bbox"):
        x, y, width, height = bbox_values(bbox)
        mapped_x = transform_x(x)
        mapped_y = transform_y(y)
        bbox.attrib.update(
            {
                "x": f"{mapped_x:.6f}",
                "y": f"{mapped_y:.6f}",
                "w": f"{transform_x(x + width) - mapped_x:.6f}",
                "h": f"{transform_y(y + height) - mapped_y:.6f}",
            }
        )
    for port in (element for element in root.iter() if local_name(element) == "port"):
        port.attrib["x"] = f"{transform_x(float(port.attrib['x'])):.6f}"
        port.attrib["y"] = f"{transform_y(float(port.attrib['y'])):.6f}"

    for arc in (element for element in root.iter() if local_name(element) == "arc"):
        point_children = [
            child for child in arc if local_name(child) in {"start", "next", "end"}
        ]
        points = [
            (float(child.attrib["x"]), float(child.attrib["y"]))
            for child in point_children
        ]
        expanded: list[tuple[float, float]] = []
        for start, end in pairwise(points):
            segment = split_segment(start, end, x_boundaries, y_boundaries)
            expanded.extend(segment if not expanded else segment[1:])
        arc_children = list(arc)
        insertion_index = min(arc_children.index(child) for child in point_children)
        for child in point_children:
            arc.remove(child)
        for index, (x, y) in enumerate(expanded):
            name = (
                "start"
                if index == 0
                else "end"
                if index == len(expanded) - 1
                else "next"
            )
            point = ET.Element(
                f"{{{namespace}}}{name}",
                {"x": f"{transform_x(x):.6f}", "y": f"{transform_y(y):.6f}"},
            )
            arc.insert(insertion_index + index, point)
    ET.indent(tree, space="  ")
    tree.write(destination, encoding="utf-8", xml_declaration=True)


def matching_finding(
    report: dict[str, Any], expected: dict[str, Any]
) -> dict[str, Any]:
    """Find the same checker result in a transformed fixture report.

    Args:
        report: Single-file checker report.
        expected: Finding selected from the canonical fixture.

    Returns:
        Exactly matching transformed finding.
    """

    expected_key = (
        expected["rule"],
        expected["kind"],
        tuple(expected.get("elements", [])),
    )
    matches = [
        finding
        for finding in report.get("findings", [])
        if (
            finding["rule"],
            finding["kind"],
            tuple(finding.get("elements", [])),
        )
        == expected_key
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one transformed finding for {expected_key}, found {len(matches)}"
        )
    return matches[0]


def stretch_to_target(
    source: Path,
    destination: Path,
    checker: Path,
    original_report: dict[str, Any],
    finding: dict[str, Any],
) -> tuple[dict[str, Any], float, float]:
    """Expand whitespace until total edge length is approximately tripled.

    Args:
        source: Canonical fixture path.
        destination: Temporary transformed fixture path.
        checker: Layout-checker executable.
        original_report: Canonical checker report.
        finding: Canonical target finding.

    Returns:
        Transformed finding, edge-length ratio, and selected gap factor.
    """

    original_length = float(original_report["metrics"]["total_arc_length"])
    target_length = original_length * EDGE_LENGTH_TARGET
    low = 1.0
    high = 8.0
    transformed_report: dict[str, Any] = {}
    gap_factor = high
    for _ in range(STRETCH_SEARCH_STEPS):
        gap_factor = (low + high) / 2.0
        stretch_fixture(source, destination, gap_factor)
        transformed = run_json([str(checker), "--format", "json", str(destination)])
        transformed_report = transformed["reports"][0]
        matching_finding(transformed_report, finding)
        transformed_length = float(transformed_report["metrics"]["total_arc_length"])
        if transformed_length < target_length:
            low = gap_factor
        else:
            high = gap_factor

    ratio = float(transformed_report["metrics"]["total_arc_length"]) / original_length
    if abs(ratio - EDGE_LENGTH_TARGET) > EDGE_LENGTH_TOLERANCE:
        raise RuntimeError(
            f"edge-length ratio {ratio:.3f} is not near {EDGE_LENGTH_TARGET:.1f}"
        )
    return matching_finding(transformed_report, finding), ratio, gap_factor


def element_bounds(element: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """Return the visible source bounds for a manifest element.

    Args:
        element: Renderer manifest element.

    Returns:
        Source rectangle, or None when no position is available.
    """

    values = [element.get(key) for key in ("x1", "y1", "x2", "y2")]
    if all(value is not None for value in values):
        numbers = [float(value) for value in values]
        return numbers[0], numbers[1], numbers[2], numbers[3]
    if element.get("cx") is not None and element.get("cy") is not None:
        cx = float(element["cx"])
        cy = float(element["cy"])
        return cx - 7, cy - 7, cx + 7, cy + 7
    return None


def annotate_png(
    base_path: Path,
    output_path: Path,
    manifest: dict[str, Any],
    finding: dict[str, Any],
) -> int:
    """Add a header, legend, and finding overlays to a rendered PNG.

    Args:
        base_path: Renderer-produced PNG.
        output_path: Destination annotated PNG.
        manifest: Renderer source-coordinate manifest.
        finding: Checker finding to display.

    Returns:
        Number of visible overlay primitives drawn.
    """

    base = Image.open(base_path).convert("RGB")
    scaled_size = (
        round(base.width * DIAGRAM_SCALE),
        round(base.height * DIAGRAM_SCALE),
    )
    base = base.resize(scaled_size, Image.Resampling.LANCZOS)
    image_width = max(MINIMUM_WIDTH, base.width + 64)
    diagram_x = (image_width - base.width) // 2
    image = Image.new(
        "RGB",
        (image_width, base.height + HEADER_HEIGHT + LEGEND_HEIGHT),
        "white",
    )
    image.paste(base, (diagram_x, HEADER_HEIGHT))
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = ImageFont.truetype(str(BOLD_FONT_PATH), 21)
    bold_font = ImageFont.truetype(str(BOLD_FONT_PATH), 15)
    text_font = ImageFont.truetype(str(FONT_PATH), 13)
    color = ERROR_COLOR if finding["severity"] == "error" else WARNING_COLOR
    canvas = manifest["canvas"]
    x_offset = -float(canvas["min_x"]) + 50.0
    y_offset = -float(canvas["min_y"]) + 50.0
    by_owner: dict[str, list[dict[str, Any]]] = {}
    for element in manifest["elements"]:
        by_owner.setdefault(element.get("owner_id", ""), []).append(element)

    def pixel_point(x: float, y: float) -> tuple[float, float]:
        """Convert one source point to the annotated image coordinate space."""

        return (
            diagram_x + (x + x_offset) * DIAGRAM_SCALE,
            HEADER_HEIGHT + (y + y_offset) * DIAGRAM_SCALE,
        )

    overlay_count = 0
    highlighted_elements = finding.get("elements", [])
    edge_index = 0
    for identifier in highlighted_elements:
        owner_elements = by_owner.get(identifier, [])
        is_edge = any(element.get("kind") == "edge_line" for element in owner_elements)
        element_color = color
        if is_edge and edge_index % 2 == 1:
            element_color = (
                SECONDARY_ERROR_COLOR
                if finding["severity"] == "error"
                else SECONDARY_WARNING_COLOR
            )
        if is_edge:
            edge_index += 1
        edge_elements = [
            element for element in owner_elements if element.get("kind") == "edge_line"
        ]
        if edge_elements:
            pixel_points = [
                pixel_point(
                    float(edge_elements[0]["x1"]), float(edge_elements[0]["y1"])
                )
            ]
            pixel_points.extend(
                pixel_point(float(element["x2"]), float(element["y2"]))
                for element in edge_elements
            )
            draw.line(pixel_points, fill="white", width=13, joint="curve")
            draw.line(pixel_points, fill=element_color, width=8, joint="curve")
            overlay_count += 1
        for element in owner_elements:
            if element.get("kind") == "edge_line":
                continue
            bounds = element_bounds(element)
            if bounds is None:
                continue
            x1, y1, x2, y2 = bounds

            rectangle = (
                diagram_x + (x1 + x_offset) * DIAGRAM_SCALE,
                HEADER_HEIGHT + (y1 + y_offset) * DIAGRAM_SCALE,
                diagram_x + (x2 + x_offset) * DIAGRAM_SCALE,
                HEADER_HEIGHT + (y2 + y_offset) * DIAGRAM_SCALE,
            )
            draw.rectangle(
                rectangle,
                fill=element_color + "26",
                outline=element_color,
                width=4,
            )
            overlay_count += 1

    point = finding.get("point")
    if point:
        x = diagram_x + (float(point["x"]) + x_offset) * DIAGRAM_SCALE
        y = HEADER_HEIGHT + (float(point["y"]) + y_offset) * DIAGRAM_SCALE
        marker_radius = 15
        draw.ellipse(
            (
                x - marker_radius,
                y - marker_radius,
                x + marker_radius,
                y + marker_radius,
            ),
            fill="white",
            outline=TEXT_COLOR,
            width=3,
        )
        draw.line((x - 8, y - 8, x + 8, y + 8), fill=TEXT_COLOR, width=3)
        draw.line((x - 8, y + 8, x + 8, y - 8), fill=TEXT_COLOR, width=3)
        draw.text((x + 20, y - 20), "crossing", fill=TEXT_COLOR, font=text_font)
        overlay_count += 1

    if overlay_count == 0:
        raise RuntimeError(
            f"finding {finding['rule']}:{finding['kind']} has no overlay"
        )

    draw.text(
        (16, 10),
        f"Rule {finding['rule']} - {finding['kind']}",
        fill=TEXT_COLOR,
        font=title_font,
    )
    draw.text((16, 37), finding["severity"].upper(), fill=color, font=bold_font)
    legend_y = base.height + HEADER_HEIGHT + 25
    edge_identifiers = [
        identifier
        for identifier in highlighted_elements
        if any(
            element.get("kind") == "edge_line"
            for element in by_owner.get(identifier, [])
        )
    ]
    if len(edge_identifiers) == 2:
        secondary_color = (
            SECONDARY_ERROR_COLOR
            if finding["severity"] == "error"
            else SECONDARY_WARNING_COLOR
        )
        draw.line((16, legend_y, 50, legend_y), fill=color, width=5)
        draw.text(
            (60, legend_y - 8), edge_identifiers[0], fill=TEXT_COLOR, font=text_font
        )
        draw.line((190, legend_y, 224, legend_y), fill=secondary_color, width=5)
        draw.text(
            (234, legend_y - 8),
            edge_identifiers[1],
            fill=TEXT_COLOR,
            font=text_font,
        )
    else:
        draw.line((16, legend_y, 50, legend_y), fill=color, width=5)
        draw.text(
            (60, legend_y - 8),
            f"Highlighted: {', '.join(highlighted_elements)}",
            fill=TEXT_COLOR,
            font=text_font,
        )
    message = finding["message"]
    if len(message) > 90:
        message = message[:87] + "..."
    draw.text((16, legend_y + 23), message, fill=TEXT_COLOR, font=text_font)
    image.save(output_path, format="PNG", optimize=True)
    return overlay_count


def generate(args: argparse.Namespace) -> None:
    """Generate the rule gallery and machine-readable index.

    Args:
        args: Parsed command-line arguments.
    """

    checker = Path(args.checker).resolve()
    renderer = Path(args.renderer).resolve()
    fixtures = Path(args.fixtures).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = run_json([str(checker), "--format", "json", str(fixtures)])
    selected = choose_examples(report["reports"])
    index: list[dict[str, Any]] = []

    for rule, (file_report, finding) in sorted(selected.items()):
        source = Path(file_report["path"]).resolve()
        stem = f"rule_{rule.replace('.', '_')}_{finding['kind']}"
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            stretched_path = temporary / source.name
            base_png_path = temporary / "base.png"
            manifest_path = temporary / "manifest.json"
            finding, edge_length_ratio, gap_factor = stretch_to_target(
                source,
                stretched_path,
                checker,
                file_report,
                finding,
            )
            subprocess.run(
                [
                    str(renderer),
                    "draw_sbgnml",
                    "--input-path",
                    str(stretched_path),
                    "--output-path",
                    str(base_png_path),
                ],
                check=True,
            )
            subprocess.run(
                [
                    str(renderer),
                    "draw_sbgnml",
                    "--input-path",
                    str(stretched_path),
                    "--generate-render-test-manifest",
                    "--output-path",
                    str(manifest_path),
                ],
                check=True,
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            png_path = output / f"{stem}.png"
            overlay_count = annotate_png(base_png_path, png_path, manifest, finding)
        index.append(
            {
                "rule": rule,
                "severity": finding["severity"],
                "kind": finding["kind"],
                "source": str(source.relative_to(Path.cwd())),
                "png": png_path.name,
                "elements": finding.get("elements", []),
                "overlay_count": overlay_count,
                "edge_length_ratio": round(edge_length_ratio, 3),
                "whitespace_gap_factor": round(gap_factor, 3),
                "message": finding["message"],
            }
        )

    (output / "index.json").write_text(
        json.dumps(index, indent=2) + "\n", encoding="utf-8"
    )
    readme = [
        "# Implemented Chapter 4 rule examples",
        "",
        "Generated PNGs visibly mark the checker elements responsible for one finding from",
        "each implemented rule. Gallery-only copies expand diagram whitespace until total",
        "edge length is approximately 3x the canonical fixture, making interactions easier",
        "to inspect without changing the checked topology. Red denotes requirement errors;",
        "orange denotes warnings.",
        "",
    ]
    for item in index:
        readme.extend(
            [
                f"## Rule {item['rule']}: `{item['kind']}`",
                "",
                f"![Rule {item['rule']} example]({item['png']})",
                "",
                f"- Severity: **{item['severity']}**",
                f"- Source: `{item['source']}`",
                f"- Edge-length scale: **{item['edge_length_ratio']:.3f}x**",
                f"- Finding: {item['message']}",
                "",
            ]
        )
    (output / "README.md").write_text("\n".join(readme), encoding="utf-8")
    print(f"generated {len(index)} annotated rule PNGs in {output}")


def main() -> None:
    """Parse command-line arguments and generate annotated rule examples."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checker", default="go/dist/sbgn_layout_checker")
    parser.add_argument(
        "--renderer", default="sbgn_libavoid/vendor/render_sbgn/go/dist/render_sbgn_go"
    )
    parser.add_argument("--fixtures", default="testdata/chapter4")
    parser.add_argument("--output", default="docs/examples/chapter4")
    generate(parser.parse_args())


if __name__ == "__main__":
    main()
