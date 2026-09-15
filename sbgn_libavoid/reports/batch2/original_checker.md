# SBGN layout checker report

Analyzed **12 SBGN files**.

## Summary

| Metric | Count | Rate |
|---|---:|---:|
| Parsed glyphs | 765 | - |
| Node glyphs checked | 703 | - |
| Parsed arcs | 789 | - |
| Arc paths checked | 789 | - |
| Arc-crossing events | 88 | - |
| Arc pairs with crossings | 88 / 85488 | 0.10% |
| Arc-node overlaps | 766 / 148604 | 0.52% |

## Per-file counts

| File | Nodes checked | Arcs checked | Arc pairs | Crossing events | Crossing pairs | Arc-node pairs | Arc-node overlaps |
|---|---:|---:|---:|---:|---:|---:|---:|
| `R-HSA-201556.sbgn` | 141 | 154 | 11781 | 9 | 9 | 21406 | 8 |
| `R-HSA-3229133.sbgn` | 5 | 3 | 3 | 0 | 0 | 9 | 0 |
| `R-HSA-351202.sbgn` | 75 | 91 | 4095 | 0 | 0 | 6643 | 0 |
| `R-HSA-3560783.sbgn` | 4 | 3 | 3 | 0 | 0 | 6 | 0 |
| `R-HSA-6809583.sbgn` | 3 | 2 | 1 | 0 | 0 | 2 | 0 |
| `R-HSA-888590.sbgn` | 54 | 63 | 1953 | 6 | 6 | 3276 | 1 |
| `R-HSA-9639288.sbgn` | 44 | 53 | 1378 | 8 | 8 | 2226 | 36 |
| `R-HSA-9669936.sbgn` | 3 | 2 | 1 | 0 | 0 | 2 | 0 |
| `R-HSA-9700206.sbgn` | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-9793528.sbgn` | 55 | 58 | 1653 | 0 | 0 | 3074 | 1 |
| `R-HSA-9856651.sbgn` | 313 | 360 | 64620 | 65 | 65 | 111960 | 720 |
| `R-HSA-9909648.sbgn` | 3 | 0 | 0 | 0 | 0 | 0 | 0 |

## Checker definitions

- SBGN parsing, port-aware path resolution, line endpoint adjustment, hidden-node filtering, and rendered node rectangles come from [`render_sbgn_py`](https://github.com/cannin/render_sbgn/tree/f0b98cfc92ad1db353aaf4aa495e488740b88c1d/python).
- **Arc crossing:** a proper intersection inside two polyline segments. Shared endpoints, boundary touches, tangent contacts, and collinear overlaps are not counted. A pair can contribute more than one crossing event.
- **Arc-node overlap:** an arc centerline enters the open interior of a rendered node bounding rectangle. The arc's source and target nodes are excluded, as are compartment backgrounds and glyph classes hidden as standalone renderer nodes. Each arc-node pair is counted at most once.
- Rates use arc pairs within each file and eligible non-endpoint arc-node pairs as their denominators.

## Interpretation

Both checks are geometric layout checks, not SBGN semantic validation. Node overlap uses rendered bounding rectangles, so it is intentionally conservative around rounded or irregular glyph corners.

## Reproduction

Run `uv run python analyze_sbgn_layout.py examples/sbgn_examples_batch2 --output sbgn_libavoid/reports/batch2/original_checker.md` from the project root.
