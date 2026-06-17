#!/usr/bin/env python3
"""Validate DSLV-ZPDI Conventional Commit messages."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HEADER_RE = re.compile(
    r"^(feat|fix|docs|test|refactor|perf|build|ci|chore|revert|security)"
    r"(\([a-z0-9._/-]+\))?!?: .+"
)


def _read_message(argv: list[str]) -> str:
    if len(argv) > 1:
        return Path(argv[1]).read_text(encoding="utf-8").strip()

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and Path(event_path).is_file():
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        pull_request = event.get("pull_request")
        if isinstance(pull_request, dict) and pull_request.get("title"):
            return str(pull_request["title"]).strip()

    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%B"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _first_non_comment_line(message: str) -> str:
    for line in message.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def main() -> int:
    message = _read_message(sys.argv)
    header = _first_non_comment_line(message)
    if not header:
        print("Conventional Commit validation failed: empty commit message", file=sys.stderr)
        return 1

    if header.startswith("Merge "):
        return 0

    if HEADER_RE.fullmatch(header):
        return 0

    print(
        "Conventional Commit validation failed.\n"
        "Expected: type(optional-scope)!: summary\n"
        "Allowed types: feat, fix, docs, test, refactor, perf, build, ci, chore, "
        "revert, security\n"
        f"Actual: {header}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
