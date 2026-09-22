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
    "verification_plan_ok",
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
    "verification_plan_ok": 0.05,
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
        rows.append({
            "model": report.get("model") or path.stem,
            "quality_score": round(score(report), 4),
            "rates": report.get("rates") or {},
            "path": str(path),
        })

    rows.sort(key=lambda row: row["quality_score"], reverse=True)
    print(json.dumps({
        "weights": WEIGHTS,
        "ranking": rows,
    }, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
