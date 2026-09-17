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
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ERROR_COLOR = "#d62728"
WARNING_COLOR = "#e67e22"
TEXT_COLOR = "#111111"
HEADER_HEIGHT = 82
LEGEND_HEIGHT = 120
MINIMUM_WIDTH = 900
DIAGRAM_SCALE = 2.5
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

    overlay_count = 0
    for identifier in finding.get("elements", []):
        for element in by_owner.get(identifier, []):
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
            draw.rectangle(rectangle, fill=color + "26", outline=color, width=4)
            overlay_count += 1

    point = finding.get("point")
    if point:
        x = diagram_x + (float(point["x"]) + x_offset) * DIAGRAM_SCALE
        y = HEADER_HEIGHT + (float(point["y"]) + y_offset) * DIAGRAM_SCALE
        draw.ellipse(
            (x - 14, y - 14, x + 14, y + 14),
            fill=color + "66",
            outline="white",
            width=3,
        )
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
    draw.line((16, legend_y, 50, legend_y), fill=color, width=5)
    draw.text(
        (60, legend_y - 8),
        f"Highlighted: {', '.join(finding.get('elements', []))}",
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
            base_png_path = temporary / "base.png"
            manifest_path = temporary / "manifest.json"
            subprocess.run(
                [
                    str(renderer),
                    "draw_sbgnml",
                    "--input-path",
                    str(source),
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
                    str(source),
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
        "each implemented rule. Red denotes requirement errors; orange denotes warnings.",
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
