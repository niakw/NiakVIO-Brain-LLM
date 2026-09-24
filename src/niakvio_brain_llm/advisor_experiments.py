from __future__ import annotations

import hashlib
import json
from typing import Any

from .contracts import RepairRequest

ROLES = ("search", "detail", "episode", "player", "source", "api", "other")
ROUTE_POLICIES = ("owned_only", "owned_plus_peer", "owned_plus_peer_generic")
RECIPE_POLICIES = ("current_only", "current_plus_provider", "current_plus_provider_peer")

DEFAULTS: dict[str, dict[str, Any]] = {
    "provider-owned-origin-header-and-domain-replay": {
        "route_policy": "owned_plus_peer",
        "recipe_policy": "current_plus_provider",
        "role_order": ["api", "detail", "search", "player", "source", "episode", "other"],
        "terminal_only": False, "alias_search": False, "response_salvage": False,
        "document_request_mining": False, "session_bootstrap": True,
        "max_depth": 3, "max_pages": 14, "max_embeds": 12, "max_recipe_passes": 3,
    },
    "search-detail-player-terminal-traversal": {
        "route_policy": "owned_plus_peer",
        "recipe_policy": "current_plus_provider_peer",
        "role_order": ["search", "detail", "episode", "player", "source", "api", "other"],
        "terminal_only": False, "alias_search": False, "response_salvage": False,
        "document_request_mining": False, "session_bootstrap": False,
        "max_depth": 5, "max_pages": 24, "max_embeds": 24, "max_recipe_passes": 4,
    },
    "terminal-media-extractor-with-playback-validation": {
        "route_policy": "owned_plus_peer",
        "recipe_policy": "current_plus_provider_peer",
        "role_order": ["player", "source", "api", "episode", "detail", "other"],
        "terminal_only": True, "alias_search": False, "response_salvage": True,
        "document_request_mining": False, "session_bootstrap": False,
        "max_depth": 5, "max_pages": 20, "max_embeds": 28, "max_recipe_passes": 4,
    },
    "same-provider-candidate-program-replay": {
        "route_policy": "owned_only",
        "recipe_policy": "current_plus_provider",
        "role_order": ["player", "api", "source", "detail", "episode", "other"],
        "terminal_only": False, "alias_search": False, "response_salvage": False,
        "document_request_mining": False, "session_bootstrap": False,
        "max_depth": 4, "max_pages": 18, "max_embeds": 24, "max_recipe_passes": 4,
    },
    "proven-request-program-and-terminal-extraction": {
        "route_policy": "owned_only",
        "recipe_policy": "current_plus_provider",
        "role_order": ["api", "source", "player", "episode", "detail", "other"],
        "terminal_only": True, "alias_search": False, "response_salvage": True,
        "document_request_mining": False, "session_bootstrap": False,
        "max_depth": 5, "max_pages": 18, "max_embeds": 28, "max_recipe_passes": 5,
    },
    "discover-api-from-current-page-and-bundles": {
        "route_policy": "owned_plus_peer_generic",
        "recipe_policy": "current_plus_provider_peer",
        "role_order": ["search", "api", "detail", "player", "source", "episode", "other"],
        "terminal_only": False, "alias_search": False, "response_salvage": False,
        "document_request_mining": True, "session_bootstrap": False,
        "max_depth": 4, "max_pages": 28, "max_embeds": 20, "max_recipe_passes": 4,
    },
}


def canon(value: object) -> str:
    return "-".join(str(value or "").strip().casefold().replace("_", "-").split())


def _camel(experiment: dict[str, Any]) -> dict[str, Any]:
    return {
        "routePolicy": experiment["route_policy"],
        "recipePolicy": experiment["recipe_policy"],
        "roleOrder": list(experiment["role_order"]),
        "terminalOnly": bool(experiment["terminal_only"]),
        "aliasSearch": bool(experiment["alias_search"]),
        "responseSalvage": bool(experiment["response_salvage"]),
        "documentRequestMining": bool(experiment["document_request_mining"]),
        "sessionBootstrap": bool(experiment["session_bootstrap"]),
        "maxDepth": int(experiment["max_depth"]),
        "maxPages": int(experiment["max_pages"]),
        "maxEmbeds": int(experiment["max_embeds"]),
        "maxRecipePasses": int(experiment["max_recipe_passes"]),
    }


