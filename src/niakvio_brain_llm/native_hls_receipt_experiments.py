"""Candidate-only Brain strategy: reuse the first verified in-memory HLS root.

This is a *deterministic* Brain-owned causal experiment selected after an
actually executed, zero-stream V29 attempt. It does not call a model, patch a
provider, persist signed URL/headers, certify playback or grant publication.
The executor must compile the generic Core/ProviderBase Lego on exact bytes.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .contracts import RepairRequest
from .native_origin_experiments import native_blocking_origin_priority_prior_attempt

_SHA40 = re.compile(r"[0-9a-f]{40}")
_SHA64 = re.compile(r"[0-9a-f]{64}")
_RUN = re.compile(r"[0-9]{8,20}")


def native_hls_root_receipt_experiment(request: RepairRequest) -> dict[str, Any]:
    """Select the next *distinct* Core experiment from trustworthy negative memory."""
    prior = native_blocking_origin_priority_prior_attempt(request)
    if not prior:
        return {}
    attempt = prior.get("attempt") or {}
    candidate = prior.get("candidate") or {}
    if not (
        attempt.get("candidateVerdict") == "candidate_zero_stream"
        and attempt.get("candidateExecutionObserved") is True
        and attempt.get("candidateRestoredObserved") is True
        and attempt.get("candidateDecodedVideoObserved") is False
        and _SHA40.fullmatch(str(attempt.get("candidateSourceSha") or ""))
        and _SHA64.fullmatch(str(attempt.get("candidateJsSha256") or ""))
        and _RUN.fullmatch(str(attempt.get("candidateRunId") or ""))
    ):
        return {}

    rows = [
        o.get("value") for o in (request.observations or [])
        if isinstance(o, dict) and o.get("source") == "official-android-tv-emulator"
        and isinstance(o.get("value"), dict)
    ]
    matched = False
    for row in rows:
        if (
            row.get("appSelected") is True
            and row.get("nativeExtractionZeroObserved") is True
            and row.get("sameMediaRootSuccessThenForbidden") is True
            and row.get("tvPromiseControl") == "bridge_ok"
            and row.get("historicalOnly") is True
            and row.get("nativeHardTimeoutObserved") is False
            and row.get("sourceNiakvioSha") == candidate.get("sourceNiakvioSha")
            and row.get("providerArtifactSha256") == candidate.get("providerArtifactSha256")
            and str(row.get("sourceRunId")) == str(candidate.get("sourceRunId"))
            and row.get("fixture") == candidate.get("fixture")
            and row.get("requestType") == candidate.get("requestType")
            and row.get("officialClientSha") == candidate.get("officialClientSha")
            and all(row.get(flag) is False for flag in (
                "proofAuthority", "publicationAuthority",
                "nativePlaybackAuthority", "providerMutationAuthority",
            ))
        ):
            matched = True
            break
    if not matched:
        return {}

    keys = (
        "experimentType", "providerId", "fixture", "requestType",
        "sourceNiakvioSha", "sourceRunId", "providerArtifactSha256",
        "officialClientSha", "runtimeScope", "evidencePattern",
        "priorCandidateRunId", "priorCandidateSourceSha",
        "priorCandidateJsSha256",
    )
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "experimentType": "native-hls-master-receipt-v30",
        "providerId": candidate["providerId"],
        "fixture": candidate["fixture"],
        "requestType": candidate["requestType"],
        "sourceNiakvioSha": candidate["sourceNiakvioSha"],
        "sourceRunId": candidate["sourceRunId"],
        "providerArtifactSha256": candidate["providerArtifactSha256"],
        "officialClientSha": candidate["officialClientSha"],
        "runtimeScope": "native-blocking-fetch",
        "evidencePattern": "same-hls-root-2xx-then-403-pre-player",
        "priorCandidateRunId": attempt["candidateRunId"],
        "priorCandidateSourceSha": attempt["candidateSourceSha"],
        "priorCandidateJsSha256": attempt["candidateJsSha256"],
        "candidateOnly": True,
        "generatedByBrain": True,
        "modelExecuted": False,
        "proofAuthority": False,
        "publicationAuthority": False,
        "nativePlaybackAuthority": False,
        "providerMutationAuthority": False,
    }
    # A completed or queued V30 must not become a new V29 parent. The
    # fingerprint is source-pinned and redacted, never a signed media URL.
    history = (request.provider_context or {}).get("native_candidate_experiment_history")
    if isinstance(history, list) and any(
        isinstance(row, dict)
        and row.get("providerArtifactSha256") == candidate.get("providerArtifactSha256")
        and row.get("providerId") == candidate.get("providerId")
        and (row.get("candidateFollowUpExperimentFingerprints") or [])
        for row in history
    ):
        return {}

    payload["experimentFingerprint"] = hashlib.sha256(
        json.dumps(
            {k: payload[k] for k in keys}, sort_keys=True, separators=(",", ":"),
        ).encode("ascii")
    ).hexdigest()
    return payload
