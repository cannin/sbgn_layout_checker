# Original versus fCoSE layout

Compared **12 matched SBGN files** using fCoSE seed `20260831`.

## Overall result

| Checker | Original | fCoSE | Assessment |
|---|---:|---:|---|
| Arc-crossing events | 37 | 425 | worse (+388) |
| Arc-node overlaps | 94 | 164 | worse (+70) |

## Per-file comparison

| File | Crossings: original | Crossings: fCoSE | Delta | Overlaps: original | Overlaps: fCoSE | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `R-HSA-112310.sbgn` | 1 | 235 | +234 | 6 | 69 | +63 |
| `R-HSA-2559583.sbgn` | 0 | 0 | +0 | 0 | 0 | +0 |
| `R-HSA-2978092.sbgn` | 0 | 4 | +4 | 0 | 0 | +0 |
| `R-HSA-5610787.sbgn` | 21 | 59 | +38 | 49 | 38 | -11 |
| `R-HSA-5627083.sbgn` | 0 | 0 | +0 | 0 | 0 | +0 |
| `R-HSA-5659735.sbgn` | 0 | 0 | +0 | 0 | 0 | +0 |
| `R-HSA-70635.sbgn` | 3 | 52 | +49 | 17 | 19 | +2 |
| `R-HSA-8963693.sbgn` | 7 | 42 | +35 | 4 | 17 | +13 |
| `R-HSA-9823587.sbgn` | 0 | 0 | +0 | 0 | 0 | +0 |
| `R-HSA-9925563.sbgn` | 0 | 3 | +3 | 0 | 0 | +0 |
| `R-HSA-9932298.sbgn` | 0 | 7 | +7 | 2 | 2 | +0 |
| `R-HSA-9942503.sbgn` | 5 | 23 | +18 | 16 | 19 | +3 |

## Method

- Node placement uses Cytoscape.js fCoSE with `quality: proof`, its other force-layout defaults, and a deterministic seed.
- Original node sizes are preserved. Compound compartment membership is inferred from original geometric containment when `compartmentRef` is absent.
- Ports and nested auxiliary glyphs move with their nodes. Old arc bends are removed and arcs are routed as straight lines between their updated SBGN endpoints.
- The same checker implementation and definitions are used before and after. Original files are not modified.
