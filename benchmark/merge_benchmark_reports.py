#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

METRICS = (
    "schema_valid",
    "provider_id_ok",
    "layer_ok",
    "strategy_ok",
    "mutation_policy_ok",
    "mutation_valid",
    "abstain_policy_ok",
    "brain_verification_plan_ok",
    "model_tests_present",
    "fully_compliant",
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    all_results = []
    models = set()
    for raw in args.reports:
        report = json.loads(Path(raw).read_text(encoding="utf-8"))
        models.add(str(report.get("model") or ""))
        all_results.extend(report.get("results") or [])

    total = len(all_results)
    counts = {
        metric: sum(1 for row in all_results if row.get(metric) is True)
        for metric in METRICS
    }
    merged = {
        "model": sorted(models)[0] if len(models) == 1 else sorted(models),
        "cases": total,
        "mode": "merged_sharded_raw_model_reasoning_plus_deterministic_brain_policy",
        "rates": {
            metric: (counts[metric] / total if total else 0.0)
            for metric in METRICS
        },
        "notes": {
            "model_tests_present": "diagnostic only; deterministic Brain owns verification planning",
        },
        "results": all_results,
    }
    Path(args.output).write_text(
        json.dumps(merged, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"cases": total, "rates": merged["rates"]}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
