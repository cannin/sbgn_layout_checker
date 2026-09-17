#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
expected_version="${1:?usage: scripts/check-versions.sh VERSION}"

python_project_version="$(awk -F ' = ' '$1 == "version" { gsub(/"/, "", $2); print $2; exit }' "$repository_root/python/pyproject.toml")"
python_package_version="$(awk -F ' = ' '$1 == "__version__" { gsub(/"/, "", $2); print $2; exit }' "$repository_root/python/sbgn_layout_checker/__init__.py")"
go_version="$(awk -F '"' '/const version =/{ print $2; exit }' "$repository_root/go/cmd/sbgn_layout_checker/main.go")"

for version_entry in \
  "Python project:$python_project_version" \
  "Python package:$python_package_version" \
  "Go:$go_version"; do
    implementation="${version_entry%%:*}"
    actual_version="${version_entry#*:}"
    if [[ "$actual_version" != "$expected_version" ]]; then
        printf '%s version is %s; expected %s\n' \
          "$implementation" "$actual_version" "$expected_version" >&2
        exit 1
    fi
done

go_cli_version="$(cd "$repository_root" && go run ./go/cmd/sbgn_layout_checker --version)"
if [[ "$go_cli_version" != "$expected_version" ]]; then
    printf 'Go CLI version is %s; expected %s\n' "$go_cli_version" "$expected_version" >&2
    exit 1
fi

printf 'All Go and Python implementation versions are %s.\n' "$expected_version"