def experiment_fingerprint(experiment: dict[str, Any]) -> str:
    payload = json.dumps(
        _camel(experiment), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _failed_fingerprints(request: RepairRequest) -> set[str]:
    history = (request.provider_context or {}).get("advisor_experiment_history")
    if not isinstance(history, list):
        return set()
    out: set[str] = set()
    for row in history:
        if not isinstance(row, dict):
            continue
        fp = str(row.get("llmAdvisorExperimentFingerprint") or "").strip().casefold()
        if len(fp) != 64 or any(not (ch.isdigit() or ch in "abcdef") for ch in fp):
            continue
        if int(row.get("consecutiveFailures") or 0) <= 0:
            continue
        if str(row.get("lastOutcome") or "").strip().casefold() in {"accepted", "verified", "success"}:
            continue
        out.add(fp)
    return out


def _issue_text(request: RepairRequest) -> str:
    parts = [
        str(request.failure_class or ""),
        str(request.status or ""),
        str((request.census_prior or {}).get("dominantIssue") or ""),
    ]
    history = (request.provider_context or {}).get("advisor_experiment_history")
    if isinstance(history, list):
        for row in history[-12:]:
            if isinstance(row, dict):
                parts.extend([
                    str(row.get("lastReason") or ""),
                    str(row.get("lastOutcome") or ""),
                    str(row.get("failureClass") or ""),
                ])
    return " ".join(parts).casefold()


def _targeted_variants(base: dict[str, Any], issue: str) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []

    def add(**changes: Any) -> None:
        row = {**base, **changes}
        row["role_order"] = list(changes.get("role_order", base["role_order"]))
        variants.append(row)

    # First response to transport/WAF failures: keep provider causality fixed,
    # but replay a browser-like session and salvage successful terminal responses.
    if any(token in issue for token in ("waf", "403", "429", "transport", "http_error", "network_exception")):
        add(
            route_policy="owned_plus_peer_generic",
            recipe_policy="current_plus_provider_peer",
            session_bootstrap=True,
            response_salvage=True,
            max_depth=min(6, int(base["max_depth"]) + 1),
            max_pages=min(36, int(base["max_pages"]) + 6),
        )
    # Zero-result/search failures need identity aliases and current document
    # request mining before merely widening the crawl budget.
    if any(token in issue for token in ("zero_result", "search", "lookup", "no proof")):
        add(
            route_policy="owned_plus_peer_generic",
            recipe_policy="current_plus_provider_peer",
            alias_search=True,
            document_request_mining=True,
            max_pages=min(36, int(base["max_pages"]) + 8),
        )
    # Terminal/playback failures prioritize terminal roles and response salvage.
    if any(token in issue for token in ("playable", "terminal", "media", "player", "profile_unavailable")):
        terminal_roles = [r for r in ("player", "source", "api", "episode", "detail", "search", "other") if r in ROLES]
        add(
            recipe_policy="current_plus_provider_peer",
            role_order=terminal_roles,
            terminal_only=True,
            response_salvage=True,
            document_request_mining=True,
            max_embeds=min(36, int(base["max_embeds"]) + 6),
            max_recipe_passes=min(6, int(base["max_recipe_passes"]) + 1),
        )
    return variants


def _generic_variants(base: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ordinal in range(1, 25):
        row = dict(base)
        row["role_order"] = list(base["role_order"])
        row["route_policy"] = ROUTE_POLICIES[ordinal % len(ROUTE_POLICIES)]
        row["recipe_policy"] = RECIPE_POLICIES[(ordinal // 2) % len(RECIPE_POLICIES)]
        row["alias_search"] = bool(ordinal & 1)
        row["response_salvage"] = bool(ordinal & 2)
        row["document_request_mining"] = bool(ordinal & 4)
        row["session_bootstrap"] = bool(ordinal & 8)
        row["terminal_only"] = bool(base["terminal_only"] or (ordinal & 16))
        row["max_depth"] = 2 + (ordinal % 5)
        row["max_pages"] = min(36, 12 + ((ordinal * 5) % 25))
        row["max_embeds"] = min(36, 12 + ((ordinal * 7) % 25))
        row["max_recipe_passes"] = 1 + (ordinal % 6)
        shift = ordinal % len(row["role_order"]) if row["role_order"] else 0
        if shift:
            row["role_order"] = row["role_order"][shift:] + row["role_order"][:shift]
        rows.append(row)
    return rows


def next_advisor_experiment(request: RepairRequest, strategy: str) -> dict[str, Any]:
    """Return the first bounded experiment not already rejected for this provider."""
    key = canon(strategy)
    base = DEFAULTS.get(key)
    if not base:
        return {}
    base = {**base, "role_order": list(base["role_order"])}
    blocked = _failed_fingerprints(request)
    issue = _issue_text(request)
    candidates = [base, *_targeted_variants(base, issue), *_generic_variants(base)]
    seen: set[str] = set()
    for row in candidates:
        fp = experiment_fingerprint(row)
        if fp in seen:
            continue
        seen.add(fp)
        if fp not in blocked:
            return row
    return {}
