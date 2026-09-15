# Batch 2: original versus libavoid routing

This independent batch contains three random files from each of four file-size
bands. The same 12 maps were checked before and after fixed-node orthogonal
routing. Only arc `<next>` bend points changed.

## Summary

| Metric | Original | libavoid | Change |
|---|---:|---:|---:|
| Arc-crossing events | 88 | 335 | +247 |
| Arc pairs with crossings | 88 | 278 | +190 |
| Arc-node overlaps | 766 | 849 | +83 |

Crossing events increased by 280.7%, and rendered-node overlaps increased by
10.8%. Six files worsened and six tied on each metric; no file improved.

## Per-file comparison

| File | Crossings original | Crossings libavoid | Delta | Overlaps original | Overlaps libavoid | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `R-HSA-201556.sbgn` | 9 | 28 | +19 | 8 | 14 | +6 |
| `R-HSA-3229133.sbgn` | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-351202.sbgn` | 0 | 15 | +15 | 0 | 3 | +3 |
| `R-HSA-3560783.sbgn` | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-6809583.sbgn` | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-888590.sbgn` | 6 | 38 | +32 | 1 | 8 | +7 |
| `R-HSA-9639288.sbgn` | 8 | 23 | +15 | 36 | 42 | +6 |
| `R-HSA-9669936.sbgn` | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-9700206.sbgn` | 0 | 0 | 0 | 0 | 0 | 0 |
| `R-HSA-9793528.sbgn` | 0 | 3 | +3 | 1 | 3 | +2 |
| `R-HSA-9856651.sbgn` | 65 | 228 | +163 | 720 | 779 | +59 |
| `R-HSA-9909648.sbgn` | 0 | 0 | 0 | 0 | 0 | 0 |

See `original_checker.md` and `routed_checker.md` for denominators and checker
definitions. Label-free visual comparisons are in
`../../outputs/batch2/side_by_side_png/`.

