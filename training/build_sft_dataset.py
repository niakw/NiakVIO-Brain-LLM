#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SYSTEM = (
    "You are NiakVIO Brain LLM. Diagnose provider failures and propose the smallest "
    "bounded repair. NiakVIO verification is the only proof authority."
)

VALID_LAYERS = {"provider", "core", "harness", "network", "unknown"}

def build_example(row: dict[str, Any]) -> dict[str, Any] | None:
    if row.get("result") not in {"validated", "abstained"}:
        return None

    target_layer = str(row.get("target_layer") or "").casefold()
    if target_layer not in VALID_LAYERS:
        # Historical RAG memory is useful without being safe supervised truth.
        return None

    request = {
        "provider_id": row.get("provider_id"),
        "failure_class": row.get("failure_class"),
        "status": row.get("status_before"),
        "supported_types": row.get("supported_types") or [],
    }
    answer = {
        "provider_id": row.get("provider_id"),
        "diagnosis": row.get("diagnosis", ""),
        "strategy": row.get("strategy", ""),
        "confidence": 1.0 if row.get("result") == "validated" else 0.6,
        "target_layer": target_layer,
        "evidence": row.get("evidence", []),
        "mutations": row.get("mutations", []),
        "tests": row.get("requested_tests") or row.get("tests") or [],
        "abstain": row.get("result") == "abstained",
        "abstain_reason": row.get("lesson", "") if row.get("result") == "abstained" else "",
    }
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(request, ensure_ascii=True)},
            {"role": "assistant", "content": json.dumps(answer, ensure_ascii=True)},
        ]
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    examples = []
    for line in Path(args.input).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            example = build_example(row)
            if example:
                examples.append(example)

    Path(args.output).write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in examples) + ("\n" if examples else ""),
        encoding="utf-8",
    )
    print(f"examples={len(examples)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
