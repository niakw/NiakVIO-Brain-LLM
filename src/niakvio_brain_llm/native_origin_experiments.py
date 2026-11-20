from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .contracts import RepairRequest

_HOST = re.compile(r"(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?")
_SHA40 = re.compile(r"[0-9a-f]{40}")
_SHA64 = re.compile(r"[0-9a-f]{64}")


def _official_tv_rows(request: RepairRequest) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for observation in request.observations or []:
        if not isinstance(observation, dict) or observation.get("source") != "official-android-tv-emulator":
            continue
        value = observation.get("value")
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _native_blocking_origin_priority_candidate(request: RepairRequest) -> dict[str, Any]:
    """Build the causal candidate before applying executed-experiment memory."""
    for row in _official_tv_rows(request):
        if not (
            row.get("appSelected") is True
            and row.get("nativeExtractionZeroObserved") is True
            and row.get("hlsPlaylist2xxNearProviderBudgetZeroObserved") is True
            and row.get("tvPromiseControl") == "bridge_ok"
            and row.get("nativeHardTimeoutObserved") is False
            and row.get("historicalOnly") is True
            and all(row.get(key) is False for key in (
                "proofAuthority", "publicationAuthority",
                "nativePlaybackAuthority", "providerMutationAuthority",
            ))
        ):
            continue
        source_sha = str(row.get("sourceNiakvioSha") or "").strip().lower()
        digest = str(row.get("providerArtifactSha256") or "").strip().lower()
        run_id = str(row.get("sourceRunId") or "")
        client_sha = str(row.get("officialClientSha") or "").strip().lower()
        if not (_SHA40.fullmatch(source_sha) and _SHA64.fullmatch(digest) and run_id.isdigit()):
            continue

        events: list[dict[str, Any]] = []
        for raw in (row.get("nativePrePlayerHostOutcomes") or [])[:12]:
            if not isinstance(raw, dict):
                continue
            kind = str(raw.get("kind") or "")
            host = str(raw.get("host") or "").strip().lower()
            status = raw.get("httpStatus")
            sequence = raw.get("sequence")
            if (
                kind not in {"player-page", "hls"}
                or type(status) is not int or not 200 <= status <= 599
                or type(sequence) is not int or not 1 <= sequence <= 999
                or (kind == "hls" and host != "")
                or (kind == "player-page" and not _HOST.fullmatch(host))
            ):
                continue
            events.append({
                "kind": kind, "host": host,
                "httpStatus": status, "sequence": sequence,
            })
        events.sort(key=lambda value: value["sequence"])

        for hls in [
            value for value in events
            if value["kind"] == "hls" and 200 <= value["httpStatus"] < 300
        ]:
            successful = [
                value for value in events
                if value["kind"] == "player-page"
                and 200 <= value["httpStatus"] < 300
                and value["sequence"] < hls["sequence"]
            ]
            if not successful:
                continue
            winner = successful[-1]
            failed = [
                value for value in events
                if value["kind"] == "player-page"
                and 500 <= value["httpStatus"] <= 599
                and value["sequence"] < winner["sequence"]
                and value["host"] != winner["host"]
            ]
            if not failed:
                continue
            deprioritized: list[str] = []
            for value in failed:
                if value["host"] not in deprioritized:
                    deprioritized.append(value["host"])
            payload: dict[str, Any] = {
                "schemaVersion": 1,
                "experimentType": "native-blocking-player-origin-priority",
                "providerId": request.provider_id,
                "fixture": str(row.get("fixture") or "")[:96],
                "requestType": str(row.get("requestType") or "")[:16],
                "sourceNiakvioSha": source_sha,
                "sourceRunId": run_id,
                "providerArtifactSha256": digest,
                "officialClientSha": client_sha if _SHA40.fullmatch(client_sha) else "",
                "runtimeScope": "native-blocking-fetch",
                "preferredHosts": [winner["host"]],
                "deprioritizedHosts": deprioritized[:4],
                "evidencePattern": "player-5xx-then-alternate-2xx-then-hls-2xx-near-budget-zero",
                "candidateOnly": True,
                "generatedByBrain": True,
                "proofAuthority": False,
                "publicationAuthority": False,
                "nativePlaybackAuthority": False,
                "providerMutationAuthority": False,
            }
            fingerprint_basis = {
                key: payload[key]
                for key in (
                    "experimentType", "providerId", "fixture", "requestType",
                    "sourceNiakvioSha", "sourceRunId", "providerArtifactSha256",
                    "officialClientSha", "runtimeScope", "preferredHosts",
                    "deprioritizedHosts", "evidencePattern",
                )
            }
            payload["experimentFingerprint"] = hashlib.sha256(
                json.dumps(
                    fingerprint_basis, sort_keys=True, separators=(",", ":"),
                ).encode("ascii")
            ).hexdigest()
            return payload
    return {}


