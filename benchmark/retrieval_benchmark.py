#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from niakvio_brain_llm.retrieval import ExperienceStore

def _partial(values: list[str]) -> list[str]:
    if not values:
        return []
    keep = max(1, (len(values) + 1) // 2)
    return values[:keep]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experience", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in Path(args.experience).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    store = ExperienceStore(rows)

    tested = 0
    top1 = 0
    topk = 0
    details = []

    for target in rows:
        expected_id = str(target.get("experience_id") or "")
        if not expected_id:
            continue

        # Simulate an incomplete new observation: no provider/id/strategy/lesson,
        # and only part of the known symptom/signal evidence.
        query = {
            "failure_class": target.get("failure_class"),
            "symptom_families": _partial(target.get("symptom_families") or []),
            "signals": _partial(target.get("signals") or []),
        }
        found = store.search(query, limit=args.top_k)
        ids = [str(row.get("experience_id") or "") for row in found]

        tested += 1
        top1 += int(bool(ids) and ids[0] == expected_id)
        topk += int(expected_id in ids)
        details.append({
            "id": expected_id,
            "retrieved": ids,
            "top_score": found[0].get("_retrieval_score") if found else None,
        })

    summary = {
        "tested": tested,
        "metric": "memory_recall_from_partial_problem_evidence",
        "top1_recall": (top1 / tested) if tested else 0.0,
        "top_k": args.top_k,
        "top_k_recall": (topk / tested) if tested else 0.0,
        "details": details,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
