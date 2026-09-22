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

def load_rows(path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

def request_for(row: dict) -> RepairRequest:
    providers = [p for p in row.get("providers") or [] if p != "global"]
    provider_id = providers[0] if providers else "global-diagnostic"
    return RepairRequest(
        provider_id=provider_id,
        failure_class=str(row.get("failure_class") or "unknown"),
        status="historical-benchmark",
        observations=[
            {"symptom_families": row.get("symptom_families") or []},
            {"signals": row.get("signals") or []},
        ],
        provider_context={
            "read_only": True,
            "benchmark": True,
        },
    )

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experience", required=True)
    parser.add_argument("--documents", default="")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="niakvio-local")
    parser.add_argument("--max-cases", type=int, default=8)
    args = parser.parse_args()

    rows = load_rows(args.experience)
    selected = rows[: max(1, args.max_cases)]
    documents = DocumentStore.from_jsonl(args.documents) if args.documents else DocumentStore([])
    backend = LocalOpenAICompatibleBackend(
        base_url=args.endpoint,
        model=args.model,
        timeout_seconds=240,
        temperature=0.0,
    )

    results = []
    schema_valid = 0
    exact_strategy = 0
    safe_global_layer = 0
    global_cases = 0

    for index, row in enumerate(selected):
        peers = rows[:index] + rows[index + 1:]
        planner = BrainPlanner(backend, ExperienceStore(peers), documents)
        request = request_for(row)
        try:
            proposal = planner.plan(request)
        except Exception as exc:
            results.append({
                "id": row.get("experience_id"),
                "error": type(exc).__name__ + ": " + str(exc),
            })
            continue

        schema_valid += 1
        expected = str(row.get("strategy") or "")
        exact_strategy += int(bool(expected) and proposal.strategy == expected)

        is_global = (row.get("providers") or []) == ["global"]
        if is_global:
            global_cases += 1
            safe_global_layer += int(proposal.target_layer != "provider")

        results.append({
            "id": row.get("experience_id"),
            "failure_class": row.get("failure_class"),
            "expected_strategy": expected,
            "actual_strategy": proposal.strategy,
            "target_layer": proposal.target_layer,
            "confidence": proposal.confidence,
            "abstain": proposal.abstain,
        })

    total = len(selected)
    summary = {
        "model": args.model,
        "cases": total,
        "schema_valid_rate": schema_valid / total if total else 0.0,
        "exact_strategy_rate": exact_strategy / total if total else 0.0,
        "safe_global_layer_rate": (
            safe_global_layer / global_cases if global_cases else None
        ),
        "results": results,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
