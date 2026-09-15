# fCoSE 1,000-trial benchmark

Ran **1,000 deterministic fCoSE trials** over the same **12 SBGN files** using seeds `20261001` through `20262000`.

## How often fCoSE beat the originals

| Comparison | Trials | Percentage |
|---|---:|---:|
| Fewer arc crossings than 37 | 0 | 0.0% |
| Fewer arc-node overlaps than 94 | 0 | 0.0% |
| Fewer on both metrics | 0 | 0.0% |
| Fewer on at least one metric | 0 | 0.0% |

## Comparison counts

| Metric | Original | Lower | Equal | Higher |
|---|---:|---:|---:|---:|
| Arc crossings | 37 | 0 | 0 | 1,000 |
| Arc-node overlaps | 94 | 0 | 0 | 1,000 |

## Trial distribution

| Metric | Minimum | 5th percentile | Median | Mean | 95th percentile | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| Arc crossings | 335 | 387.9 | 456.0 | 461.6 | 554.0 | 644 |
| Arc-node overlaps | 131 | 157.0 | 186.0 | 187.8 | 226.0 | 264 |

## Best observed trials

- Lowest crossings: seed `20261687` with 335 crossings and 149 overlaps.
- Lowest overlaps: seed `20261233` with 490 crossings and 131 overlaps.

## Method

Each trial used plain Cytoscape.js fCoSE node placement with `quality: proof`, deterministic randomization, preserved node sizes, inferred compound compartments, translated ports and auxiliary glyphs, and straight rerouted arcs. No trial was selected or tuned using checker feedback.

Run `uv run python benchmark_fcose.py` from the project root to reproduce the benchmark.
