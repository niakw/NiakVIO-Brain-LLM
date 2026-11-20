"""Source-pinned V31 Core candidate after a *failed and restored* native V30.

This is a deterministic Brain-owned causal Lego choice, not an LLM execution,
accepted repair, or permission to change published providers. It is applicable
to an HLS first-wins dedupe family, never merely to "zero streams" alone.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .contracts import RepairRequest
from .native_origin_experiments import (
    native_blocking_origin_priority_prior_attempt,
    _official_tv_rows,
)

SHA40 = re.compile(r"[a-f0-9]{40}")
SHA64 = re.compile(r"[a-f0-9]{64}")
RUN = re.compile(r"[0-9]{8,20}")
KEYS = (
    "experimentType", "providerId", "fixture", "requestType",
    "sourceNiakvioSha", "sourceRunId", "providerArtifactSha256",
    "officialClientSha", "runtimeScope", "evidencePattern",
    "parentExperimentFingerprint", "priorCandidateRunId",
    "priorCandidateSourceSha", "priorCandidateJsSha256",
)


def native_hls_receipt_dedupe_experiment(request: RepairRequest) -> dict[str, Any]:
    """Select one never-executed V31 when V30's exact bytes returned zero."""
    prior = native_blocking_origin_priority_prior_attempt(request)
    original = prior.get("candidate") or {}
    v29 = prior.get("attempt") or {}
    if not original or not (
        v29.get("candidateVerdict") == "candidate_zero_stream"
        and v29.get("candidateExecutionObserved") is True
        and v29.get("candidateRestoredObserved") is True
        and v29.get("candidateDecodedVideoObserved") is False
        and v29.get("validatedRepair") is False
        and v29.get("publicationAllowed") is False
    ):
        return {}
    # The original independently attested 200->403 replay remains mandatory.
    observed = [
        row for row in _official_tv_rows(request)
        if row.get("historicalOnly") is True
        and row.get("appSelected") is True
        and row.get("sameMediaRootSuccessThenForbidden") is True
        and row.get("nativeExtractionZeroObserved") is True
        and row.get("nativeHardTimeoutObserved") is False
        and row.get("tvPromiseControl") == "bridge_ok"
        and row.get("sourceNiakvioSha") == original.get("sourceNiakvioSha")
        and str(row.get("sourceRunId") or "") == str(original.get("sourceRunId") or "")
        and row.get("providerArtifactSha256") == original.get("providerArtifactSha256")
        and row.get("fixture") == original.get("fixture")
        and row.get("requestType") == original.get("requestType")
        and row.get("officialClientSha") == original.get("officialClientSha")
        and all(row.get(flag) is False for flag in (
            "proofAuthority", "publicationAuthority",
            "nativePlaybackAuthority", "providerMutationAuthority",
        ))
    ]
    if len(observed) != 1:
        return {}
    if not (
        SHA40.fullmatch(str(original.get("officialClientSha") or ""))
        and SHA64.fullmatch(str(original.get("providerArtifactSha256") or ""))
        and RUN.fullmatch(str(original.get("sourceRunId") or ""))
        and RUN.fullmatch(str(v29.get("candidateRunId") or ""))
    ):
        return {}
    ledger_rows = (request.provider_context or {}).get("native_candidate_experiment_history")
    if not isinstance(ledger_rows, list):
        return {}
    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for parent in ledger_rows[-8:]:
        if not isinstance(parent, dict) or (
            parent.get("providerId") != original.get("providerId")
            or parent.get("providerArtifactSha256") != original.get("providerArtifactSha256")
            or parent.get("runtimeScope") != "native-blocking-fetch"
        ):
            continue
        # Suppress a repeated V31 plan across the same current provider bytes.
        if parent.get("candidateV31ExperimentFingerprints"):
            return {}
        for follow in (parent.get("executedHlsReceiptFollowups") or [])[:4]:
            if not isinstance(follow, dict) or (
                follow.get("experimentType") != "native-hls-master-receipt-v30"
                or not SHA64.fullmatch(str(follow.get("experimentFingerprint") or ""))
                or str(follow.get("priorCandidateRunId") or "") != str(v29.get("candidateRunId") or "")
                or follow.get("priorCandidateSourceSha") != v29.get("candidateSourceSha")
                or follow.get("priorCandidateJsSha256") != v29.get("candidateJsSha256")
            ):
                continue
            for attempt in (follow.get("candidateAttempts") or [])[-8:]:
                if not isinstance(attempt, dict) or not (
                    attempt.get("candidateExperimentType") == "native-hls-master-receipt-v30"
                    and attempt.get("candidateVerdict") == "candidate_zero_stream"
                    and attempt.get("candidateExecutionObserved") is True
                    and attempt.get("candidateRestoredObserved") is True
                    and attempt.get("candidateDecodedVideoObserved") is False
                    and attempt.get("validatedRepair") is False
                    and attempt.get("publicationAllowed") is False
                    and RUN.fullmatch(str(attempt.get("candidateRunId") or ""))
                    and SHA40.fullmatch(str(attempt.get("candidateSourceSha") or ""))
                    and SHA64.fullmatch(str(attempt.get("candidateJsSha256") or ""))
                ):
                    continue
                candidates.append((follow, attempt))
    if len(candidates) != 1:
        return {}
    follow, attempt = candidates[0]
    payload = {
        "schemaVersion": 1,
        "experimentType": "native-hls-master-receipt-dedupe-v31",
        "providerId": original["providerId"],
        "fixture": original["fixture"],
        "requestType": original["requestType"],
        "sourceNiakvioSha": original["sourceNiakvioSha"],
        "sourceRunId": original["sourceRunId"],
        "providerArtifactSha256": original["providerArtifactSha256"],
        "officialClientSha": original["officialClientSha"],
        "runtimeScope": "native-blocking-fetch",
        "evidencePattern": "v30-zero-after-same-hls-root-2xx-403-first-wins-dedupe",
        "parentExperimentFingerprint": follow["experimentFingerprint"],
        "priorCandidateRunId": attempt["candidateRunId"],
        "priorCandidateSourceSha": attempt["candidateSourceSha"],
        "priorCandidateJsSha256": attempt["candidateJsSha256"],
        "candidateOnly": True, "generatedByBrain": True, "modelExecuted": False,
        "proofAuthority": False, "publicationAuthority": False,
        "nativePlaybackAuthority": False, "providerMutationAuthority": False,
    }
    payload["experimentFingerprint"] = hashlib.sha256(
        json.dumps({key: payload[key] for key in KEYS},
                   sort_keys=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    return payload


def native_hls_receipt_dedupe_positive_result(request: RepairRequest) -> dict[str, Any]:
    """Read one exact V31 decoded candidate without treating it as production proof.

    A successful terminal diagnostic changes the *verification frontier*,
    not the provider's published status. An attempted V31 with 0 streams,
    wrong source or missing rollback cannot bypass V29/V30 evidence gates.
    """
    prior = native_blocking_origin_priority_prior_attempt(request)
    original = prior.get("candidate") or {}
    v29 = prior.get("attempt") or {}
    if not original or not (
        v29.get("candidateVerdict") == "candidate_zero_stream"
        and v29.get("candidateExecutionObserved") is True
        and v29.get("candidateRestoredObserved") is True
        and v29.get("candidateDecodedVideoObserved") is False
        and v29.get("validatedRepair") is False
        and v29.get("publicationAllowed") is False
    ):
        return {}
    witnessed = [
        row for row in _official_tv_rows(request)
        if row.get("historicalOnly") is True
        and row.get("appSelected") is True
        and row.get("sameMediaRootSuccessThenForbidden") is True
        and row.get("nativeExtractionZeroObserved") is True
        and row.get("nativeHardTimeoutObserved") is False
        and row.get("tvPromiseControl") == "bridge_ok"
        and all(row.get(key) == original.get(key) for key in (
            "sourceNiakvioSha", "providerArtifactSha256",
            "officialClientSha", "fixture", "requestType",
        ))
        and str(row.get("sourceRunId") or "") == str(original.get("sourceRunId") or "")
        and all(row.get(flag) is False for flag in (
            "proofAuthority", "publicationAuthority",
            "nativePlaybackAuthority", "providerMutationAuthority",
        ))
    ]
    if len(witnessed) != 1:
        return {}
    ledger = (request.provider_context or {}).get("native_candidate_experiment_history")
    if not isinstance(ledger, list):
        return {}
    matched = []
    for parent in ledger[-8:]:
        if not isinstance(parent, dict) or (
            parent.get("providerId") != original.get("providerId")
            or parent.get("providerArtifactSha256") != original.get("providerArtifactSha256")
            or parent.get("runtimeScope") != "native-blocking-fetch"
        ):
            continue
        v30_plans = [
            x for x in (parent.get("executedHlsReceiptFollowups") or [])[:4]
            if isinstance(x, dict)
            and x.get("experimentType") == "native-hls-master-receipt-v30"
            and SHA64.fullmatch(str(x.get("experimentFingerprint") or ""))
        ]
        published_fingerprints = set(parent.get("candidateV31ExperimentFingerprints") or [])
        for child in (parent.get("executedHlsDedupeFollowups") or [])[:8]:
            if not isinstance(child, dict) or (
                child.get("experimentType") != "native-hls-master-receipt-dedupe-v31"
                or not SHA64.fullmatch(str(child.get("experimentFingerprint") or ""))
                or child.get("experimentFingerprint") not in published_fingerprints
                or not SHA64.fullmatch(str(child.get("parentExperimentFingerprint") or ""))
                or any(child.get(key) != original.get(key) for key in (
                    "sourceNiakvioSha", "officialClientSha", "fixture", "requestType",
                ))
                or str(child.get("sourceRunId") or "") != str(original.get("sourceRunId") or "")
            ):
                continue
            parents = [x for x in v30_plans if (
                x.get("experimentFingerprint") == child.get("parentExperimentFingerprint")
                and x.get("priorCandidateRunId") == str(v29.get("candidateRunId") or "")
                and x.get("priorCandidateSourceSha") == v29.get("candidateSourceSha")
                and x.get("priorCandidateJsSha256") == v29.get("candidateJsSha256")
            )]
            if len(parents) != 1:
                continue
            v30_results = [
                x for x in (parents[0].get("candidateAttempts") or [])[-8:]
                if isinstance(x, dict)
                and x.get("candidateExperimentType") == "native-hls-master-receipt-v30"
                and x.get("candidateVerdict") == "candidate_zero_stream"
                and x.get("candidateExecutionObserved") is True
                and x.get("candidateRestoredObserved") is True
                and x.get("candidateDecodedVideoObserved") is False
                and x.get("validatedRepair") is False
                and x.get("publicationAllowed") is False
                and str(x.get("candidateRunId") or "") == child.get("priorCandidateRunId")
                and x.get("candidateSourceSha") == child.get("priorCandidateSourceSha")
                and x.get("candidateJsSha256") == child.get("priorCandidateJsSha256")
            ]
            if len(v30_results) != 1:
                continue
            for attempt in (child.get("candidateAttempts") or [])[-8:]:
                if not isinstance(attempt, dict) or not (
                    attempt.get("candidateExperimentType") == child.get("experimentType")
                    and attempt.get("candidateVerdict") == "candidate_terminal_decode_observed"
                    and attempt.get("candidateExecutionObserved") is True
                    and attempt.get("candidateRestoredObserved") is True
                    and attempt.get("candidateExtractionNonEmpty") is True
                    and attempt.get("candidateTerminalReaderHealthy") is True
                    and attempt.get("candidateDecodedVideoObserved") is True
                    and type(attempt.get("candidateRuntimeReturnedCount")) is int
                    and 0 < attempt["candidateRuntimeReturnedCount"] <= 200
                    and attempt.get("validatedRepair") is False
                    and attempt.get("publicationAllowed") is False
                    and RUN.fullmatch(str(attempt.get("candidateRunId") or ""))
                    and SHA40.fullmatch(str(attempt.get("candidateSourceSha") or ""))
                    and SHA64.fullmatch(str(attempt.get("candidateJsSha256") or ""))
                ):
                    continue
                matched.append({
                    "experimentFingerprint": child["experimentFingerprint"],
                    "candidateRunId": str(attempt["candidateRunId"]),
                    "candidateSourceSha": attempt["candidateSourceSha"],
                    "candidateJsSha256": attempt["candidateJsSha256"],
                    "candidateRuntimeReturnedCount": attempt["candidateRuntimeReturnedCount"],
                    "candidateFrAudioObserved": attempt.get("candidateFrAudioObserved") is True,
                    "publicationAllowed": False,
                    "validatedRepair": False,
                })
    return matched[0] if len(matched) == 1 else {}
