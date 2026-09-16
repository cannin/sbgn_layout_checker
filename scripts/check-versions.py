#!/usr/bin/env python3
"""Verify release metadata and both CLIs expose one project version."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def run(*command: str) -> str:
    """Run a version command and return normalized output.

    Args:
        command: Executable and arguments to run.

    Returns:
        Standard output with surrounding whitespace removed.
    """

    return subprocess.run(
        command, cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def source_version(path: Path, pattern: str) -> str:
    """Extract a version from source code.

    Args:
        path: Source file to inspect.
        pattern: Regular expression with one version capture group.

    Returns:
        Captured version.
    """

    match = re.search(pattern, path.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"Could not find a version in {path.relative_to(ROOT)}")
    return match.group(1)


def main() -> None:
    """Check canonical, package, source, and CLI version parity."""

    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", VERSION) is None:
        raise SystemExit(f"VERSION is not semantic: {VERSION!r}")
    versions = {
        "Go source": source_version(
            ROOT / "go/cmd/sbgn_layout_checker/main.go",
            r'const version = "([^"]+)"',
        ),
        "Python source": source_version(
            ROOT / "python/sbgn_layout_checker/version.py",
            r'__version__ = "([^"]+)"',
        ),
        "Go CLI": run("go", "run", "./go/cmd/sbgn_layout_checker", "--version"),
        "Python CLI": run(
            "uv",
            "run",
            "--project",
            "python",
            "sbgn-layout-checker-py",
            "--version",
        ),
    }
    mismatches = {name: value for name, value in versions.items() if value != VERSION}
    if mismatches:
        raise SystemExit(f"Version mismatch: expected {VERSION}; got {mismatches}")
    print(f"All version declarations and CLIs expose {VERSION}.")


if __name__ == "__main__":
    main()
