#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.retrieval import ExperienceStore

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--experience", required=True)
    parser.add_argument("--documents", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="niakvio-local")
    args = parser.parse_args()

    cases = [
        json.loads(line)
        for line in Path(args.cases).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    planner = BrainPlanner(
        LocalOpenAICompatibleBackend(
            base_url=args.endpoint,
            model=args.model,
            timeout_seconds=240,
            temperature=0.0,
        ),
        ExperienceStore.from_jsonl(args.experience),
        DocumentStore.from_jsonl(args.documents),
    )

    layer_ok = 0
    strategy_ok = 0
    contract_ok = 0
    rows = []

    for case in cases:
        request = RepairRequest(**case["request"])
        try:
            proposal = planner.plan(request)
            contract_ok += 1
            expected_layer = case["expected_target_layer"]
            expected_strategies = set(case.get("expected_strategies") or [])
            layer_match = proposal.target_layer == expected_layer
            strategy_match = proposal.strategy in expected_strategies
            layer_ok += int(layer_match)
            strategy_ok += int(strategy_match)
            rows.append({
                "id": case["id"],
                "contract_ok": True,
                "layer_ok": layer_match,
                "strategy_ok": strategy_match,
                "expected_layer": expected_layer,
                "actual_layer": proposal.target_layer,
                "expected_strategies": sorted(expected_strategies),
                "actual_strategy": proposal.strategy,
                "confidence": proposal.confidence,
                "abstain": proposal.abstain,
            })
        except Exception as exc:
            rows.append({
                "id": case["id"],
                "contract_ok": False,
                "error": type(exc).__name__ + ": " + str(exc),
            })

    total = len(cases)
    result = {
        "model": args.model,
        "cases": total,
        "contract_valid_rate": contract_ok / total if total else 0.0,
        "causal_layer_accuracy": layer_ok / total if total else 0.0,
        "exact_strategy_accuracy": strategy_ok / total if total else 0.0,
        "results": rows,
    }
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
