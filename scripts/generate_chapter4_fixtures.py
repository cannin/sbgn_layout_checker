#!/usr/bin/env python3
"""Generate two semantically valid SBGN-PD fixtures per Chapter 4 guideline."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

NAMESPACE = "http://sbgn.org/libsbgn/0.3"
TEST_NAMESPACE = "https://github.com/cannin/sbgn_layout_checker/test"
OUTPUT_DIRECTORY = Path(__file__).parents[1] / "testdata" / "chapter4"

ET.register_namespace("layout-test", TEST_NAMESPACE)


def bbox(parent: ET.Element, values: tuple[float, float, float, float]) -> None:
    """Append an SBGN bounding box.

    Args:
        parent: XML element receiving the box.
        values: X, Y, width, and height.
    """

    x, y, width, height = values
    ET.SubElement(
        parent,
        "bbox",
        {"x": str(x), "y": str(y), "w": str(width), "h": str(height)},
    )


def add_glyph(map_node: ET.Element, spec: dict[str, Any]) -> ET.Element:
    """Append one glyph and optional nested auxiliary glyphs.

    Args:
        map_node: Parent map or glyph element.
        spec: Declarative glyph fields.

    Returns:
        Created glyph element.
    """

    attrs = {"id": spec["id"], "class": spec["class"]}
    for key in ("compartmentRef", "orientation"):
        if spec.get(key):
            attrs[key] = spec[key]
    glyph = ET.SubElement(map_node, "glyph", attrs)
    if "label" in spec:
        label = ET.SubElement(glyph, "label", {"text": spec["label"]})
        if spec.get("label_bbox"):
            bbox(label, spec["label_bbox"])
    bbox(glyph, spec["bbox"])
    for port_id, x, y in spec.get("ports", []):
        ET.SubElement(glyph, "port", {"id": port_id, "x": str(x), "y": str(y)})
    for child in spec.get("children", []):
        add_glyph(glyph, child)
    return glyph


def add_arc(map_node: ET.Element, spec: dict[str, Any]) -> None:
    """Append one arc and its optional label glyph.

    Args:
        map_node: Parent SBGN map.
        spec: Declarative arc fields.
    """

    arc = ET.SubElement(
        map_node,
        "arc",
        {
            "id": spec["id"],
            "class": spec["class"],
            "source": spec["source"],
            "target": spec["target"],
        },
    )
    points = spec["points"]
    ET.SubElement(arc, "start", {"x": str(points[0][0]), "y": str(points[0][1])})
    for x, y in points[1:-1]:
        ET.SubElement(arc, "next", {"x": str(x), "y": str(y)})
    ET.SubElement(arc, "end", {"x": str(points[-1][0]), "y": str(points[-1][1])})
    if spec.get("label_bbox"):
        auxiliary = ET.SubElement(
            arc,
            "glyph",
            {"id": f"{spec['id']}_label", "class": "cardinality"},
        )
        ET.SubElement(auxiliary, "label", {"text": "1"})
        bbox(auxiliary, spec["label_bbox"])


def base_case(variant: int) -> dict[str, Any]:
    """Return a small semantically valid A-to-B process with modifier C.

    Args:
        variant: One or two, used for small geometric variation.

    Returns:
        Mutable diagram specification.
    """

    shift = float((variant - 1) * 5)
    return {
        "glyphs": [
            {
                "id": "a",
                "class": "macromolecule",
                "label": "A",
                "label_bbox": (15, 26, 10, 8),
                "bbox": (10, 20, 20, 20),
            },
            {
                "id": "p",
                "class": "process",
                "bbox": (70 + shift, 25, 10, 10),
                "ports": [
                    ("p.1", 65 + shift, 30),
                    ("p.2", 85 + shift, 30),
                ],
            },
            {
                "id": "b",
                "class": "macromolecule",
                "label": "B",
                "label_bbox": (105 + shift, 26, 10, 8),
                "bbox": (100 + shift, 20, 20, 20),
            },
            {
                "id": "c",
                "class": "macromolecule",
                "label": "C",
                "label_bbox": (72 + shift, 1, 10, 8),
                "bbox": (67 + shift, -5, 20, 20),
            },
        ],
        "arcs": [
            {
                "id": "consume",
                "class": "consumption",
                "source": "a",
                "target": "p.1",
                "points": [(30, 30), (65 + shift, 30)],
            },
            {
                "id": "produce",
                "class": "production",
                "source": "p.2",
                "target": "b",
                "points": [(85 + shift, 30), (100 + shift, 30)],
            },
            {
                "id": "stimulate",
                "class": "stimulation",
                "source": "c",
                "target": "p",
                "points": [(77 + shift, 15), (75 + shift, 25)],
            },
        ],
    }


def apply_scenario(case: dict[str, Any], slug: str, variant: int) -> None:
    """Mutate a baseline into one targeted bad-layout scenario.

    Args:
        case: Mutable baseline diagram.
        slug: Stable guideline scenario name.
        variant: One or two.
    """

    glyphs = {glyph["id"]: glyph for glyph in case["glyphs"]}
    arcs = {arc["id"]: arc for arc in case["arcs"]}
    delta = float(variant * 2)
    if slug == "4_2_1_node_overlap":
        glyphs["b"]["bbox"] = (25 + delta, 25, 20, 20)
        glyphs["b"]["label_bbox"] = (30 + delta, 31, 10, 8)
    elif slug in {"4_2_2_edge_z_order", "4_3_1_node_edge_crossing"}:
        glyphs["c"]["bbox"] = (40 + delta, 20, 20, 20)
        glyphs["c"]["label_bbox"] = (45 + delta, 26, 10, 8)
        arcs["stimulate"]["points"] = [(50 + delta, 20), (75 + (variant - 1) * 5, 25)]
    elif slug == "4_2_3_node_border_edge_overlap":
        glyphs["c"]["bbox"] = (38 + delta, 30, 20, 20)
        glyphs["c"]["label_bbox"] = (43 + delta, 36, 10, 8)
        arcs["stimulate"]["points"] = [(48 + delta, 30), (75 + (variant - 1) * 5, 25)]
    elif slug == "4_2_4_edge_overlap":
        case["glyphs"].extend(
            [
                {
                    "id": "q",
                    "class": "process",
                    "bbox": (70, 60, 10, 10),
                    "ports": [("q.1", 65, 65), ("q.2", 85, 65)],
                },
                {
                    "id": "d",
                    "class": "macromolecule",
                    "label": "D",
                    "label_bbox": (105, 61, 10, 8),
                    "bbox": (100, 55, 20, 20),
                },
            ]
        )
        case["arcs"].extend(
            [
                {
                    "id": "consume_second",
                    "class": "consumption",
                    "source": "c",
                    "target": "q.1",
                    "points": [(40 + delta, 30), (58 + delta, 30), (65, 65)],
                },
                {
                    "id": "produce_second",
                    "class": "production",
                    "source": "q.2",
                    "target": "d",
                    "points": [(85, 65), (100, 65)],
                },
            ]
        )
    elif slug == "4_2_5_diagonal_orientation":
        glyphs["a"]["orientation"] = "diagonal"
        glyphs["a"]["bbox"] = (10, 20, 28, 12)
    elif slug == "4_2_6_process_attachment":
        glyphs["p"]["ports"] = [
            ("p.1", 65 + (variant - 1) * 5, 27 + variant),
            ("p.2", 85 + (variant - 1) * 5, 33 - variant),
        ]
    elif slug == "4_2_7_node_labels":
        glyphs["a"]["label_bbox"] = (32 + delta, 22, 10, 8)
    elif slug == "4_2_8_edge_labels":
        arcs["consume"]["label_bbox"] = (12 + delta, 22, 12, 10)
    elif slug == "4_2_9_compartments":
        compartment = {
            "id": "cell",
            "class": "compartment",
            "label": "C",
            "label_bbox": (5, 70, 10, 8),
            "bbox": (0, 0, 130, 80),
        }
        case["glyphs"].insert(0, compartment)
        for glyph in case["glyphs"]:
            if glyph["id"] != "cell":
                glyph["compartmentRef"] = "cell"
        glyphs["p"]["bbox"] = (145 + delta, 25, 10, 10)
        glyphs["p"]["ports"] = [("p.1", 140 + delta, 30), ("p.2", 160 + delta, 30)]
        arcs["consume"]["points"] = [(30, 30), (140 + delta, 30)]
        arcs["produce"]["points"] = [(160 + delta, 30), (100 + (variant - 1) * 5, 30)]
        arcs["stimulate"]["points"] = [(77 + (variant - 1) * 5, 15), (150 + delta, 25)]
    elif slug == "4_3_2_label_quality":
        glyphs["a"]["label_bbox"] = (25 + delta, 26, 12, 8)
    elif slug in {"4_3_3_edge_crossings", "4_4_crossing_angle"}:
        y_offset = 1.0 if slug == "4_4_crossing_angle" else 15.0
        arcs["stimulate"]["points"] = [
            (40, 30 - y_offset),
            (62, 30 + y_offset),
            (75 + (variant - 1) * 5, 25),
        ]
    elif slug == "4_3_4_branch_proximity":
        glyphs["p"]["class"] = "association"
        arcs["consume"]["points"] = [(30, 30), (35, 30), (65 + (variant - 1) * 5, 30)]
        arcs["produce"]["points"] = [
            (85 + (variant - 1) * 5, 30),
            (140 + delta, 30),
            (100 + (variant - 1) * 5, 30),
        ]
    elif slug == "4_3_5_unit_information":
        glyphs["a"]["children"] = [
            {
                "id": "a_info",
                "class": "unit of information",
                "label": "A",
                "bbox": (100 + (variant - 1) * 5, 20, 12, 10),
            }
        ]
    elif slug in {"4_4_compactness", "4_4_edge_length", "4_4_proximity"}:
        glyphs["b"]["bbox"] = (500 + variant * 100, 20, 20, 20)
        glyphs["b"]["label_bbox"] = (505 + variant * 100, 26, 10, 8)
        arcs["produce"]["points"] = [
            (85 + (variant - 1) * 5, 30),
            (500 + variant * 100, 30),
        ]
    elif slug == "4_4_edge_bends":
        arcs["consume"]["points"] = [
            (30, 30),
            (38, 10),
            (45, 50),
            (52, 10),
            (58, 50),
            (65 + (variant - 1) * 5, 30),
        ]
    elif slug == "4_4_similarity_symmetry":
        glyphs["b"]["bbox"] = (100, 55 + delta, 20, 20)
        glyphs["b"]["label_bbox"] = (105, 61 + delta, 10, 8)
        arcs["produce"]["points"] = [(85 + (variant - 1) * 5, 30), (100, 65 + delta)]
    elif slug == "4_4_direction":
        glyphs["b"]["bbox"] = (15 + delta, 70, 20, 20)
        glyphs["b"]["label_bbox"] = (20 + delta, 76, 10, 8)
        arcs["produce"]["points"] = [(85 + (variant - 1) * 5, 30), (25 + delta, 70)]
    elif slug == "4_4_compartment_shading":
        compartments = [
            {
                "id": "left",
                "class": "compartment",
                "label": "A",
                "bbox": (0, -15, 65, 75),
            },
            {
                "id": "right",
                "class": "compartment",
                "label": "B",
                "bbox": (90, -15, 45, 75),
            },
        ]
        case["glyphs"] = compartments + case["glyphs"]
        glyphs["a"]["compartmentRef"] = "left"
        glyphs["c"]["compartmentRef"] = "left"
        glyphs["p"]["compartmentRef"] = "left"
        glyphs["b"]["compartmentRef"] = "right"


def write_case(
    slug: str, section: str, expected_kind: str, variant: int
) -> dict[str, str]:
    """Generate one fixture and return its manifest record.

    Args:
        slug: Stable guideline scenario name.
        section: Chapter 4 section or bullet identifier.
        expected_kind: Go finding kind, or an empty string for metric/manual cases.
        variant: One or two.

    Returns:
        JSON-compatible fixture metadata.
    """

    case = base_case(variant)
    apply_scenario(case, slug, variant)
    root = ET.Element("sbgn", {"xmlns": NAMESPACE})
    map_node = ET.SubElement(
        root,
        "map",
        {"id": f"{slug}_{variant}", "language": "process description"},
    )
    extension = ET.SubElement(map_node, "extension")
    ET.SubElement(
        extension,
        f"{{{TEST_NAMESPACE}}}expectedViolation",
        {
            "section": section,
            "scenario": slug,
            "variant": str(variant),
            "checkerFinding": expected_kind,
        },
    )
    for glyph in case["glyphs"]:
        add_glyph(map_node, glyph)
    for arc in case["arcs"]:
        add_arc(map_node, arc)
    ET.indent(root, space="  ")
    path = OUTPUT_DIRECTORY / f"{slug}_{variant}.sbgn"
    ET.ElementTree(root).write(path, encoding="unicode", xml_declaration=True)
    return {
        "path": path.name,
        "section": section,
        "expected_kind": expected_kind,
    }


def main() -> None:
    """Generate all fixtures and their machine-readable expectation manifest."""

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    scenarios = [
        ("4_2_1_node_overlap", "4.2.1", "node_overlap"),
        ("4_2_2_edge_z_order", "4.2.2", ""),
        ("4_2_3_node_border_edge_overlap", "4.2.3", "node_border_edge_overlap"),
        ("4_2_4_edge_overlap", "4.2.4", "edge_edge_overlap_or_touch"),
        ("4_2_5_diagonal_orientation", "4.2.5", "invalid_node_orientation"),
        ("4_2_6_process_attachment", "4.2.6", "process_flow_not_centered"),
        ("4_2_7_node_labels", "4.2.7", "node_label_outside_node"),
        ("4_2_8_edge_labels", "4.2.8", "edge_label_overlaps_node"),
        ("4_2_9_compartments", "4.2.9", "process_outside_participant_compartment"),
        ("4_3_1_node_edge_crossing", "4.3.1", "node_edge_crossing"),
        ("4_3_2_label_quality", "4.3.2", "node_label_not_fully_inside"),
        ("4_3_3_edge_crossings", "4.3.3", "edge_crossing"),
        ("4_3_4_branch_proximity", "4.3.4", ""),
        ("4_3_5_unit_information", "4.3.5", "unit_of_information_overlap"),
        ("4_4_crossing_angle", "4.4 crossing angle", "edge_crossing"),
        ("4_4_compactness", "4.4 compactness", ""),
        ("4_4_edge_length", "4.4 edge length", ""),
        ("4_4_edge_bends", "4.4 edge bends", ""),
        ("4_4_similarity_symmetry", "4.4 similarity and symmetry", ""),
        ("4_4_proximity", "4.4 proximity", ""),
        ("4_4_direction", "4.4 direction", ""),
        ("4_4_compartment_shading", "4.4 compartment shading", ""),
    ]
    manifest = [
        write_case(slug, section, expected_kind, variant)
        for slug, section, expected_kind in scenarios
        for variant in (1, 2)
    ]
    manifest_path = OUTPUT_DIRECTORY / "cases.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
