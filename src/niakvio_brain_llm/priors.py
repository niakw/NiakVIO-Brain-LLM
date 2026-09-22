from __future__ import annotations

from typing import Any

from .contracts import RepairRequest

STATIC_FAILURE_PRIORS: dict[str, tuple[str, float]] = {
    "media-type-pre-network-gate": ("core", 0.99),
    "transport-environment-gap": ("harness", 0.99),
    "client-capability-projection-gap": ("core", 0.96),
    "materializer-non-idempotence": ("core", 0.96),
    "client-lifecycle-gap": ("core", 0.96),
    "route-proven-gap": ("provider", 0.96),
    "chain-terminal-gap": ("provider", 0.96),
    "candidate-replay-gap": ("provider", 0.96),
    "media-extraction-gap": ("provider", 0.96),
    "api-discovery-gap": ("provider", 0.96),
}

def _canon(value: object) -> str:
    return "-".join(str(value or "").strip().casefold().replace("_", "-").split())

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
    static = STATIC_FAILURE_PRIORS.get(failure)
    if static:
        layer, confidence = static
        return {
            "target_layer": layer,
            "confidence": confidence,
            "source": "failure_class_taxonomy",
        }

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
