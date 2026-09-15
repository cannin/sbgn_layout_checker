#!/usr/bin/env bash
set -euo pipefail

(cd go && go test ./...)
(cd python && uv run pytest)
(cd python && uv run ruff check . && uv run ruff format --check .)
uv run --project python ruff check scripts/generate_chapter4_fixtures.py
uv run --project python ruff format --check scripts/generate_chapter4_fixtures.py
./scripts/validate-fixtures.sh
