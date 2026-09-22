from __future__ import annotations

from typing import Any

from .contracts import RepairRequest

def _canon(value: object) -> str:
    return str(value or "").strip().casefold().replace("_", "-")

def build_causal_prior(
    request: RepairRequest,
    experiences: list[dict[str, Any]],
) -> dict[str, Any]:
    status = _canon(request.status)

    if "harness-mismatch" in status:
        return {"target_layer": "harness", "confidence": 0.99, "source": "current_status"}
    if "harness/env-blocked" in status or "harness-env-blocked" in status:
        return {"target_layer": "harness", "confidence": 0.95, "source": "current_status"}
    if "provider-network-blocked" in status:
        return {"target_layer": "network", "confidence": 0.99, "source": "current_status"}
    if status == "disabled" or "disabled" in status:
        return {"target_layer": "unknown", "confidence": 0.99, "source": "lifecycle_disabled"}

    failure = _canon(request.failure_class)
    exact = [
        row for row in experiences
        if _canon(row.get("failure_class") or row.get("failureClass")) == failure
    ]
    if exact:
        row = exact[0]
        providers = {_canon(x) for x in row.get("providers") or []}
        if providers and "global" not in providers:
            return {
                "target_layer": "provider",
                "confidence": 0.94,
                "source": "exact_historical_provider_case",
                "experience_id": row.get("experience_id"),
                "strategy_prior": row.get("strategy"),
                "lesson": row.get("lesson"),
            }

    provider_statuses = (
        "route-proven",
        "chain-reached",
        "candidate-ok",
        "partial-ok",
        "regression-provider-js",
        "provider-js-broken",
    )
    if any(token in status for token in provider_statuses):
        return {
            "target_layer": "provider",
            "confidence": 0.82,
            "source": "current_census_repair_state",
        }

    return {
        "target_layer": "unknown",
        "confidence": 0.35,
        "source": "insufficient_causal_prior",
    }
