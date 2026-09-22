#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from niakvio_brain_llm.retrieval import ExperienceStore

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

    tested = 0
    top1 = 0
    topk = 0
    details = []

    for index, target in enumerate(rows):
        strategy = str(target.get("strategy") or "")
        if not strategy:
            continue

        peers = rows[:index] + rows[index + 1:]
        store = ExperienceStore(peers)

        # Hide provider/id/solution. The retriever must generalize from the problem shape.
        query = {
            "failure_class": target.get("failure_class"),
            "symptom_families": target.get("symptom_families") or [],
            "signals": target.get("signals") or [],
        }
        found = store.search(query, limit=args.top_k)
        strategies = [str(row.get("strategy") or "") for row in found]
        tested += 1
        top1 += int(bool(strategies) and strategies[0] == strategy)
        topk += int(strategy in strategies)
        details.append({
            "id": target.get("experience_id"),
            "expected": strategy,
            "retrieved": strategies,
        })

    summary = {
        "tested": tested,
        "top1": (top1 / tested) if tested else 0.0,
        "top_k": args.top_k,
        "top_k_accuracy": (topk / tested) if tested else 0.0,
        "details": details,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
