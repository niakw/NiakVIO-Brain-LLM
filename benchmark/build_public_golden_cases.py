#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from niakvio_brain_llm.priors import taxonomy_layer

def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        case for case in data.get("cases") or []
        if isinstance(case, dict)
    ]

def build_case(case: dict[str, Any]) -> dict[str, Any] | None:
    failure = str(case.get("failureClass") or "")
    layer = taxonomy_layer(failure)
    strategy = str(case.get("solutionClass") or "")
    if not layer or not strategy:
        return None

    providers = [str(x) for x in case.get("providers") or []]
    provider_id = next((p for p in providers if p != "global"), "global-diagnostic")

    observations = []
    for signal in case.get("transferableSignals") or []:
        observations.append({"signal": str(signal)})

    status = {
        "route_proven_gap": "ROUTE PROVEN",
        "chain_terminal_gap": "CHAIN REACHED",
        "candidate_replay_gap": "CANDIDATE OK",
        "transport_environment_gap": "HARNESS/ENV BLOCKED",
    }.get(failure, "historical-benchmark")

    return {
        "id": str(case.get("id") or failure),
        "request": {
            "provider_id": provider_id,
            "failure_class": failure,
            "status": status,
            "supported_types": [],
            "observations": observations[:8],
            "provider_context": {
                "read_only": True,
                "benchmark": True,
            },
        },
        "expected_target_layer": layer,
        "expected_strategies": [strategy],
        "source": "NiakVIO historical repair seed",
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = []
    for case in load_cases(Path(args.seed)):
        built = build_case(case)
        if built:
            rows.append(built)

    Path(args.output).write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )
    print(json.dumps({
        "cases": len(rows),
        "layers": {
            layer: sum(1 for row in rows if row["expected_target_layer"] == layer)
            for layer in sorted({row["expected_target_layer"] for row in rows})
        },
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
