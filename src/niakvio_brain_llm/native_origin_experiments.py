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


def native_blocking_origin_priority_experiment(request: RepairRequest) -> dict[str, Any]:
    """Build candidate-only origin ordering from exact official native evidence."""
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
