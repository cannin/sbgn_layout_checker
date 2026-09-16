#!/usr/bin/env bash
set -euo pipefail

./scripts/check-versions.py
(cd go && go test ./...)
(cd python && uv run pytest)
(cd python && uv run ruff check . && uv run ruff format --check .)
uv run --project python ruff check scripts/generate_chapter4_fixtures.py
uv run --project python ruff format --check scripts/generate_chapter4_fixtures.py
uv run --project python ruff check scripts/check-versions.py scripts/render_rule_examples.py
uv run --project python ruff format --check scripts/check-versions.py scripts/render_rule_examples.py
./scripts/validate-fixtures.sh
