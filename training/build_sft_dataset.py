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

VALID_LAYERS = {"provider", "core", "harness", "network"}

def build_example(row: dict[str, Any]) -> dict[str, Any] | None:
    learning = row.get("_learning")
    if not isinstance(learning, dict) or learning.get("sft_candidate") is not True:
        return None
    if row.get("result") != "validated":
        return None
    if str(row.get("verification_authority") or "").strip().casefold() != "niakvio":
        return None

    target_layer = str(row.get("target_layer") or "").casefold()
    if target_layer not in VALID_LAYERS:
        return None

    provider_id = str(row.get("provider_id") or "").strip()
    failure_class = str(row.get("failure_class") or "").strip()
    strategy = str(row.get("strategy") or "").strip()
    if not provider_id or not failure_class or not strategy:
        return None

    request = {
        "provider_id": provider_id,
        "failure_class": failure_class,
        "status": row.get("status_before"),
        "supported_types": row.get("supported_types") or [],
    }
    answer = {
        "provider_id": provider_id,
        "diagnosis": row.get("diagnosis", ""),
        "strategy": strategy,
        "confidence": 1.0,
        "target_layer": target_layer,
        "evidence": row.get("evidence", []),
        "mutations": row.get("mutations", []),
        "tests": row.get("requested_tests") or row.get("tests") or [],
        "abstain": False,
        "abstain_reason": "",
    }
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(request, ensure_ascii=True)},
            {"role": "assistant", "content": json.dumps(answer, ensure_ascii=True)},
        ],
        "metadata": {
            "source": "niakvio-verified-learning",
            "weight": float(learning.get("weight") or 1.0),
        },
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
        "\n".join(json.dumps(row, ensure_ascii=True) for row in examples)
        + ("\n" if examples else ""),
        encoding="utf-8",
    )
    print(json.dumps({
        "examples": len(examples),
        "validated_only": True,
        "verification_authority": "niakvio",
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
