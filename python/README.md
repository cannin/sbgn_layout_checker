# Python implementation

This directory contains the original Python layout checker and its dependency
metadata.

```bash
uv sync
uv run pytest
uv run sbgn-layout-checker-py ../examples/sbgn_examples \
  --output ../reports/sbgn_layout_report.md
```

The Python checker currently retains its original two checks: proper arc
crossings and non-endpoint arc-node overlaps. The Go implementation at
`../go/` is the primary Chapter 4 checker.
