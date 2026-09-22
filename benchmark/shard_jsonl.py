#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    args = parser.parse_args()

    if args.shard_count < 1:
        raise SystemExit("shard-count must be >= 1")
    if not 0 <= args.shard_index < args.shard_count:
        raise SystemExit("shard-index out of range")

    rows = [
        line for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [
        line for index, line in enumerate(rows)
        if index % args.shard_count == args.shard_index
    ]
    Path(args.output).write_text(
        "\n".join(selected) + ("\n" if selected else ""),
        encoding="utf-8",
    )
    print(f"shard={args.shard_index}/{args.shard_count} cases={len(selected)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
