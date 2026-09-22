#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.retrieval import ExperienceStore

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--experience", default="data/experience.example.jsonl")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="niakvio-local")
    args = parser.parse_args()

    cases = [
        json.loads(line)
        for line in Path(args.cases).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    planner = BrainPlanner(
        LocalOpenAICompatibleBackend(base_url=args.endpoint, model=args.model),
        ExperienceStore.from_jsonl(args.experience),
    )

    passed = 0
    results = []
    for case in cases:
        request = RepairRequest(**case["request"])
        proposal = planner.plan(request)
        expected = set(case.get("expected_strategies") or [])
        ok = proposal.strategy in expected if expected else True
        passed += int(ok)
        results.append({
            "id": case.get("id"),
            "ok": ok,
            "expected_strategies": sorted(expected),
            "actual_strategy": proposal.strategy,
            "confidence": proposal.confidence,
            "abstain": proposal.abstain,
        })

    summary = {
        "cases": len(cases),
        "passed": passed,
        "accuracy": (passed / len(cases)) if cases else 0.0,
        "results": results,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if passed == len(cases) else 1

if __name__ == "__main__":
    raise SystemExit(main())
