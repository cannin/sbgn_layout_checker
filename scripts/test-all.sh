#!/usr/bin/env bash
set -euo pipefail

./scripts/check-versions.sh 0.1.1
(cd go && go test ./...)
(cd python && uv run --no-default-groups --extra test pytest)
(cd python && uv run --no-default-groups --extra test ruff check . && uv run --no-default-groups --extra test ruff format --check .)
uvx ruff check scripts/generate_chapter4_fixtures.py scripts/generate_rule_pngs.py
uvx ruff format --check scripts/generate_chapter4_fixtures.py scripts/generate_rule_pngs.py
./scripts/validate-fixtures.sh
make -C go current
(cd sbgn_libavoid/vendor/render_sbgn/go && GOWORK=off go build -trimpath -o dist/render_sbgn_go .)
./scripts/generate_rule_pngs.py
