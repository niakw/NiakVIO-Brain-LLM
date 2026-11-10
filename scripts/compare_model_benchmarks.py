#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

QUALITY_KEYS = (
    "schema_valid",
    "provider_id_ok",
    "layer_ok",
    "strategy_ok",
    "mutation_policy_ok",
    "mutation_valid",
    "abstain_policy_ok",
    "brain_verification_plan_ok",
    "fully_compliant",
)

WEIGHTS = {
    "schema_valid": 0.05,
    "provider_id_ok": 0.05,
    "layer_ok": 0.20,
    "strategy_ok": 0.20,
    "mutation_policy_ok": 0.15,
    "mutation_valid": 0.10,
    "abstain_policy_ok": 0.10,
    "brain_verification_plan_ok": 0.05,
    "fully_compliant": 0.10,
}

def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def score(report: dict[str, Any]) -> float:
    rates = report.get("rates") or {}
    return sum(
        float(rates.get(key) or 0.0) * WEIGHTS[key]
        for key in QUALITY_KEYS
    )

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+")
    args = parser.parse_args()

    rows = []
    for raw in args.reports:
        path = Path(raw)
        report = load(path)
        observed = report.get("results")
        if isinstance(observed, list):
            valid_count = sum(row.get("schema_valid") is True
                              for row in observed if isinstance(row, dict))
        else:
            valid_count = int(report.get("validCaseCount") or 0)
            if valid_count == 0 and float((report.get("rates") or {}).get("schema_valid") or 0) > 0:
                valid_count = 1
        usable = valid_count > 0
        rows.append({
            "model": report.get("model") or path.stem,
            "quality_score": round(score(report), 4) if usable else None,
            "status": "quality_measured" if usable else "inference_unavailable",
            "valid_case_count": valid_count,
            "timeout_cases": sum(str(row.get("error") or "").startswith("TimeoutError:")
                                 for row in (observed or []) if isinstance(row, dict)),
            "rates": report.get("rates") or {},
            "model_tests_present": (report.get("rates") or {}).get("model_tests_present"),
            "path": str(path),
        })

    rows.sort(key=lambda row: (row["quality_score"] is not None,
                               row["quality_score"] or 0), reverse=True)
    print(json.dumps({
        "weights": WEIGHTS,
        "ranking": rows,
        "note": "Models with zero schema-valid completions are inference_unavailable, NOT quality_score 0; deterministic Brain owns verification planning",
    }, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
