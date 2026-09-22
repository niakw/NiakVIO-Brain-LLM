#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from niakvio_brain_llm.learning_policy import classify_learning_record

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            rows.append(value)
    return rows

def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    buckets: dict[str, list[dict[str, Any]]] = {
        "positive": [],
        "negative": [],
        "safety": [],
        "transient": [],
        "sft_candidates": [],
    }

    for row in rows:
        policy = classify_learning_record(row)
        enriched = dict(row)
        enriched["_learning"] = policy
        bucket = str(policy["rag_bucket"])
        buckets[bucket].append(enriched)
        if policy["sft_candidate"]:
            buckets["sft_candidates"].append(enriched)

    out = Path(args.output_dir)
    for name, values in buckets.items():
        write_jsonl(out / f"{name}.jsonl", values)

    print(json.dumps({
        "input": len(rows),
        "positive": len(buckets["positive"]),
        "negative": len(buckets["negative"]),
        "safety": len(buckets["safety"]),
        "transient": len(buckets["transient"]),
        "sft_candidates": len(buckets["sft_candidates"]),
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
