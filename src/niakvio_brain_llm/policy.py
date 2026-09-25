from __future__ import annotations

import re
from typing import Any

from .contracts import RepairRequest

URL = re.compile(r"https?://[^\s\"'<>]+", re.I)
FRESH_KEYS = {
    "candidate_api_url",
    "current_api_url",
    "discovered_url",
    "bundle_api_url",
    "validated_candidate_url",
    "current_endpoint",
}
FRESH_SOURCES = {
    "current_api_discovery",
    "current_bundle_probe",
    "current_network_probe",
    "live_discovery",
}

NO_MUTATION_STRATEGIES = {
    "same_provider_candidate_program_replay",
    "compare_browser_native_residential_profiles_without_provider_mutation",
    "normalize_client_media_type_before_provider_capability_gate",
}
FRESH_DISCOVERY_STRATEGIES = {
    "discover_api_from_current_page_and_bundles",
}

def _has_fresh_url(value: Any) -> bool:
    if isinstance(value, dict):
        source = str(value.get("source") or "").strip().casefold()
        if source in FRESH_SOURCES:
            if URL.search(str(value)):
                return True
        for key, item in value.items():
            if str(key).strip().casefold() in FRESH_KEYS and URL.search(str(item)):
                return True
            if _has_fresh_url(item):
                return True
    elif isinstance(value, list):
        return any(_has_fresh_url(item) for item in value)
    return False

def build_mutation_policy(
    request: RepairRequest,
    causal_prior: dict[str, Any],
) -> dict[str, Any]:
    layer = str(causal_prior.get("target_layer") or "unknown")
    strategy = str(causal_prior.get("strategy_prior") or "")

    if layer != "provider":
        return {
            "allow_mutations": False,
            "allowed_scopes": [],
            "force_abstain": True,
            "reason": f"causal layer is {layer}",
        }

    if strategy in NO_MUTATION_STRATEGIES:
        return {
            "allow_mutations": False,
            "allowed_scopes": [],
            "force_abstain": False,
            "reason": "strategy is verification/replay only",
        }

    if request.advisor_only:
        return {
            "allow_mutations": False,
            "allowed_scopes": [],
            "force_abstain": False,
            "reason": "advisor-only planning; deterministic Brain owns candidate mutation and proof",
        }

    context = request.provider_context or {}
    allowed = set(request.allowed_mutations)

    if not context.get("authored_module"):
        allowed.discard("provider_js")
    if not context.get("registered_patch_scripts"):
        allowed.discard("provider_patch")
    if not (context.get("override") or context.get("hub")):
        allowed.discard("provider_data")

    fresh = _has_fresh_url(request.observations) or _has_fresh_url(context)
    if strategy in FRESH_DISCOVERY_STRATEGIES and not fresh:
        return {
            "allow_mutations": False,
            "allowed_scopes": [],
            "force_abstain": True,
            "reason": "fresh current discovery evidence is required before patching",
        }

    if not allowed:
        return {
            "allow_mutations": False,
            "allowed_scopes": [],
            "force_abstain": True,
            "reason": "no provider-local patch context is available",
        }

    return {
        "allow_mutations": True,
        "allowed_scopes": sorted(allowed),
        "force_abstain": False,
        "reason": "provider-local patch context available",
    }
