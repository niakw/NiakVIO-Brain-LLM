"""One current-SHA authority for injecting bounded real execution into Brain requests.

This code is shared by production FORCE and read-only source challenger. The
observation is a diagnostic, not proof of a repair or a host to copy.
"""
from __future__ import annotations

import re
from typing import Any

from .live_evidence import (
    apply_verified_live_failure, executed_runtime_source, fixture_evidence,
    network_evidence, observed_failure_class, public_domain_references,
    verification_feedback,
)


def attach_live_runtime_evidence(
    request: Any, live: dict[str, Any], *, source_sha: str,
    explicit_providers: list[str], repair_mode: bool = True,
) -> dict[str, int | bool]:
    """Fail closed on different provider or SHA; never infer an upstream URL.

    The producer may observe the current code's network and fixture behavior,
    but its output cannot grant publication, mutation or playable-media proof.
    """
    if (
        not isinstance(live, dict)
        or not isinstance(source_sha, str)
        or not re.fullmatch(r"[0-9a-f]{40}", source_sha)
        or live.get("sourceSha") != source_sha
        or live.get("provider") != request.provider_id
        or request.provider_id not in explicit_providers
    ):
        raise ValueError("live execution provider/SHA authority mismatch")
    if live.get("fixture_selection_complete") is False:
        raise ValueError("live execution fixture set is incomplete")
    ctx = request.provider_context
    if not isinstance(ctx, dict):
        raise ValueError("provider context must be a dictionary")
    active_functions = [
        name for name in (live.get("active_functions") or [])[:6]
        if isinstance(name, str) and re.fullmatch(r"[A-Za-z_$][\w$]{0,63}", name)
    ] if isinstance(live.get("active_functions") or [], list) else []
    recent_edits = live.get("previous_executed_edits")
    if not isinstance(recent_edits, list):
        recent_edits = []
    current = {
        "network_evidence": network_evidence(live.get("network_evidence")),
        "public_domain_references": public_domain_references(live.get("public_domain_references")),
        "fixture_evidence": fixture_evidence(live.get("fixture_evidence")),
        "previous_verification": verification_feedback(live.get("previous_verification")),
        "active_functions": active_functions,
        "previous_executed_edits": [
            {key: str(value)[:1800] for key, value in row.items()
             if key in {"scope", "family", "find", "replace", "diff"}}
            for row in recent_edits[-2:] if isinstance(row, dict)
        ],
    }
    ctx["live_runtime_evidence"] = current
    refs = current["public_domain_references"]
    if refs:
        request.observations.insert(0, {
            "stage": "public_domain_reference",
            "source": "immutable-public-upstream",
            "value": {"references": refs, "publicationAuthority": False},
            "instruction": (
                "These public origins are only candidate hints, not playback proof. "
                "External current-source media validation remains mandatory."
            ),
        })
    overridden = bool(
        repair_mode and apply_verified_live_failure(
            request, live, source_sha, explicit_providers,
        )
    )
    request.failure_class = observed_failure_class(request.failure_class, current)
    source = executed_runtime_source(ctx, current)
    if source:
        ctx["preferredRuntimeMutationSource"] = source
    return {
        "network_count": len(current["network_evidence"]),
        "fixture_count": len(current["fixture_evidence"]),
        "active_function_count": len(active_functions),
        "historical_prior_overridden": overridden,
        "fixture_selection_complete": live.get("fixture_selection_complete") is True,
    }
