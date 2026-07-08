"""trim_red_team_json.py

Repair a red_team.json corrupted by a trailing duplicate JSON tail from
`claude -p` retries/reasoning traces. Overwrites the file with the first
complete JSON object only.

Usage:
    python scripts/trim_red_team_json.py <path/to/red_team.json>
"""

from __future__ import annotations

import json
import sys


def trim(path: str) -> None:
    text = open(path, "r", encoding="utf-8").read()
    start = text.index("{")
    depth = 0
    end = start
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    clean = text[start : end + 1]
    data = json.loads(clean)  # validates completeness
    open(path, "w", encoding="utf-8").write(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"trimmed {len(text)} -> {len(clean)} bytes")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python trim_red_team_json.py <path>", file=sys.stderr)
        raise SystemExit(1)
    trim(sys.argv[1])
