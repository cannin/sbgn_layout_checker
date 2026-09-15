# SBGN Layout Checker

Checks SBGN Process Description maps against the layout rules in Chapter 4 of
the SBGN PD Level 1 Version 2.1 specification.

The repository is organized as a language-separated monorepo. The Go checker
is the primary implementation; the original Python checker remains available
as its own installable package.

## Quick Start

```bash
go run ./go/cmd/sbgn_layout_checker examples/sbgn_examples
```

Write JSON instead of Markdown:

```bash
go run ./go/cmd/sbgn_layout_checker \
  --format json --output reports/layout.json examples/sbgn_examples
```

Use `--fail-on-error` when a Chapter 4 requirement violation should make the
command exit unsuccessfully.

## Installation

The primary Go checker requires Git, Make, and Go 1.25 or newer. Clone the
repository and build a binary for the current platform:

```bash
git clone https://github.com/cannin/sbgn_layout_checker.git
cd sbgn_layout_checker
make -C go current
```

The binary is written to `go/dist/sbgn_layout_checker`. Run it there or copy it
to a directory on your `PATH`. To install directly into Go's binary directory
instead, run:

```bash
go install ./go/cmd/sbgn_layout_checker
```

The legacy Python checker requires Python 3.14 or newer and
[uv](https://docs.astral.sh/uv/). Install it as an isolated command-line tool:

```bash
uv tool install ./python
sbgn-layout-checker-py examples/sbgn_examples
```

For development, create the locked project environment and run it through uv:

```bash
uv sync --project python
uv run --project python sbgn-layout-checker-py examples/sbgn_examples
```

### Related tools

The Go checker is self-contained and does not require either of the related
repositories below.

[`render_sbgn`](https://github.com/cannin/render_sbgn) is required by the
legacy Python checker. `uv sync --project python` and
`uv tool install ./python` install its pinned Python package automatically. To
install and use the renderer independently from its source repository:

```bash
git clone https://github.com/cannin/render_sbgn.git
uv sync --project render_sbgn/python
uv run --project render_sbgn/python render_sbgn_py --help
```

[`fcose_sbgn`](https://github.com/cannin/fcose_sbgn) is optional. Install it
when you want to add connected glyphs using its fCoSE-style layout adapters;
it is not needed to check an existing layout. The Python adapter can be
installed from its source repository with:

```bash
git clone https://github.com/cannin/fcose_sbgn.git
uv sync --project fcose_sbgn/python
uv run --project fcose_sbgn/python fcose_sbgn_py --help
```

This repository also contains whole-map fCoSE experiments that use
`cytoscape-fcose` directly rather than `fcose_sbgn`. Install their locked Node
dependencies and run the relayout tool from this repository's root:

```bash
npm ci
uv run --project python python/tools/relayout_sbgn_fcose.py
```

## Basic usage

Both files and directories are accepted. Directories are searched recursively
for `.sbgn` files. The Go CLI emits Markdown by default and can emit JSON with
`--format json`.

## Metrics and findings

The checker separates specification findings from descriptive metrics:

- **Errors** are violations of mandatory Chapter 4 requirements.
- **Warnings** identify recommendation issues, such as avoidable node-edge or
  edge-edge crossings. They do not make a map non-conformant.
- **Metrics** describe the supplied geometry without applying an invented
  pass/fail threshold. This is important for the qualitative Section 4.4 goals,
  such as compact layouts, short arcs, and crossings near 90 degrees.

The JSON report emits these metrics for each SBGN-ML file:

| Metric | Meaning |
|---|---|
| `glyphs` | Number of parsed glyphs, including nested glyphs. |
| `arcs` | Number of arcs declared in the input. |
| `resolved_arcs` | Number of arcs whose endpoints and polyline geometry could be resolved. Geometry-dependent measurements use this set. |
| `arc_crossings` | Number of distinct proper edge-edge crossing events. Shared graph endpoints are not crossings. |
| `arc_node_crossings` | Number of times an arc passes through a non-endpoint glyph. |
| `total_arc_length` | Sum of resolved arc-segment lengths in the source coordinate system. Lower values generally indicate more direct routing, but no universal target is imposed. |
| `arc_bends` | Total number of intermediate points on resolved arc polylines. This is a routing-complexity measure, not a conformance score. |
| `minimum_crossing_angle_degrees` | Smallest proper edge-edge crossing angle, in degrees. It is omitted from JSON when no nonzero crossing angle was measured. Angles closer to 90 degrees follow the Section 4.4 recommendation. |
| `drawing_width` / `drawing_height` | Width and height of the bounding box enclosing glyph geometry, in source coordinates. Together they describe drawing size; they are not normalized for map content. |

Metrics are best used to compare alternative layouts of the same map. Raw
values should not be compared as quality scores across maps with different
numbers of glyphs or arcs. Detailed rule coverage and deliberate omissions are
documented in [`docs/chapter4_rules.md`](docs/chapter4_rules.md).

## Configuration

The Go checker has no runtime dependencies. Its SBGN parser, data model, and
endpoint-resolution behavior are adapted from `render_sbgn` at commit
`f2985994e867f7c94d46c52284b555f02ea3af76`; see
[`go/internal/rendersbgn`](go/internal/rendersbgn).

The Python implementation depends on `render-sbgn-py`, pinned in
[`python/pyproject.toml`](python/pyproject.toml).

## Documentation

- [Chapter 4 coverage and underspecified rules](docs/chapter4_rules.md)
- [Two valid negative-layout fixtures per guideline](testdata/chapter4/README.md)
- [Go implementation](go/README.md)
- [Python implementation](python/README.md)

## Testing

```bash
./scripts/test-all.sh
```
