from __future__ import annotations

from typing import Any

from .contracts import RepairRequest

# Project-wide causal taxonomy learned from validated NiakVIO architecture/history.
# These are failure classes, never provider-specific exceptions.
STATIC_FAILURE_PRIORS: dict[str, dict[str, Any]] = {
    "media-type-pre-network-gate": {
        "target_layer": "core",
        "confidence": 0.99,
        "strategy_prior": "normalize_client_media_type_before_provider_capability_gate",
    },
    "provider-backend-isolation": {
        "target_layer": "provider",
        "confidence": 0.96,
    },
    "api-discovery-gap": {
        "target_layer": "provider",
        "confidence": 0.96,
        "strategy_prior": "discover_api_from_current_page_and_bundles",
    },
    "playback-identity-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "runtime-compatibility-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "client-capability-projection-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "materializer-non-idempotence": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "provider-identity-collision": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "transport-environment-gap": {
        "target_layer": "harness",
        "confidence": 0.99,
        "strategy_prior": "compare_browser_native_residential_profiles_without_provider_mutation",
    },
    "typed-api-execution": {
        "target_layer": "provider",
        "confidence": 0.96,
    },
    "provider-reconstruction-integrity": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "identity-mismatch": {
        "target_layer": "provider",
        "confidence": 0.96,
    },
    "media-validation-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "runtime-timeout-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "structured-parse-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "state-authority-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "activation-proof-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "client-lifecycle-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "proof-freshness-gap": {
        "target_layer": "core",
        "confidence": 0.96,
    },
    "provider-transport-gap": {
        "target_layer": "provider",
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
        "strategy_prior": "proven_request_program_and_terminal_extraction",
    },
}

def _canon(value: object) -> str:
    return "-".join(str(value or "").strip().casefold().replace("_", "-").split())

def taxonomy_prior(failure_class: object) -> dict[str, Any] | None:
    prior = STATIC_FAILURE_PRIORS.get(_canon(failure_class))
    return dict(prior) if prior else None

def taxonomy_layer(failure_class: object) -> str | None:
    prior = taxonomy_prior(failure_class)
    return str(prior["target_layer"]) if prior else None

def build_causal_prior(
    request: RepairRequest,
    experiences: list[dict[str, Any]],
) -> dict[str, Any]:
    status = _canon(request.status)
    failure = _canon(request.failure_class)
    static = taxonomy_prior(failure)
    transport_class = _canon((request.census_prior or {}).get("harnessTransportClass"))

    def status_prior(layer: str, confidence: float, source: str = "current_status") -> dict[str, Any]:
        prior: dict[str, Any] = {
            "target_layer": layer,
            "confidence": confidence,
            "source": source,
        }
        # Current status owns the causal layer. A taxonomy strategy may survive
        # only when it belongs to the same layer; never carry a provider repair
        # strategy into a harness/network override.
        if static and static.get("target_layer") == layer:
            if static.get("strategy_prior"):
                prior["strategy_prior"] = static["strategy_prior"]
        return prior

    if "client-transport-gap" in status:
        prior = status_prior("harness", 0.99)
        if transport_class == "browser-profile-only-both-networks":
            prior["strategy_prior"] = "native_tls_browser_differential_v1"
        elif transport_class == "browser-profile-only":
            prior["strategy_prior"] = "browser_session_transport_bridge_v1"
        return prior
    if "harness-mismatch" in status:
        prior = status_prior("harness", 0.99)
        if transport_class == "browser-profile-only-both-networks":
            prior["strategy_prior"] = "native_tls_browser_differential_v1"
        return prior
    if "harness/env-blocked" in status or "harness-env-blocked" in status:
        return status_prior("harness", 0.95)
    if "provider-network-blocked" in status:
        return status_prior("network", 0.99)
    if status == "disabled" or "disabled" in status:
        return status_prior("unknown", 0.99, "lifecycle_disabled")

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