def _matching_native_origin_attempt(
    request: RepairRequest, candidate: dict[str, Any],
) -> dict[str, Any]:
    history = (request.provider_context or {}).get("native_candidate_experiment_history")
    if not isinstance(history, list) or not candidate:
        return {}
    for row in reversed(history[-8:]):
        if not isinstance(row, dict):
            continue
        if (
            row.get("providerId") != candidate.get("providerId")
            or row.get("providerArtifactSha256") != candidate.get("providerArtifactSha256")
            or row.get("runtimeScope") != candidate.get("runtimeScope")
            or row.get("preferredHosts") != candidate.get("preferredHosts")
            or row.get("deprioritizedHosts") != candidate.get("deprioritizedHosts")
            or row.get("evidencePattern") != candidate.get("evidencePattern")
            or row.get("candidateOnly") is not True
            or row.get("generatedByBrain") is not True
            or any(row.get(flag) is not False for flag in (
                "proofAuthority", "publicationAuthority",
                "nativePlaybackAuthority", "providerMutationAuthority",
            ))
        ):
            continue
        attempts = row.get("candidateAttempts")
        if not isinstance(attempts, list):
            continue
        for attempt in reversed(attempts[-8:]):
            if not isinstance(attempt, dict):
                continue
            verdict = str(attempt.get("candidateVerdict") or "")
            if verdict not in {
                "candidate_integrity_failure",
                "candidate_not_executed",
                "candidate_zero_stream",
                "candidate_runtime_nonempty_unconfirmed_extraction",
                "candidate_extraction_improved_reader_unverified",
                "candidate_reader_healthy_decode_unverified",
                "candidate_terminal_decode_observed",
            }:
                continue
            return {
                "candidateRunId": str(attempt.get("candidateRunId") or ""),
                "candidateSourceSha": str(attempt.get("candidateSourceSha") or ""),
                "candidateJsSha256": str(attempt.get("candidateJsSha256") or ""),
                "candidateExecutionObserved": attempt.get("candidateExecutionObserved") is True,
                "candidateRuntimeReturnedCount": int(
                    attempt.get("candidateRuntimeReturnedCount") or 0
                ),
                "candidateRestoredObserved": attempt.get("candidateRestoredObserved") is True,
                "candidateExtractionNonEmpty": attempt.get("candidateExtractionNonEmpty") is True,
                "candidateTerminalReaderHealthy": attempt.get("candidateTerminalReaderHealthy") is True,
                "candidateDecodedVideoObserved": attempt.get("candidateDecodedVideoObserved") is True,
                "candidateFrAudioObserved": attempt.get("candidateFrAudioObserved") is True,
                "candidateVerdict": verdict,
                "validatedRepair": attempt.get("validatedRepair") is True,
                "publicationAllowed": attempt.get("publicationAllowed") is True,
            }
    return {}


def native_blocking_origin_priority_prior_attempt(request: RepairRequest) -> dict[str, Any]:
    """Return the prior bounded verdict for this exact causal strategy/bytes."""
    candidate = _native_blocking_origin_priority_candidate(request)
    if not candidate:
        return {}
    attempt = _matching_native_origin_attempt(request, candidate)
    if not attempt:
        return {}
    return {"candidate": candidate, "attempt": attempt}


def native_blocking_origin_priority_experiment(request: RepairRequest) -> dict[str, Any]:
    """Generate V29 once; executed history must change the next strategy."""
    candidate = _native_blocking_origin_priority_candidate(request)
    if not candidate or _matching_native_origin_attempt(request, candidate):
        return {}
    return candidate
