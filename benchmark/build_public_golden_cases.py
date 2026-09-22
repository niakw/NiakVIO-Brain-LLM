#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# High-confidence causal labels derived from NiakVIO's historical architecture.
# Ambiguous cases are intentionally excluded from this benchmark.
LAYER_BY_FAILURE = {
    "media_type_pre_network_gate": "core",
    "provider_backend_isolation": "provider",
    "api_discovery_gap": "provider",
    "playback_identity_gap": "core",
    "runtime_compatibility_gap": "core",
    "client_capability_projection_gap": "core",
    "materializer_non_idempotence": "core",
    "provider_identity_collision": "core",
    "transport_environment_gap": "harness",
    "typed_api_execution": "provider",
    "provider_reconstruction_integrity": "core",
    "identity_mismatch": "provider",
    "media_validation_gap": "core",
    "runtime_timeout_gap": "core",
    "structured_parse_gap": "core",
    "state_authority_gap": "core",
    "activation_proof_gap": "core",
    "client_lifecycle_gap": "core",
    "proof_freshness_gap": "core",
    "provider_transport_gap": "provider",
    "route_proven_gap": "provider",
    "chain_terminal_gap": "provider",
    "candidate_replay_gap": "provider",
    "media_extraction_gap": "provider",
}

def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        case for case in data.get("cases") or []
        if isinstance(case, dict)
    ]

def build_case(case: dict[str, Any]) -> dict[str, Any] | None:
    failure = str(case.get("failureClass") or "")
    layer = LAYER_BY_FAILURE.get(failure)
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
