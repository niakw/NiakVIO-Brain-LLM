from __future__ import annotations

from typing import Any

from .contracts import RepairRequest

# Stable NiakVIO failure classes carry a causal + strategy prior. This is not
# provider-specific repair logic: it is the project-wide taxonomy learned from
# validated historical cases.
STATIC_FAILURE_PRIORS: dict[str, dict[str, Any]] = {
    "media-type-pre-network-gate": {
        "target_layer": "core",
        "confidence": 0.99,
        "strategy_prior": "normalize_client_media_type_before_provider_capability_gate",
    },
    "transport-environment-gap": {
        "target_layer": "harness",
        "confidence": 0.99,
        "strategy_prior": "compare_browser_native_residential_profiles_without_provider_mutation",
    },
    "client-capability-projection-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "materializer-non-idempotence": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "client-lifecycle-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "route-proven-gap": {
        "target_layer": "provider",
        "confidence": 0.96,
        "strategy_prior": "search_detail_player_terminal_traversal",
    },
    "chain-terminal-gap": {
        "target_layer": "provider",
        "confidence": 0.96,
        "strategy_prior": "terminal_media_extractor_with_playback_validation",
    },
    "candidate-replay-gap": {
        "target_layer": "provider",
        "confidence": 0.96,
        "strategy_prior": "same_provider_candidate_program_replay",
    },
    "media-extraction-gap": {
        "target_layer": "provider",
        "confidence": 0.96,
        "strategy_prior": "terminal_media_extractor_with_playback_validation",
    },
    "api-discovery-gap": {
        "target_layer": "provider",
        "confidence": 0.96,
        "strategy_prior": "discover_api_from_current_page_and_bundles",
    },
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
        prior = dict(static)
        prior["source"] = "failure_class_taxonomy"
        exact = next((
            row for row in experiences
            if _canon(row.get("failure_class") or row.get("failureClass")) == failure
        ), None)
        if exact:
            prior["experience_id"] = exact.get("experience_id")
            prior["lesson"] = exact.get("lesson")
            if not prior.get("strategy_prior") and exact.get("strategy"):
                prior["strategy_prior"] = exact.get("strategy")
        return prior

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
