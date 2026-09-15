# SBGN layout checker report

Analyzed **12 SBGN files**.

## Summary

| Metric | Count | Rate |
|---|---:|---:|
| Parsed glyphs | 564 | - |
| Node glyphs checked | 505 | - |
| Parsed arcs | 557 | - |
| Arc paths checked | 557 | - |
| Arc-crossing events | 37 | - |
| Arc pairs with crossings | 32 / 30470 | 0.11% |
| Arc-node overlaps | 94 / 53247 | 0.18% |

## Per-file counts

| File | Nodes checked | Arcs checked | Arc pairs | Crossing events | Crossing pairs | Arc-node pairs | Arc-node overlaps |
|---|---:|---:|---:|---:|---:|---:|---:|
| `R-HSA-112310.sbgn` | 157 | 178 | 15753 | 1 | 1 | 27590 | 6 |
| `R-HSA-2559583.sbgn` | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-2978092.sbgn` | 7 | 6 | 15 | 0 | 0 | 30 | 0 |
| `R-HSA-5610787.sbgn` | 110 | 124 | 7626 | 21 | 16 | 13392 | 49 |
| `R-HSA-5627083.sbgn` | 8 | 9 | 36 | 0 | 0 | 54 | 0 |
| `R-HSA-5659735.sbgn` | 4 | 3 | 3 | 0 | 0 | 6 | 0 |
| `R-HSA-70635.sbgn` | 73 | 81 | 3240 | 3 | 3 | 5751 | 17 |
| `R-HSA-8963693.sbgn` | 53 | 61 | 1830 | 7 | 7 | 3111 | 4 |
| `R-HSA-9823587.sbgn` | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-9925563.sbgn` | 8 | 8 | 28 | 0 | 0 | 48 | 0 |
| `R-HSA-9932298.sbgn` | 31 | 34 | 561 | 0 | 0 | 986 | 2 |
| `R-HSA-9942503.sbgn` | 45 | 53 | 1378 | 5 | 5 | 2279 | 16 |

## Checker definitions

- SBGN parsing, port-aware path resolution, line endpoint adjustment, hidden-node filtering, and rendered node rectangles come from [`render_sbgn_py`](https://github.com/cannin/render_sbgn/tree/f0b98cfc92ad1db353aaf4aa495e488740b88c1d/python).
- **Arc crossing:** a proper intersection inside two polyline segments. Shared endpoints, boundary touches, tangent contacts, and collinear overlaps are not counted. A pair can contribute more than one crossing event.
- **Arc-node overlap:** an arc centerline enters the open interior of a rendered node bounding rectangle. The arc's source and target nodes are excluded, as are compartment backgrounds and glyph classes hidden as standalone renderer nodes. Each arc-node pair is counted at most once.
- Rates use arc pairs within each file and eligible non-endpoint arc-node pairs as their denominators.

## Interpretation

Both checks are geometric layout checks, not SBGN semantic validation. Node overlap uses rendered bounding rectangles, so it is intentionally conservative around rounded or irregular glyph corners.

## Reproduction

Run `uv run python analyze_sbgn_layout.py` from the project root.
