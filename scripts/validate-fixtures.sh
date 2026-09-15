#!/usr/bin/env bash
set -euo pipefail

for fixture in testdata/chapter4/*.sbgn; do
    result=$(sbgn-validator -document "$fixture")
    if ! rg -q '"valid": true' <<<"$result"; then
        printf '%s\n' "$result" >&2
        printf 'invalid fixture: %s\n' "$fixture" >&2
        exit 1
    fi
done

printf 'validated %s chapter 4 fixtures\n' "$(find testdata/chapter4 -name '*.sbgn' | wc -l)"
