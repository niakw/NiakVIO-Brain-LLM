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

def _provider_targeted_observation(payload: Any, provider_id: str) -> dict[str, Any]:
    providers = payload.get("providers") if isinstance(payload, dict) else None
    if not isinstance(providers, dict):
        return {}
    wanted = _canon(provider_id)
    row = next(
        (
            value for key, value in providers.items()
            if _canon(key) == wanted and isinstance(value, dict)
        ),
        {},
    )
    if not row:
        return {}

    network_out: dict[str, list[dict[str, Any]]] = {}
    network = row.get("network") if isinstance(row.get("network"), dict) else {}
    for lane, values in list(network.items())[:8]:
        if not isinstance(values, list):
            continue
        safe_rows: list[dict[str, Any]] = []
        for value in values[:16]:
            if not isinstance(value, dict):
                continue
            safe_rows.append({
                "method": str(value.get("method") or "")[:12],
                "host": str(value.get("host") or "")[:120],
                "path": str(value.get("path") or "")[:180],
                "status": value.get("status"),
            })
        if safe_rows:
            network_out[str(lane)[:40]] = safe_rows

    return {
        "debugStages": row.get("debugStages") or {},
        "statuses": row.get("statuses") or {},
        "verifiedLanes": [str(x)[:40] for x in (row.get("verifiedLanes") or [])[:8]],
        "playableLanes": [str(x)[:40] for x in (row.get("playableLanes") or [])[:8]],
        "contradictions": int(row.get("contradictions") or 0),
        "sampleTitles": {
            str(lane)[:40]: [str(x)[:120] for x in values[:8]]
            for lane, values in (row.get("sampleTitles") or {}).items()
            if isinstance(values, list)
        },
        "network": network_out,
    }

def _provider_refined_groups(payload: Any, provider_id: str, *, census_run_id: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    source_run = str(payload.get("sourceRunId") or payload.get("sourcePlanRunId") or "")
    if census_run_id and source_run and source_run != census_run_id:
        return []
    wanted = _canon(provider_id)
    out: list[dict[str, Any]] = []
    for group in payload.get("groups") or []:
        if not isinstance(group, dict):
            continue
        providers = {_canon(value) for value in group.get("providers") or []}
        if wanted not in providers:
            continue
        out.append({
            "groupId": str(group.get("groupId") or "")[:180],
            "parentGroupId": str(group.get("parentGroupId") or "")[:180],
            "repairScope": str(group.get("repairScope") or "")[:80],
            "capabilityStrategy": str(group.get("capabilityStrategy") or "")[:100],
            "transportSignature": str(group.get("transportSignature") or "")[:120],
            "evidenceDepths": [str(x)[:80] for x in (group.get("evidenceDepths") or [])[:12]],
            "dominantIssues": [str(x)[:100] for x in (group.get("dominantIssues") or [])[:12]],
            "debugStages": [str(x)[:120] for x in (group.get("debugStages") or [])[:12]],
            "networkShape": [str(x)[:240] for x in (group.get("networkShape") or [])[:24]],
            "splitReason": str(group.get("splitReason") or "")[:120],
        })
    return out[:4]

def _provider_negative_memory(payload: Any, provider_id: str) -> list[dict[str, Any]]:
    """Return bounded provider-local failed experiment memory from current NiakVIO state."""
    if not isinstance(payload, dict):
        return []
    wanted = _canon(provider_id)
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return []
    out: list[dict[str, Any]] = []
    for value in entries:
        if not isinstance(value, dict) or _canon(value.get("providerId")) != wanted:
            continue
        out.append({
            "failureClass": str(value.get("failureClass") or "")[:120],
            "profile": str(value.get("profile") or "")[:120],
            "llmAdvisorExperimentFingerprint": str(value.get("llmAdvisorExperimentFingerprint") or "")[:80],
            "experimentVariant": value.get("experimentVariant"),
            "experimentGeneration": value.get("experimentGeneration"),
            "consecutiveFailures": int(value.get("consecutiveFailures") or 0),
            "failures": int(value.get("failures") or 0),
            "successes": int(value.get("successes") or 0),
            "lastOutcome": str(value.get("lastOutcome") or "")[:120],
            "lastReason": str(value.get("lastReason") or "")[:240],
            "executionObserved": value.get("executionObserved") is True,
        })
    return out[:32]

def classify_census_failure(row: dict[str, Any]) -> str:
    explicit = str(row.get("failureClass") or "").strip()
    if explicit:
        return explicit

    status = _canon(row.get("status"))
    depths = " ".join(str(x) for x in row.get("evidenceDepth") or []).casefold()
    dominant = str(row.get("dominantIssue") or "").strip()

    if (
        "harness mismatch" in status
        or "harness/env blocked" in status
        or "client transport gap" in status
    ):
        return "transport_environment_gap"

    if row.get("candidateProof") or "candidate ok" in status:
        return "candidate_replay_gap"

    if "chain_reached" in depths or "chain reached" in status:
        return "chain_terminal_gap"

    if row.get("routeProof") or "route proven" in status:
        return "route_proven_gap"

    if "provider network blocked" in status:
        return "provider_transport_gap"

    if any(token in dominant for token in (
        "provider_network_http_error",
        "provider_network_exception",
        "provider_waf_challenge",
    )):
        return "provider_transport_gap"

    return dominant or str(row.get("status") or "unknown")

def request_from_checkout(root: str | Path, provider_id: str) -> RepairRequest:
    """Build one bounded LLM request from a read-only NiakVIO checkout."""
    root = Path(root)
    wanted = _canon(provider_id)

    census = _load(root / "automation" / "provider-census-status.json", {})
    experience = _load(root / "automation" / "brain-repair-experience.json", {})
    memory = _load(root / "automation" / "brain-repair-memory.json", {})
    targeted = _load(root / "automation" / "provider-targeted-regression-recovery-latest.json", {})
    refined = _load(root / "automation" / "provider-repair-batch-refined-latest.json", {})

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

    negative_memory = _provider_negative_memory(memory, provider_id)

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

    targeted_observation = _provider_targeted_observation(targeted, provider_id)
    refined_groups = _provider_refined_groups(
        refined,
        provider_id,
        census_run_id=str(census.get("runId") or ""),
    )

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

    provider_context = build_provider_context(root, provider_id)
    provider_context["advisor_experiment_history"] = negative_memory

    return RepairRequest(
        provider_id=provider_id,
        failure_class=str(failure),
        status=str(row.get("status") or ""),
        supported_types=[str(x) for x in supported][:8],
        census_prior=census_prior,
        observations=[
            {"source": "census_current", "value": census_prior},
            *(
                [{"source": "targeted-regression-current", "value": targeted_observation}]
                if targeted_observation else []
            ),
            *(
                [{"source": "refined-repair-batch-current", "value": refined_groups}]
                if refined_groups else []
            ),
            {"source": "brain-repair-experience", "value": provider_experience[:4]},
            {"source": "brain-repair-memory", "value": negative_memory[:4]},
        ],
        provider_context=provider_context,
    )
