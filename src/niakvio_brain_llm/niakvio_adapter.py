from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import RepairRequest
from .provider_context import build_provider_context

def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

def _canon(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().replace("_", " ").split())

def classify_census_failure(row: dict[str, Any]) -> str:
    explicit = str(row.get("failureClass") or "").strip()
    if explicit:
        return explicit

    status = _canon(row.get("status"))
    depths = " ".join(str(x) for x in row.get("evidenceDepth") or []).casefold()
    dominant = str(row.get("dominantIssue") or "").strip()

    if "harness mismatch" in status or "harness/env blocked" in status:
        return "transport_environment_gap"

    if row.get("candidateProof") or "candidate ok" in status:
        return "candidate_replay_gap"

    if "chain_reached" in depths or "chain reached" in status:
        return "chain_terminal_gap"

    if row.get("routeProof") or "route proven" in status:
        return "route_proven_gap"

    if "provider network blocked" in status:
        return "provider_transport_gap"

    if "provider_network_http_error" in dominant:
        return "provider_transport_gap"

    return dominant or str(row.get("status") or "unknown")

def request_from_checkout(root: str | Path, provider_id: str) -> RepairRequest:
    """Build one bounded LLM request from a read-only NiakVIO checkout."""
    root = Path(root)
    wanted = _canon(provider_id)

    census = _load(root / "automation" / "provider-census-status.json", {})
    experience = _load(root / "automation" / "brain-repair-experience.json", {})
    memory = _load(root / "automation" / "brain-repair-memory.json", {})

    row: dict[str, Any] = {}
    for candidate in census.get("providers") or []:
        if isinstance(candidate, dict) and _canon(candidate.get("provider")) == wanted:
            row = candidate
            break

    failure = classify_census_failure(row)

    provider_experience: list[Any] = []
    if isinstance(experience, dict):
        for key in ("providers", "providerExperience", "experiences"):
            block = experience.get(key)
            if isinstance(block, dict):
                value = block.get(provider_id) or block.get(wanted)
                if value:
                    provider_experience.append(value)

    negative_memory: list[Any] = []
    if isinstance(memory, dict):
        for key in ("providers", "entries", "memory"):
            block = memory.get(key)
            if isinstance(block, dict):
                value = block.get(provider_id) or block.get(wanted)
                if value:
                    negative_memory.append(value)

    supported = (
        row.get("declaredLanes")
        or row.get("declaredTypes")
        or row.get("supportedTypes")
        or row.get("types")
        or []
    )
    if isinstance(supported, str):
        supported = [part.strip() for part in supported.split(";") if part.strip()]
    if not isinstance(supported, list):
        supported = []

    census_prior = {
        "status": row.get("status"),
        "underlyingStatus": row.get("underlyingStatus"),
        "dominantIssue": row.get("dominantIssue"),
        "repairEligible": row.get("repairEligible"),
        "brainCheckRequired": row.get("brainCheckRequired"),
        "authorityClass": row.get("authorityClass"),
        "authorityConfidence": row.get("authorityConfidence"),
        "authorityAction": row.get("authorityAction"),
        "latestLaneVerdicts": row.get("latestLaneVerdicts") or [],
        "evidenceDepth": row.get("evidenceDepth") or [],
        "routeProof": row.get("routeProof") or [],
        "candidateProof": row.get("candidateProof") or [],
        "harnessTransportClass": row.get("harnessTransportClass"),
        "harnessTransportEvidence": row.get("harnessTransportEvidence") or [],
    }

    return RepairRequest(
        provider_id=provider_id,
        failure_class=str(failure),
        status=str(row.get("status") or ""),
        supported_types=[str(x) for x in supported][:8],
        census_prior=census_prior,
        observations=[
            {"source": "census_current", "value": census_prior},
            {"source": "brain-repair-experience", "value": provider_experience[:4]},
            {"source": "brain-repair-memory", "value": negative_memory[:4]},
        ],
        provider_context=build_provider_context(root, provider_id),
    )
