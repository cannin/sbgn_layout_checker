# Original versus fCoSE layout

Compared **12 matched SBGN files** using fCoSE seed `20260901`.

## Overall result

| Checker | Original | fCoSE | Assessment |
|---|---:|---:|---|
| Arc-crossing events | 37 | 492 | worse (+455) |
| Arc-node overlaps | 94 | 153 | worse (+59) |

## Per-file comparison

| File | Crossings: original | Crossings: fCoSE | Delta | Overlaps: original | Overlaps: fCoSE | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `R-HSA-112310.sbgn` | 1 | 302 | +301 | 6 | 68 | +62 |
| `R-HSA-2559583.sbgn` | 0 | 0 | +0 | 0 | 0 | +0 |
| `R-HSA-2978092.sbgn` | 0 | 2 | +2 | 0 | 0 | +0 |
| `R-HSA-5610787.sbgn` | 21 | 73 | +52 | 49 | 32 | -17 |
| `R-HSA-5627083.sbgn` | 0 | 0 | +0 | 0 | 0 | +0 |
| `R-HSA-5659735.sbgn` | 0 | 0 | +0 | 0 | 0 | +0 |
| `R-HSA-70635.sbgn` | 3 | 43 | +40 | 17 | 18 | +1 |
| `R-HSA-8963693.sbgn` | 7 | 40 | +33 | 4 | 16 | +12 |
| `R-HSA-9823587.sbgn` | 0 | 0 | +0 | 0 | 0 | +0 |
| `R-HSA-9925563.sbgn` | 0 | 4 | +4 | 0 | 0 | +0 |
| `R-HSA-9932298.sbgn` | 0 | 8 | +8 | 2 | 4 | +2 |
| `R-HSA-9942503.sbgn` | 5 | 20 | +15 | 16 | 15 | -1 |

## Method

- Node placement uses Cytoscape.js fCoSE with `quality: proof`, its other force-layout defaults, and a deterministic seed.
- Original node sizes are preserved. Compound compartment membership is inferred from original geometric containment when `compartmentRef` is absent.
- Ports and nested auxiliary glyphs move with their nodes. Old arc bends are removed and arcs are routed as straight lines between their updated SBGN endpoints.
- The same checker implementation and definitions are used before and after. Original files are not modified.
