# Go implementation

The dependency-free Go checker is the primary implementation.

```bash
go run ./cmd/sbgn_layout_checker ../examples/sbgn_examples
go test ./...
make
```

`make` tests first, builds all supported release targets, then leaves the
current-system binary at `dist/sbgn_layout_checker`.

Release artifacts are:

- `dist/sbgn_layout_checker-linux-amd64`
- `dist/sbgn_layout_checker-linux-arm64`
- `dist/sbgn_layout_checker-darwin-amd64`
- `dist/sbgn_layout_checker-darwin-arm64`
- `dist/sbgn_layout_checker-windows-amd64.exe`
- `dist/sbgn_layout_checker-windows-arm64.exe`
