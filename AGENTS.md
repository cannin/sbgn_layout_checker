# Repository Guidelines

## Architecture

- `go/` is the primary checker implementation and must not invoke Python.
- `python/` contains the independently installable legacy Python checker.
- `examples/`, `reports/`, and `pd_level1_version2_1.pdf` are shared assets.
- `go/internal/rendersbgn/` is the attributed extraction of reusable Go parser
  and path-resolution logic from `render_sbgn`. Keep its behavior aligned with
  the source commit documented in the root README.
- Do not couple one language implementation to another language runtime.

## Commands

Run all maintained tests:

```bash
./scripts/test-all.sh
```

Run implementation-specific checks:

```bash
(cd go && go test ./...)
(cd python && uv run pytest)
(cd python && uv run ruff check .)
./scripts/validate-fixtures.sh
```

Build all Go release targets and the current-system binary:

```bash
make -C go
```

## Editing constraints

- Keep Chapter 4 rule IDs on every finding.
- Do not turn qualitative recommendations into pass/fail checks without a
  documented threshold in `docs/chapter4_rules.md`.
- Preserve explicit distinctions between requirement errors, recommendation
  warnings, metrics, and rules that cannot be derived from SBGN-ML.
- Add focused unit tests for geometry changes and run the integration fixture
  test against `examples/sbgn_examples`.
- Use `gofmt` for Go and Ruff for Python.

## Pitfalls

- SBGN-ML label boxes are optional; missing geometry cannot be inferred
  portably from text alone.
- Compartment ownership may be explicit (`compartmentRef`), nested, or only
  visually inferable. Explicit ownership takes precedence.
- Legitimate arcs can share a process port. Do not report their common graph
  endpoint as an edge-edge touch.
- Bounding boxes conservatively approximate rounded and irregular glyphs.
