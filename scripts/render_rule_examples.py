#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pillow>=12.0.0",
# ]
# ///
"""Render annotated PNG examples for every implemented Chapter 4 rule."""

import json
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parents[1]
FIXTURE_DIRECTORY = ROOT / "testdata" / "chapter4"
OUTPUT_DIRECTORY = ROOT / "docs" / "images" / "rules"
PADDING = 50.0
ANNOTATION_COLOR = "#d62728"


def local_name(tag: str) -> str:
    """Return an XML tag without its namespace.

    Args:
        tag: Potentially namespaced XML tag.

    Returns:
        Local tag name.
    """

    return tag.rsplit("}", 1)[-1]


def child(element: ET.Element, name: str) -> ET.Element | None:
    """Find an immediate child by local tag name.

    Args:
        element: Parent XML element.
        name: Local child name.

    Returns:
        Matching child, if present.
    """

    return next((item for item in element if local_name(item.tag) == name), None)


def coordinates(root: ET.Element) -> Iterable[tuple[float, float]]:
    """Yield diagram coordinates used to determine renderer translation.

    Args:
        root: Parsed SBGN document root.

    Returns:
        Iterator of coordinate pairs.
    """

    for element in root.iter():
        name = local_name(element.tag)
        if name == "bbox" or name in {"start", "next", "end", "port"}:
            yield float(element.attrib["x"]), float(element.attrib["y"])


def element_geometry(root: ET.Element) -> dict[str, list[tuple[float, float]]]:
    """Map glyph and arc IDs to points enclosing their geometry.

    Args:
        root: Parsed SBGN document root.

    Returns:
        Element IDs mapped to bounding or polyline points.
    """

    geometry: dict[str, list[tuple[float, float]]] = {}
    for element in root.iter():
        element_id = element.attrib.get("id")
        if not element_id:
            continue
        name = local_name(element.tag)
        if name == "glyph":
            box = child(element, "bbox")
            if box is not None:
                x = float(box.attrib["x"])
                y = float(box.attrib["y"])
                width = float(box.attrib["w"])
                height = float(box.attrib["h"])
                geometry[element_id] = [(x, y), (x + width, y + height)]
        elif name == "arc":
            points = [
                (float(item.attrib["x"]), float(item.attrib["y"]))
                for item in element
                if local_name(item.tag) in {"start", "next", "end"}
            ]
            if points:
                geometry[element_id] = points
    return geometry


def annotate(source: Path, target: Path, finding: dict[str, Any]) -> None:
    """Overlay one checker's finding on its existing rendered fixture.

    Args:
        source: SBGN fixture path.
        target: Annotated PNG destination.
        finding: Matching Go checker finding.
    """

    root = ET.parse(source).getroot()
    points = list(coordinates(root))
    minimum_x = min(point[0] for point in points)
    minimum_y = min(point[1] for point in points)
    base = Image.open(source.with_suffix(".png")).convert("RGB")
    scale = base.width / float(
        ET.parse(source.with_suffix(".svg"))
        .getroot()
        .attrib["width"]
        .removesuffix("px")
    )
    banner_height = 120
    image = Image.new("RGB", (base.width, base.height + banner_height), "white")
    image.paste(base, (0, banner_height))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", 42
    )
    bold = ImageFont.truetype(
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", 48
    )
    rule = str(finding["rule"])
    kind = str(finding["kind"]).replace("_", " ")
    draw.rectangle((0, 0, image.width - 1, banner_height - 1), fill="#fff4f4")
    draw.text((24, 12), f"Rule {rule}", fill=ANNOTATION_COLOR, font=bold)
    draw.text((260, 18), kind, fill="#222222", font=font)
    draw.line(
        (0, banner_height - 4, image.width, banner_height - 4),
        fill=ANNOTATION_COLOR,
        width=8,
    )

    geometry = element_geometry(root)

    def transform(point: tuple[float, float]) -> tuple[float, float]:
        return (
            (point[0] - minimum_x + PADDING) * scale,
            (point[1] - minimum_y + PADDING) * scale + banner_height,
        )

    point = finding.get("point")
    if point:
        center = transform((float(point["x"]), float(point["y"])))
        radius = 30
        draw.ellipse(
            (
                center[0] - radius,
                center[1] - radius,
                center[0] + radius,
                center[1] + radius,
            ),
            outline=ANNOTATION_COLOR,
            width=10,
        )
    else:
        for element_id in finding.get("elements", []):
            element_points = geometry.get(str(element_id))
            if not element_points:
                continue
            transformed = [transform(item) for item in element_points]
            left = min(item[0] for item in transformed) - 14
            top = min(item[1] for item in transformed) - 14
            right = max(item[0] for item in transformed) + 14
            bottom = max(item[1] for item in transformed) + 14
            draw.rounded_rectangle(
                (left, top, right, bottom),
                radius=18,
                outline=ANNOTATION_COLOR,
                width=10,
            )
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)


def main() -> None:
    """Generate one annotated PNG for each implemented fixture rule."""

    manifest = json.loads((FIXTURE_DIRECTORY / "cases.json").read_text())
    report = json.loads(
        subprocess.run(
            [
                "go",
                "run",
                "./go/cmd/sbgn_layout_checker",
                "--format",
                "json",
                str(FIXTURE_DIRECTORY),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    reports = {Path(item["path"]).name: item for item in report["reports"]}
    selected_rules: set[str] = set()
    generated: list[dict[str, str]] = []
    for case in manifest:
        expected_kind = case["expected_kind"]
        if not expected_kind:
            continue
        findings = [
            finding
            for finding in reports[case["path"]]["findings"]
            if finding["kind"] == expected_kind
        ]
        if not findings:
            raise SystemExit(f"Missing {expected_kind} finding for {case['path']}")
        finding = findings[0]
        if finding["rule"] in selected_rules:
            continue
        selected_rules.add(finding["rule"])
        target_name = f"rule_{finding['rule'].replace('.', '_')}.png"
        annotate(
            FIXTURE_DIRECTORY / case["path"], OUTPUT_DIRECTORY / target_name, finding
        )
        generated.append(
            {
                "rule": finding["rule"],
                "kind": finding["kind"],
                "source": case["path"],
                "image": target_name,
            }
        )
    (OUTPUT_DIRECTORY / "manifest.json").write_text(
        json.dumps(generated, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Rendered {len(generated)} annotated rule examples.")


if __name__ == "__main__":
    main()
