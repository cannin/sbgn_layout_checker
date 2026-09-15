# Original versus libavoid routing

The same 12 SBGN files were checked before and after fixed-node orthogonal
routing. Only arc `<next>` bend points changed.

## Summary

| Metric | Original | libavoid | Change |
|---|---:|---:|---:|
| Arc-crossing events | 37 | 215 | +178 |
| Arc pairs with crossings | 32 | 197 | +165 |
| Arc-node overlaps | 94 | 128 | +34 |

The libavoid result is worse for these already laid-out Reactome diagrams:
crossing events increased by 481.1%, and rendered-node overlaps increased by
36.2%. No file improved on either count. Crossing counts worsened in 8 files
and tied in 4; overlap counts worsened in 5 files and tied in 7.

## Per-file comparison

| File | Crossings original | Crossings libavoid | Delta | Overlaps original | Overlaps libavoid | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `R-HSA-112310.sbgn` | 1 | 96 | +95 | 6 | 20 | +14 |
| `R-HSA-2559583.sbgn` | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-2978092.sbgn` | 0 | 1 | +1 | 0 | 0 | 0 |
| `R-HSA-5610787.sbgn` | 21 | 59 | +38 | 49 | 62 | +13 |
| `R-HSA-5627083.sbgn` | 0 | 1 | +1 | 0 | 0 | 0 |
| `R-HSA-5659735.sbgn` | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-70635.sbgn` | 3 | 21 | +18 | 17 | 20 | +3 |
| `R-HSA-8963693.sbgn` | 7 | 17 | +10 | 4 | 7 | +3 |
| `R-HSA-9823587.sbgn` | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-9925563.sbgn` | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-9932298.sbgn` | 0 | 4 | +4 | 2 | 2 | 0 |
| `R-HSA-9942503.sbgn` | 5 | 16 | +11 | 16 | 17 | +1 |

See `original_checker.md` and `routed_checker.md` for denominators, checker
definitions, and exact reproduction commands. Visual comparisons are in
`../outputs/side_by_side_png/`.

## Interpretation

Orthogonal routing is constrained to fixed explicit terminals and fixed nodes.
Many source terminals do not align with their semantic source or target glyph,
and the original hand-authored diagonal routes are unusually direct. Under
those constraints, converting all arcs to orthogonal paths adds shared channels
and crossings. These results do not support replacing the original arc geometry
with this libavoid configuration.

