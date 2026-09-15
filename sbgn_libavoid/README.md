# Fixed-node SBGN routing with libavoid

This Rust tool replaces only SBGN arc `<next>` bend points with orthogonal
routes. Glyph positions, sizes, orientations, identifiers, arc endpoints, and
all biological semantics remain unchanged.

## Run the router

From `sbgn_libavoid/`:

```bash
cargo run --release -- route \
  --input ../examples/sbgn_examples \
  --output outputs/routed
```

The default routing configuration is:

| Parameter | Default |
|---|---:|
| Shape buffer distance | 4 |
| Ideal nudging distance | 4 |
| Segment penalty | 10 |
| Crossing penalty | 200 |

All values are exposed as command-line options. Every non-compartment glyph
bounding box is registered as a fixed obstacle. Compartments are containers,
so treating their full interiors as obstacles would make their contents
unroutable. Explicit `<start>` and `<end>` coordinates are fixed. The returned
route is simplified by removing consecutive duplicates and collinear middle
points, and only its interior points are written as `<next>` elements.

The routing layer uses `compute_edge_routes(&Graph, &RoutingConfig)` to return
routes without mutable access to the graph. It snapshots node geometry before
and after libavoid, and the XML layer separately verifies exact glyph bounding
box strings and a semantic fingerprint before applying routes.

## Check the layouts

From the project root:

```bash
uv run --project python sbgn-layout-checker-py examples/sbgn_examples \
  --output sbgn_libavoid/reports/original_checker.md
uv run --project python sbgn-layout-checker-py sbgn_libavoid/outputs/routed \
  --output sbgn_libavoid/reports/routed_checker.md
```

The combined interpretation is in `reports/comparison.md`.

## Render original and routed diagrams

The vendored renderer is pinned to `cannin/render_sbgn` commit
`f0b98cfc92ad1db353aaf4aa495e488740b88c1d`. Its Rust drawing path has a small
local fix so parsed `<next>` points are drawn as a polyline and explicit SBGN
terminals take precedence over renderer-side port snapping.

```bash
cd vendor/render_sbgn/rust
cargo build --release
```

The generated artifacts are organized as follows:

- `outputs/rendered_original_png/`: 12 original Rust renders.
- `outputs/rendered_png/`: 12 libavoid-routed Rust renders.
- `outputs/side_by_side_png/`: 12 label-free original/libavoid comparisons.
- `outputs/batch2/`: the same three output groups plus routed XML for the
  independent second batch.

Side-by-side source renders use the local renderer's `--no-labels` option. The
`Original` and `libavoid` panel headings remain visible, but all diagram labels
are suppressed so arc geometry is easier to compare.

## Tests

```bash
cargo fmt --check
cargo test
```

The seven router tests cover exact node immutability, obstacle clearance,
orthogonality, duplicate/collinear simplification, fixed endpoints, multiple
connectors, and an SBGN round trip in which only arc bend elements may change.

## libavoid-rust limitations encountered

- `libavoid = "0.1.0"` was not available from crates.io, so `Cargo.toml` pins
  the documented repository at commit
  `f72fe0b6a541b8f32a1c160d38c889f0c697eecd`.
- The current port can emit a direct diagonal fallback for some dense inputs.
  Those exceptional segments are converted to the less obstructed of the two
  equivalent Manhattan elbows, then revalidated for orthogonality and raw
  bounding-box avoidance.
- Orthogonal route nudging entered raw obstacles on this corpus, so
  `NudgeOrthogonalRoutes` is conservatively disabled. Shared-path penalties and
  crossing costs remain enabled.
- Some source files place fixed terminals inside nested unit-of-information
  glyphs. Such nested glyphs are recognized as part of the terminal glyph;
  preserving the explicit endpoint takes priority over clearance at that
  terminal.
- The Python checker uses rendered rectangles that can be larger than the raw
  SBGN `<bbox>`. Consequently its overlap count is not identical to the router's
  enforced raw-box invariant.
