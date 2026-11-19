from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .contracts import RepairRequest
from .provider_context import build_provider_context, build_validated_reference_patterns

def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

def _canon(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().replace("_", " ").split())

def _provider_current_structure_evidence(payload: Any, provider_id: str) -> dict[str, Any]:
    """Project current provider structure into bounded, observation-only Brain evidence."""
    providers = payload.get("providers") if isinstance(payload, dict) else None
    if not isinstance(providers, dict):
        return {}
    wanted = _canon(provider_id)
    raw = next(
        (
            value for key, value in providers.items()
            if _canon(key) == wanted and isinstance(value, dict)
        ),
        {},
    )
    if not raw:
        return {}

    origin_host = str(raw.get("originHost") or "").strip().casefold()[:160]
    if origin_host and not all(ch.isalnum() or ch in ".-" for ch in origin_host):
        origin_host = ""

    routes: list[dict[str, Any]] = []
    for value in (raw.get("routes") or [])[:12]:
        if not isinstance(value, dict):
            continue
        path = str(value.get("path") or "").strip()
        if not path.startswith("/") or len(path) > 260:
            continue
        method = str(value.get("method") or "").strip().upper()[:12]
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "UNKNOWN", ""}:
            method = "UNKNOWN"
        role = str(value.get("role") or "").strip()[:80]
        row_out: dict[str, Any] = {"path": path}
        if method:
            row_out["method"] = method
        if role:
            row_out["role"] = role
        routes.append(row_out)

    request_keys = [
        str(value)[:48]
        for value in (raw.get("requestKeys") or [])[:24]
        if str(value)
        and str(value)[0].isalpha()
        and all(ch.isalnum() or ch in "_-" for ch in str(value))
    ]

    fanout_raw = raw.get("fanout") if isinstance(raw.get("fanout"), dict) else {}

    def bounded_int(value: Any, limit: int) -> int:
        try:
            return max(0, min(int(value or 0), limit))
        except (TypeError, ValueError):
            return 0

    group_counts = [
        bounded_int(value, 128)
        for value in (fanout_raw.get("groupVariantCounts") or [])[:16]
        if bounded_int(value, 128) > 0
    ]
    language_labels = [
        str(value)[:24].upper()
        for value in (fanout_raw.get("languageLabels") or [])[:16]
        if str(value).strip()
        and all(ch.isalnum() or ch in "_-" for ch in str(value))
    ]
    quality_height_values: set[int] = set()
    for value in (fanout_raw.get("qualityHeights") or [])[:16]:
        try:
            height = int(value)
        except (TypeError, ValueError):
            continue
        if 144 <= height <= 4320:
            quality_height_values.add(height)
    quality_heights = sorted(quality_height_values)
    fanout = {
        "groupCount": bounded_int(fanout_raw.get("groupCount"), 32),
        "groupVariantCounts": group_counts,
        "indexedVariantCount": bounded_int(fanout_raw.get("indexedVariantCount"), 512),
        "qualityHeights": quality_heights,
        "languageLabels": language_labels,
    }

    return {
        "role": "current-provider-structure-observation",
        "proofAuthority": False,
        "executionAuthority": False,
        "sourceKind": str(raw.get("sourceKind") or "manual-current-observation")[:80],
        "observedAt": str(raw.get("observedAt") or "")[:32],
        **({"originHost": origin_host} if origin_host else {}),
        "routes": routes,
        "requestKeys": request_keys,
        "fanout": fanout,
    }


def _safe_response_shape(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    kind = str(value.get("kind") or "")[:24]
    if kind not in {"json", "html", "javascript"}:
        return {}
    out: dict[str, Any] = {"kind": kind}
    if kind == "json":
        top = str(value.get("top") or "")[:24]
        if top:
            out["top"] = top
        for key, rows in value.items():
            if key == "keys" or key == "itemKeys" or key.endswith("Keys") or key.endswith("ItemKeys"):
                if isinstance(rows, list):
                    out[key] = [
                        str(item)[:48]
                        for item in rows[:16]
                        if str(item) and all(ch.isalnum() or ch in "_.:-" for ch in str(item))
                    ]
            elif key == "lengthBucket" or key.endswith("Type"):
                out[key] = str(rows)[:24]
        return out
    for key in ("sampleBytes", "forms", "iframes", "videos", "sources", "scripts", "anchors", "functions", "fetchCalls"):
        raw = value.get(key)
        if type(raw) is int:
            out[key] = max(0, min(raw, 65536 if key == "sampleBytes" else 99))
    for key, limit in (("classTokens", 16), ("idTokens", 12)):
        rows = value.get(key)
        if isinstance(rows, list):
            safe = [
                item
                for item in rows[:limit]
                if isinstance(item, str)
                and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,47}", item)
            ]
            if safe:
                out[key] = safe
    facts = value.get("classFacts")
    if isinstance(facts, list):
        safe_facts = []
        allowed_signals = {"movie", "series", "season", "episode", "download", "4k", "1080p", "720p", "year"}
        for row in facts[:8]:
            if not isinstance(row, dict):
                continue
            # Reject malformed evidence rather than manufacture a selector
            # through truncation or coercion of a JSON scalar.
            token = row.get("token")
            if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,47}", token):
                continue
            counters = {key: row.get(key, 0) for key in ("count", "selfHref", "nestedAnchors")}
            if any(type(raw) is not int for raw in counters.values()):
                continue
            raw_tags = row.get("tags")
            tags = [
                tag.lower()
                for tag in (raw_tags[:4] if isinstance(raw_tags, list) else [])
                if isinstance(tag, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,15}", tag)
            ]
            raw_signals = row.get("signals")
            safe_facts.append({
                "token": token,
                "count": max(0, min(counters["count"], 12)),
                "tags": tags,
                "selfHref": max(0, min(counters["selfHref"], 12)),
                "nestedAnchors": max(0, min(counters["nestedAnchors"], 24)),
                "signals": [
                    sig for sig in (raw_signals[:9] if isinstance(raw_signals, list) else [])
                    if isinstance(sig, str) and sig in allowed_signals
                ],
            })
        if safe_facts:
            out["classFacts"] = safe_facts
    markers = value.get("markers")
    allowed = {"next-data", "json-ld", "player", "download", "episode", "hls-literal", "mp4-literal", "turnstile", "embed"}
    if isinstance(markers, list):
        out["markers"] = [str(item) for item in markers[:12] if str(item) in allowed]
    return out


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
        shape_index: dict[tuple[str, str, str, str], int] = {}
        for value in values[:16]:
            if not isinstance(value, dict):
                continue
            method = str(value.get("method") or "")[:12]
            host = str(value.get("host") or "")[:120]
            path = str(value.get("path") or "")[:180]
            status = value.get("status")
            shape = _safe_response_shape(value.get("shape"))
            if shape:
                signature = (
                    method,
                    host,
                    str(status),
                    json.dumps(shape, sort_keys=True, separators=(",", ":")),
                )
                prior_index = shape_index.get(signature)
                if prior_index is not None:
                    safe_rows[prior_index]["sameShapeRoutes"] = int(
                        safe_rows[prior_index].get("sameShapeRoutes") or 1
                    ) + 1
                    continue
            row_out = {
                "method": method,
                "host": host,
                "path": path,
                "status": status,
                **({"shape": shape} if shape else {}),
            }
            safe_rows.append(row_out)
            if shape:
                shape_index[signature] = len(safe_rows) - 1
            if len(safe_rows) >= 10:
                break
        if safe_rows:
            network_out[str(lane)[:40]] = safe_rows

    structure_hints: list[str] = []
    for lane, values in network_out.items():
        for value in values:
            shape = value.get("shape") if isinstance(value, dict) else None
            if not isinstance(shape, dict) or shape.get("kind") != "html":
                continue
            classes = [str(x) for x in (shape.get("classTokens") or [])[:12]]
            ids = [str(x) for x in (shape.get("idTokens") or [])[:8]]
            markers = [str(x) for x in (shape.get("markers") or [])[:8]]
            facts = []
            for fact in (shape.get("classFacts") or [])[:6]:
                if not isinstance(fact, dict):
                    continue
                bits = [
                    str(fact.get("token") or ""),
                    "count=" + str(int(fact.get("count") or 0)),
                    "selfHref=" + str(int(fact.get("selfHref") or 0)),
                    "nestedAnchors=" + str(int(fact.get("nestedAnchors") or 0)),
                ]
                tags = [str(x) for x in (fact.get("tags") or [])[:4]]
                signals = [str(x) for x in (fact.get("signals") or [])[:9]]
                if tags:
                    bits.append("tags=" + ",".join(tags))
                if signals:
                    bits.append("signals=" + ",".join(signals))
                facts.append("[" + ";".join(bits) + "]")
            parts = []
            if classes:
                parts.append("classes=" + ",".join(classes))
            if ids:
                parts.append("ids=" + ",".join(ids))
            if markers:
                parts.append("markers=" + ",".join(markers))
            if facts:
                parts.append("classFacts=" + "".join(facts))
            if parts:
                structure_hints.append(str(lane)[:40] + ":" + ";".join(parts))
            break

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
        "structureHints": structure_hints[:8],
    }

def _provider_sharded_observation(payload: Any, provider_id: str) -> dict[str, Any]:
    """Project exact current sharded-census rows into the bounded targeted shape."""
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return {}
    wanted = _canon(provider_id)
    debug_stages: dict[str, str] = {}
    statuses: dict[str, str] = {}
    network: dict[str, list[dict[str, Any]]] = {}
    sample_titles: dict[str, list[str]] = {}
    fanout: dict[str, dict[str, Any]] = {}
    verified_lanes: list[str] = []
    playable_lanes: list[str] = []
    contradictions = 0

    for row in rows:
        if not isinstance(row, dict) or _canon(row.get("provider_id")) != wanted:
            continue
        lane = str(row.get("semantic_type") or "")[:40]
        if not lane:
            continue
        stage = str(row.get("debug_stage") or "")[:80]
        status = str(row.get("status") or "")[:80]
        if stage:
            debug_stages[lane] = stage
        if status:
            statuses[lane] = status
        contradictions += max(0, int(row.get("contradictions") or 0))
        if row.get("verified") is True and lane not in verified_lanes:
            verified_lanes.append(lane)
        if row.get("playable") is True and lane not in playable_lanes:
            playable_lanes.append(lane)
        titles = [
            str(value)[:120]
            for value in (row.get("sample_titles") or [])
            if str(value).strip()
        ][:8]
        if titles:
            sample_titles[lane] = titles

        fanout_state = str(row.get("variant_fanout_state") or "")[:80].casefold()
        announced_players = max(0, int(row.get("announced_player_candidates") or 0))
        announced_variants = max(0, int(row.get("announced_variant_candidates") or 0))
        explored_requests = max(0, int(row.get("explored_player_requests") or 0))
        streams_returned = max(0, int(row.get("streams_returned") or row.get("raw") or 0))
        if (
            fanout_state
            or announced_players
            or announced_variants
            or explored_requests
        ):
            fanout[lane] = {
                "streamsReturned": streams_returned,
                "streamsPlayable": max(0, int(row.get("playable") or 0)),
                "streamsVerified": max(0, int(row.get("verified") or 0)),
                "announcedPlayerCandidates": announced_players,
                "announcedVariantCandidates": announced_variants,
                "announcedPlayerHosts": [
                    str(value)[:160].casefold()
                    for value in (row.get("announced_player_hosts") or [])[:24]
                    if str(value).strip()
                ],
                "announcedQualityHeights": [
                    int(value)
                    for value in (row.get("announced_quality_heights") or [])[:12]
                    if str(value or "").isdigit() and int(value) > 0
                ],
                "exploredPlayerRequests": explored_requests,
                "exploredPlayerHosts": [
                    str(value)[:160].casefold()
                    for value in (row.get("explored_player_hosts") or [])[:24]
                    if str(value).strip()
                ],
                "state": fanout_state,
                "fixtureTitle": str(row.get("fanout_fixture_title") or row.get("fixture_title") or "")[:160],
            }

        safe_fetches: list[dict[str, Any]] = []
        for fetch in (row.get("debug_fetches") or [])[:16]:
            if not isinstance(fetch, dict):
                continue
            raw_url = str(fetch.get("response_url") or fetch.get("url") or "")
            try:
                parsed = urlsplit(raw_url)
            except ValueError:
                continue
            host = str(parsed.hostname or "")[:120]
            path = str(parsed.path or "/")[:180]
            shape = _safe_response_shape(fetch.get("response_shape") or fetch.get("shape"))
            safe_fetches.append({
                "method": str(fetch.get("method") or "")[:12],
                "host": host,
                "path": path,
                "status": fetch.get("status"),
                **({"shape": shape} if shape else {}),
            })
        if safe_fetches:
            network[lane] = safe_fetches

    if not debug_stages and not statuses and not network and not fanout:
        return {}
    result = _provider_targeted_observation(
        {
            "providers": {
                provider_id: {
                    "debugStages": debug_stages,
                    "statuses": statuses,
                    "verifiedLanes": verified_lanes,
                    "playableLanes": playable_lanes,
                    "contradictions": contradictions,
                    "sampleTitles": sample_titles,
                    "network": network,
                }
            }
        },
        provider_id,
    )
    if fanout:
        result["fanout"] = fanout
    return result


def _dynamic_variant_coverage_gap(observation: dict[str, Any]) -> bool:
    """Treat current multi-player/server census evidence as repairable completeness debt."""
    fanout = observation.get("fanout") if isinstance(observation, dict) else None
    if not isinstance(fanout, dict):
        return False
    gap_states = {
        "announced-not-explored",
        "explored-not-resolved",
        "returned-subset",
        "quality-gap",
    }
    for raw in fanout.values():
        if not isinstance(raw, dict):
            continue
        announced = max(0, int(raw.get("announcedVariantCandidates") or 0))
        returned = max(0, int(raw.get("streamsReturned") or 0))
        state = str(raw.get("state") or "").strip().casefold()
        if announced >= 2 and (state in gap_states or returned < announced):
            return True
    return False


_USER_CLIENT_OBSERVATION_STATES = frozenset({
    "stream-played", "stream-returned", "not-in-stream-list",
    "stream-playback-failed", "provider-disabled-in-ui",
    "provider-not-installed", "unknown",
})
_USER_CLIENT_NAMES = frozenset({
    "desktop-macos", "desktop-windows", "android-tv",
    "android-mobile", "ios", "unspecified",
})


def _provider_user_client_field_observation(
    payload: Any,
    provider_id: str,
    *,
    active_manifest_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """Sanitize user field observations; never turn a report into current proof.

    A Desktop stream playing and an Android TV stream missing can be a client,
    manifest-cache, media-type, runtime, network, or display difference. Without
    the installed build and executed JS hash, this is diagnosis context only.
    """
    if (
        not isinstance(payload, dict)
        or payload.get("schemaVersion") != 1
        or payload.get("authority") != "non-authoritative-user-field-report"
        or payload.get("proofAuthority") is not False
        or payload.get("publicationAuthority") is not False
        or payload.get("sourceBundleVerified") is not False
    ):
        return {}
    wanted = _canon(provider_id)
    reported = str(payload.get("reportedOn") or "")
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", reported):
        return {}
    for row in (payload.get("rows") or [])[:50]:
        if not isinstance(row, dict) or _canon(row.get("provider")) != wanted:
            continue
        if row.get("fixtureKnown") is not False:
            # Unknown user fixture cannot be silently assigned from a previous
            # assistant test request or synthetic Retest fixture.
            continue
        clients: list[dict[str, Any]] = []
        for item in (row.get("clients") or [])[:6]:
            if not isinstance(item, dict):
                continue
            client = str(item.get("client") or "")
            result = str(item.get("observation") or "")
            if client not in _USER_CLIENT_NAMES or result not in _USER_CLIENT_OBSERVATION_STATES:
                continue
            observed_count = item.get("streamCountObserved")
            audio = item.get("audioLanguagesObserved")
            languages = [
                value.casefold() for value in (audio if isinstance(audio, list) else [])[:8]
                if isinstance(value, str) and re.fullmatch(r"[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8}){0,2}", value)
            ][:4]
            clients.append({
                "client": client,
                "observation": result,
                "streamCountObserved": (
                    min(20, observed_count) if type(observed_count) is int
                    and 0 <= observed_count <= 20 else None
                ),
                "audioLanguagesObserved": languages,
            })
        if not clients:
            continue
        scopes = sorted({
            scope for scope in (active_manifest_scopes or [])
            if scope in {
                "manifest.json", "vf/manifest.json",
                "no-anime/manifest.json", "vf-no-anime/manifest.json",
            }
        })
        states = {x["observation"] for x in clients}
        return {
            "authority": "historical-user-report-only",
            "reportedOn": reported,
            "provider": wanted,
            "fixtureKnown": False,
            "executedJsKnown": False,
            "installedManifestKnown": False,
            "appBuildKnown": False,
            "activeManifestScopesAtCheckout": scopes,
            "clients": clients,
            "crossClientVisibilityDiscrepancy": (
                "stream-played" in states and "not-in-stream-list" in states
            ),
            "nextDiagnosticStages": [
                "installed_manifest_and_scraper_enabled",
                "media_type_and_client_selection",
                "native_getstreams_invocation",
                "network_and_terminal_media",
                "stream_ui_render_and_audio",
            ],
            "proofAuthority": False,
            "publicationAuthority": False,
            "mutationAuthority": False,
        }
    return {}


_RETEST_IDENTITY_REASONS = frozenset({
    "insufficient_identity_metadata", "duration_incomplete_hls",
    "duration_unavailable", "fixture_duration_mismatch",
    "provider_tmdb_route_mismatch", "wrong_season_episode", "wrong_episode",
    "forbidden_title_alias", "media_filename_title_mismatch",
    "strong_title_mismatch", "expected_title_alias", "season_episode_match",
    "episode_match", "provider_tmdb_direct_route",
})


def _provider_retest_observation(
    payload: Any,
    census: Any,
    provider_id: str,
    *,
    current_bundle_sha256: str = "",
) -> dict[str, Any]:
    """Bind sanitized Retest failure reasons to exact current JS and census run.

    A GitHub workflow success or one playable URL never grants a provider
    correctness, identity or client-playback assertion. Historical receipts
    and wrong-source-row data fail closed.
    """
    if not isinstance(payload, dict) or not isinstance(census, dict):
        return {}
    current_digest = str(current_bundle_sha256 or "").strip().casefold()
    if not re.fullmatch(r"[a-f0-9]{64}", current_digest):
        return {}
    source_run = str(payload.get("sourceCensusRunId") or "")
    source_sha = str(payload.get("sourceNiakvioSha") or "")
    if (
        payload.get("schemaVersion") != 1
        or payload.get("authority") != "current-retest-observation-only"
        or payload.get("proofAuthority") is not False
        or payload.get("publicationAuthority") is not False
        or not source_run.endswith("-retest")
        or source_run != str(census.get("runId") or "")
        or not re.fullmatch(r"[a-f0-9]{40}", source_sha)
        or source_sha != str(census.get("triggerSha") or "")
    ):
        return {}
    wanted = _canon(provider_id)
    current = next(
        (row for row in census.get("providers") or []
         if isinstance(row, dict) and _canon(row.get("provider")) == wanted), {}
    )
    if current.get("testedThisRun") is not True or current.get("status") == "DISABLED":
        return {}
    for row in (payload.get("rows") or [])[:8]:
        if not isinstance(row, dict) or _canon(row.get("provider")) != wanted:
            continue
        if (
            str(row.get("providerArtifactSha256") or "").strip().casefold()
            != current_digest
            or row.get("proofAuthority") is not False
            or row.get("publicationAuthority") is not False
            or row.get("nativePlaybackAuthority") is not False
        ):
            continue
        fixture = row.get("fixture") if isinstance(row.get("fixture"), dict) else {}
        def bounded(value: Any) -> int:
            return min(10000, max(0, value)) if type(value) is int else 0
        lane = str(row.get("lane") or "")
        status = str(row.get("status") or "")
        stage = str(row.get("debugStage") or "")
        if lane not in {"movie", "tv", "anime"}:
            lane = ""
        return {
            "source": "same-js-current-retest",
            "lane": lane,
            "status": status[:48] if re.fullmatch(r"[a-z_]+", status) else "",
            "debugStage": stage[:64] if re.fullmatch(r"[a-z_]+", stage) else "",
            "fixture": {
                "mediaType": lane,
                "tmdbId": str(fixture.get("tmdbId") or "")[:12] if str(fixture.get("tmdbId") or "").isdigit() else "",
                "season": bounded(fixture.get("season")),
                "episode": bounded(fixture.get("episode")),
            },
            "raw": bounded(row.get("raw")),
            "playable": bounded(row.get("playable")),
            "verified": bounded(row.get("verified")),
            "identityReasons": [
                v for v in (row.get("identityReasons") or [])[:12]
                if isinstance(v, str) and v in _RETEST_IDENTITY_REASONS
            ],
            "proofAuthority": False,
            "publicationAuthority": False,
            "nativePlaybackAuthority": False,
        }
    return {}


_CAUSAL_DIAGNOSTIC_LAYERS = frozenset({
    "unknown", "core", "client", "runtime", "network", "provider",
    "pipeline", "harness", "environment", "brain",
})
_CAUSAL_DIAGNOSTIC_STATUSES = frozenset({
    "completed", "abstained", "model_error", "route_only",
})


def _provider_causal_diagnostic_priors(
    payload: Any, provider_id: str, *, current_bundle_sha256: str = ""
) -> list[dict[str, Any]]:
    """Re-use past model diagnoses only for the same exact JS bytes.

    The guidance branch is historical and no hypothesis upgrades client
    playback, provider mutation, publisher authority or current facts.
    Free-text LLM output and private data are never ingested from this lane.
    """
    if (
        not isinstance(payload, dict)
        or payload.get("schemaVersion") != 1
        or payload.get("authority") != "brain-source-pinned-causal-hypotheses-only"
        or any(payload.get(key) is not False for key in (
            "proofAuthority", "publicationAuthority",
            "providerMutationAuthority", "nativePlaybackAuthority",
            "privateContentRetained",
        ))
    ):
        return []
    wanted = _canon(provider_id).replace(" ", "-")
    current_digest = str(current_bundle_sha256 or "").strip().casefold()
    if not re.fullmatch(r"[a-f0-9]{64}", current_digest):
        return []
    accepted: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in (payload.get("rows") or [])[:1400]:
        if not isinstance(row, dict):
            continue
        strategy = str(row.get("strategy") or "")
        failure = str(row.get("failureClass") or "")
        model_status = str(row.get("modelStatus") or "")
        source_sha = str(row.get("sourceNiakvioSha") or "")
        brain_sha = str(row.get("brainLlmSha") or "")
        if (
            _canon(row.get("providerId")).replace(" ", "-") != wanted
            or str(row.get("providerArtifactSha256") or "") != current_digest
            or row.get("historicalOnly") is not True
            or any(row.get(key) is not False for key in (
                "proofAuthority", "publicationAuthority",
                "providerMutationAuthority", "nativePlaybackAuthority",
            ))
            or not re.fullmatch(r"[a-f0-9]{40}", source_sha)
            or not re.fullmatch(r"[a-f0-9]{40}", brain_sha)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}", strategy)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}", failure)
            or model_status not in _CAUSAL_DIAGNOSTIC_STATUSES
        ):
            continue
        key = (source_sha, strategy)
        if key in seen:
            continue
        seen.add(key)
        routing_layer = str(row.get("routingLayer") or "")
        hypothesis_layer = str(row.get("hypothesisLayer") or "")
        accepted.append({
            "source": "same-js-historical-brain-causal-hypothesis",
            "strategy": strategy,
            "failureClass": failure,
            "routingLayer": (
                routing_layer if routing_layer in _CAUSAL_DIAGNOSTIC_LAYERS else "unknown"
            ),
            "hypothesisLayer": (
                hypothesis_layer if hypothesis_layer in _CAUSAL_DIAGNOSTIC_LAYERS else "unknown"
            ),
            "modelStatus": model_status,
            "historicalOnly": True,
            "proofAuthority": False,
            "publicationAuthority": False,
            "providerMutationAuthority": False,
            "nativePlaybackAuthority": False,
        })
        if len(accepted) >= 4:
            break
    return accepted


def _provider_retest_history_observations(
    payload: Any,
    provider_id: str,
    *,
    current_bundle_sha256: str = "",
    current_census_run_id: str = "",
) -> list[dict[str, Any]]:
    """Retain old failures on unchanged JS, explicitly historical and non-authoritative.

    Source SHA/census freshness is intentionally NOT promoted by this lane.
    Only exact current-bundle-byte matches are usable as negative hypotheses.
    """
    if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
        return []
    if (
        payload.get("authority") != "historical-exact-bundle-diagnostics-only"
        or payload.get("proofAuthority") is not False
        or payload.get("publicationAuthority") is not False
    ):
        return []
    digest = str(current_bundle_sha256 or "").strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        return []
    wanted = _canon(provider_id)
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in (payload.get("rows") or [])[:1400]:
        if not isinstance(row, dict):
            continue
        run = str(row.get("sourceCensusRunId") or "")
        sha = str(row.get("sourceNiakvioSha") or "")
        if (
            _canon(row.get("provider")) != wanted
            or str(row.get("providerArtifactSha256") or "").strip().casefold() != digest
            or run == current_census_run_id
            or not re.fullmatch(r"\d+-retest", run)
            or not re.fullmatch(r"[0-9a-f]{40}", sha)
            or row.get("proofAuthority") is not False
            or row.get("publicationAuthority") is not False
            or row.get("nativePlaybackAuthority") is not False
            or run in seen
        ):
            continue
        seen.add(run)
        def bounded(value: Any) -> int:
            return min(10000, max(0, value)) if type(value) is int else 0
        lane = str(row.get("lane") or "")
        if lane not in {"movie", "tv", "anime"}:
            continue
        output.append({
            "source": "historical-exact-js-retest",
            "sourceCensusRunId": run,
            "lane": lane,
            "playable": bounded(row.get("playable")),
            "verified": bounded(row.get("verified")),
            "identityReasons": [
                value for value in (row.get("identityReasons") or [])[:12]
                if isinstance(value, str) and value in _RETEST_IDENTITY_REASONS
            ],
            "historicalOnly": True,
            "proofAuthority": False,
            "publicationAuthority": False,
            "nativePlaybackAuthority": False,
        })
        if len(output) >= 4:
            break
    return output


_ANDROID_TV_STATES = frozenset({
    "ready", "playing", "error", "short_media", "buffering", "unknown",
    "ended", "timeout", "not_reached", "paused",
})
_ANDROID_TV_ERRORS = frozenset({
    "none", "reference_error", "type_error", "syntax_error", "timeout",
    "network_error", "http_error", "unspecified_js_exception",
})


def _provider_android_tv_emulator_observations(
    payload: Any, provider_id: str, *,
    current_bundle_sha256: str = "",
    active_manifest_scopes: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Use historical exact-JS official TV traces as a diagnostic oracle only.

    The emulator's historical source commit is not the current Brain source.
    Byte equality permits comparing failures, NEVER declaring current playback
    valid or granting provider mutation authority. Client patch ownership is
    determined separately from the provider's extraction path.
    """
    if not isinstance(payload, dict) or (
        payload.get("schemaVersion") != 1
        or payload.get("authority") != "official-android-tv-emulator-diagnostic-only"
        or payload.get("primaryClient") != "tv"
        or any(payload.get(key) is not False for key in (
            "proofAuthority", "publicationAuthority", "nativePlaybackAuthority",
            "providerMutationAuthority",
        ))
    ):
        return []
    digest = str(current_bundle_sha256 or "").strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        return []
    allowed_scopes = set(active_manifest_scopes or [])
    results: list[dict[str, Any]] = []
    wanted = _canon(provider_id).replace("_", "-")
    for row in (payload.get("rows") or [])[:1400]:
        if not isinstance(row, dict):
            continue
        if (
            _canon(row.get("provider")).replace("_", "-") != wanted
            or row.get("providerArtifactSha256") != digest
            or row.get("manifestScope") not in allowed_scopes
            or not re.fullmatch(r"[0-9a-f]{40}", str(row.get("sourceNiakvioSha") or ""))
            or not str(row.get("nativeRunId") or "").isdigit()
            or any(row.get(key) is not False for key in (
                "proofAuthority", "publicationAuthority", "nativePlaybackAuthority",
                "providerMutationAuthority",
            ))
        ):
            continue
        lane = str(row.get("requestType") or "")
        fixture = str(row.get("fixture") or "")
        if lane not in {"movie", "tv", "anime"} or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,95}", fixture):
            continue
        errors = [
            x for x in (row.get("quickJsErrors") or [])[:8]
            if isinstance(x, str) and x in _ANDROID_TV_ERRORS and x != "none"
        ]
        states = [
            x for x in (row.get("playerStates") or [])[:8]
            if isinstance(x, str) and x in _ANDROID_TV_STATES
        ]
        phases = [
            x for x in (row.get("quickJsPhases") or [])[:4]
            if isinstance(x, str) and x in {"call", "result", "error", "missing_export"}
        ]
        result = {
            "source": "official-android-tv-emulator",
            "client": "tv",
            "fixture": fixture,
            "requestType": lane,
            "sourceRunId": str(row["nativeRunId"]),
            # Exact official NuvioTV commit, separate from the NiakVIO JS SHA
            # and from an unverified user-installed APK version. Old receipts
            # without this field stay historical and are never backfilled.
            "officialClientSha": (
                str(row.get("officialClientSha") or "").lower()
                if re.fullmatch(r"[0-9a-f]{40}", str(row.get("officialClientSha") or "").lower())
                else ""
            ),
            "manifestScope": row["manifestScope"],
            "appSelected": row.get("appSelected") if type(row.get("appSelected")) is bool else None,
            "quickJsPhases": phases,
            "quickJsErrors": errors,
            "tvPromiseControl": str(row.get("tvPromiseControl") or "")
                if row.get("tvPromiseControl") in {
                    "bridge_ok", "promise_delivery_gap", "baseline_failed",
                } else "not_observed",
            "quickJsReturned": min(10000, max(0, row.get("quickJsReturned")))
                if type(row.get("quickJsReturned")) is int else 0,
            "nativeHardTimeoutObserved": row.get("nativeHardTimeoutObserved") is True,
            # This clock is imposed by NiakVIO's generated Future.get
            # harness, NOT by official NuvioTV PluginManager. It cannot
            # prove a provider code defect or a client playback failure.
            "nativeHardTimeoutOrigin": (
                "niakvio-test-harness" if row.get("nativeHardTimeoutObserved") is True
                else "not-observed"
            ),
            "nativeHardTimeoutMs": min(180000, max(0, row.get("nativeHardTimeoutMs")))
                if row.get("nativeHardTimeoutObserved") is True
                and type(row.get("nativeHardTimeoutMs")) is int else 0,
            "nativeExtractionZeroObserved": row.get("nativeExtractionZeroObserved") is True,
            "nativeExtractionPositiveObserved": row.get("nativeExtractionPositiveObserved") is True,
            "nativeExtractionReturnedCount": min(10000, max(0, row.get("nativeExtractionReturnedCount")))
                if type(row.get("nativeExtractionReturnedCount")) is int else 0,
            # Sanitized pre-player signature from NiakVIO's official TV log:
            # the exact same HLS root succeeded once, then returned 403 on a
            # later Core/runtime probe. No URL, host, token or header survives.
            "sameMediaRootSuccessThenForbidden": row.get("sameMediaRootSuccessThenForbidden") is True,
            "playerVideoFormatUnverified": row.get("playerVideoFormatUnverified") is True,
            # Independent network check is NOT the official player network's
            # HTTP status; this permits causal header/WAF investigation only.
            "independentTerminalHttpStatuses": sorted({
                v for v in (row.get("independentTerminalHttpStatuses") or [])[:8]
                if type(v) is int and 400 <= v <= 599
            }),
            "playerStates": states,
            "readerEvidenceComplete": row.get("readerEvidenceComplete") is True,
            "historicalOnly": True,
            "proofAuthority": False,
            "publicationAuthority": False,
            "nativePlaybackAuthority": False,
            "providerMutationAuthority": False,
        }
        results.append(result)
        if len(results) >= 4:
            break
    return results


def _provider_waf_observation(
    payload: Any, provider_id: str, *, current_bundle_sha256: str = ""
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    wanted = _canon(provider_id)
    rows = [
        row for row in payload.get("rows") or []
        if isinstance(row, dict) and _canon(row.get("provider")) == wanted
    ]
    replay_rows = [
        row for row in ((payload.get("residentialProviderReplay") or {}).get("rows") or [])
        if isinstance(row, dict) and _canon(row.get("provider")) == wanted
    ]
    # Browser/WAF probes remain transport observations across generations.
    # Full residential *provider* replay can drive Brain mutation causality only
    # when its exact executed JS bytes match this request's published bundle.
    current_digest = str(current_bundle_sha256 or "").strip().casefold()
    # No verified current bundle hash means NO executable residential replay
    # authority. Never accidentally promote an unpinned historical record.
    if re.fullmatch(r"[0-9a-f]{64}", current_digest) is None:
        replay_rows = []
    else:
        replay_rows = [
            row for row in replay_rows
            if str(row.get("providerArtifactSha256") or "").strip().casefold() == current_digest
        ]
    if not rows and not replay_rows:
        return {}
    return {
        "residentialReplayCurrentBundle": bool(current_digest and replay_rows),
        "browserOutcomes": sorted({
            str(row.get("outcome") or "") for row in rows if str(row.get("outcome") or "")
        }),
        "residentialOutcomes": sorted({
            str((row.get("residentialExitNodeProfile") or {}).get("outcome") or "")
            for row in rows
            if str((row.get("residentialExitNodeProfile") or {}).get("outcome") or "")
        }),
        "contentProfiles": sorted({
            str(profile)
            for row in rows
            for profile in (row.get("contentProfiles") or [])
            if str(profile)
        }),
        "nativeTvTransportStillUnproven": any(
            row.get("nativeTvTransportStillUnproven") is True for row in rows
        ),
        "residentialReplay": [
            {
                "lane": str(row.get("lane") or "")[:40],
                "status": str(row.get("status") or "")[:80],
                "debugStage": str(row.get("debugStage") or "")[:120],
                "sampleDebugStages": [
                    str(value or "")[:120]
                    for value in (row.get("sampleDebugStages") or [])[:16]
                    if str(value or "")
                ],
                "sampleStatuses": [
                    str(value or "")[:80]
                    for value in (row.get("sampleStatuses") or [])[:16]
                    if str(value or "")
                ],
                "raw": int(row.get("raw") or 0),
                "playable": int(row.get("playable") or 0),
                "verified": int(row.get("verified") or 0),
                "contradictions": int(row.get("contradictions") or 0),
                "identitySafe": row.get("identitySafe") is True,
            }
            for row in replay_rows[:8]
        ],
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

CURRENT_REPAIR_PROVIDER_FAILURES = {
    "provider-transport-gap",
    "route-proven-gap",
    "chain-terminal-gap",
    "media-extraction-gap",
}


def _targeted_provider_execution_current(observation: Any) -> bool:
    """Require current provider-owned successful HTTP evidence, never TMDB-only traffic."""
    if not isinstance(observation, dict):
        return False
    network = observation.get("network")
    if not isinstance(network, dict):
        return False
    for rows in network.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            host = str(row.get("host") or "").strip().casefold()
            if not host or host in {"api.themoviedb.org", "www.themoviedb.org"}:
                continue
            try:
                status = int(row.get("status") or 0)
            except (TypeError, ValueError):
                continue
            if 200 <= status < 400:
                return True
    return False


def _provider_current_repair_execution(
    payload: Any,
    memory_payload: Any,
    provider_id: str,
    *,
    census_run_id: str,
    current_artifact_sha256: str = "",
    current_targeted_observation: Any = None,
) -> dict[str, Any]:
    """Reuse executed sandbox progress without confusing it with positive proof.

    Same-census progress is reusable directly. Cross-census progress is reusable
    only when the exact current published provider SHA256 equals the parent bytes
    of the attempt that produced diagnostic progress and the new census has fresh
    provider-owned successful network evidence.
    """
    if not isinstance(payload, dict) or not isinstance(memory_payload, dict):
        return {}
    source_run = str(payload.get("sourceCensusRunId") or "")
    if not census_run_id or not source_run:
        return {}
    wanted = _canon(provider_id)
    selected = {
        _canon(value)
        for value in payload.get("selectedProviders") or []
        if str(value or "").strip()
    }
    if wanted not in selected:
        return {}

    plan: dict[str, Any] = {}
    diagnostics: list[dict[str, Any]] = []
    for wave in payload.get("waves") or []:
        if not isinstance(wave, dict):
            continue
        for batch in wave.get("batches") or []:
            if not isinstance(batch, dict):
                continue
            brain = batch.get("brain") if isinstance(batch.get("brain"), dict) else {}
            plans = brain.get("plans") if isinstance(brain.get("plans"), dict) else {}
            for key, value in plans.items():
                key_provider = str(key or "").split(":", 1)[-1]
                if _canon(key_provider) == wanted and isinstance(value, dict):
                    plan = value
            diagnostics.extend(
                value
                for value in (brain.get("attemptDiagnostics") or [])
                if isinstance(value, dict) and _canon(value.get("provider")) == wanted
            )

    raw_failure = str(plan.get("failureClass") or "").strip()
    failure_key = "-".join(_canon(raw_failure).split())
    if failure_key not in CURRENT_REPAIR_PROVIDER_FAILURES:
        return {}
    progress = [
        row for row in diagnostics
        if str(row.get("phase") or "").strip().casefold() == "exploration_progress"
        and str(row.get("reasonCode") or "").strip().casefold() == "sandbox_diagnostic_progress"
    ]
    if not progress:
        return {}

    same_census = source_run == census_run_id
    reuse_authority = "same-census"
    current_sha = str(current_artifact_sha256 or "").strip().casefold()
    if not same_census:
        progress_repairs = {
            str(row.get("repairSha256") or "").strip().casefold()
            for row in progress
            if len(str(row.get("repairSha256") or "").strip()) == 64
        }
        progress_parents = {
            str(row.get("parentSha256") or "").strip().casefold()
            for row in diagnostics
            if str(row.get("phase") or "").strip().casefold() == "attempts"
            and str(row.get("status") or "").strip().casefold() == "generated"
            and str(row.get("repairSha256") or "").strip().casefold() in progress_repairs
            and len(str(row.get("parentSha256") or "").strip()) == 64
        }
        if (
            len(current_sha) != 64
            or not all(ch.isdigit() or ch in "abcdef" for ch in current_sha)
            or current_sha not in progress_parents
            or not _targeted_provider_execution_current(current_targeted_observation)
        ):
            return {}
        reuse_authority = "exact-byte-current-evidence"

    # Execution memory can legitimately carry the taxonomy that existed when
    # the sandbox first entered exploration (for example search_gap), while the
    # same Repair transaction later refines its current plan to
    # media_extraction_gap. Do not require those labels to be byte-identical:
    # bind the memory to this provider's explicit sandbox progress instead.
    safe_progress_memory_failures = CURRENT_REPAIR_PROVIDER_FAILURES | {"search-gap"}
    memory_rows = []
    for value in memory_payload.get("entries") or []:
        if not isinstance(value, dict) or _canon(value.get("providerId")) != wanted:
            continue
        memory_failure = "-".join(_canon(value.get("failureClass")).split())
        if memory_failure not in safe_progress_memory_failures:
            continue
        if value.get("executionObserved") is not True:
            continue
        if str(value.get("lastOutcome") or "").strip().casefold() != "exploration_progress_nonpublishable":
            continue
        last_reason = str(value.get("lastReason") or "").strip().casefold()
        if not last_reason.startswith("sandbox_diagnostic_progress:"):
            continue
        memory_rows.append(value)
    if not memory_rows:
        return {}

    # observedPipelineStage can lag the actual frontier (the real sandbox may
    # record "episode" while lastReason records provider-frontier:player).
    # Recover only a small allowlist of explicit persisted frontier tokens.
    stage_tokens = {
        "search", "lookup", "detail", "episode", "watch",
        "player", "embed", "source", "api", "terminal",
    }
    stages = {
        str(value.get("observedPipelineStage") or "").strip().casefold()[:40]
        for value in memory_rows
        if str(value.get("observedPipelineStage") or "").strip()
    }
    for value in memory_rows:
        last_reason = str(value.get("lastReason") or "").strip().casefold()
        marker = "provider-frontier:"
        if marker not in last_reason:
            continue
        suffix = last_reason.split(marker, 1)[1]
        for token in suffix.split(","):
            token = token.strip()
            if token in stage_tokens:
                stages.add(token)
    stages = sorted(stages)
    generated = sum(
        1 for row in diagnostics
        if str(row.get("phase") or "").strip().casefold() == "attempts"
        and str(row.get("status") or "").strip().casefold() == "generated"
    )
    return {
        "role": "current-fast-repair-sandbox-observation",
        "sourceCensusRunId": source_run,
        "currentCensusRunId": census_run_id,
        "reuseAuthority": reuse_authority,
        **({"providerArtifactSha256": current_sha} if current_sha else {}),
        "failureClass": raw_failure[:120],
        "executionObserved": True,
        "explorationProgress": True,
        "observedPipelineStages": stages[:8],
        "generatedAttemptCount": min(generated, 32),
        "proofAuthority": False,
        "publicationAuthority": False,
    }


def _provider_negative_memory(payload: Any, provider_id: str) -> list[dict[str, Any]]:
    """Keep the provider's sanitized ledger intact for deterministic exclusions.

    The source ledger has NiakVIO's global retention bound. Prompt construction
    separately bounds the narrative history; truncating here makes the selector
    forget failed fingerprints before the publication guard checks them.
    """
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
            **(
                {"executionObserved": value.get("executionObserved") is True}
                if "executionObserved" in value else {}
            ),
        })
    return out

def _safe_execution_coverage(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    keys = {
        "streamsReturned", "streamsPlayable", "identityContradictions",
        "announcedPlayerCandidates", "announcedVariantCandidates",
        "exploredPlayerRequests", "reachableHostCount", "maxPlayableHeight",
        "qualityHeightCount",
    }
    return {
        key: max(-100000, min(100000, raw))
        for key, raw in value.items()
        if key in keys and isinstance(raw, int) and not isinstance(raw, bool)
    }


def _provider_force_negative_memory(payload: Any, provider_id: str) -> list[dict[str, Any]]:
    """Return safe rejected Force execution outcomes without mutation/source text."""
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
        failures = int(value.get("consecutiveFailures") or 0)
        successes = int(value.get("successes") or 0)
        if failures <= 0 and successes <= 0:
            continue
        out.append({
            "memoryRole": "force_sandbox_execution",
            "consecutiveFailures": failures,
            "failures": int(value.get("failures") or 0),
            "successes": successes,
            "lastOutcome": str(value.get("lastOutcome") or "")[:80],
            "lastReason": str(value.get("lastReason") or "")[:240],
            **{
                key: _safe_execution_coverage(value[key])
                for key in ("lastBaselineCoverage", "lastCandidateCoverage", "lastCoverageDelta")
                if _safe_execution_coverage(value.get(key))
            },
            "lastMutationSummary": [
                {
                    "scope": str(item.get("scope") or "")[:40],
                    "operation": str(item.get("operation") or "")[:40],
                    **({"family": str(item.get("family") or "")[:80]} if str(item.get("family") or "") else {}),
                    **({"path": str(item.get("path") or "")[:160]} if str(item.get("path") or "") else {}),
                }
                for item in (value.get("lastMutationSummary") or [])[:8]
                if isinstance(item, dict) and str(item.get("scope") or "")
            ],
            "mutationFingerprint": str(value.get("mutationFingerprint") or "")[:64],
            "mutationContextFingerprint": str(value.get("mutationContextFingerprint") or "")[:64],
            "lastCurrentSha": str(value.get("lastCurrentSha") or "")[:40],
            "sourceNiakvioSha": str(value.get("sourceNiakvioSha") or "")[:40],
            "sourceBrainLlmSha": str(value.get("sourceBrainLlmSha") or "")[:40],
            # An unverified old ledger is a prior, never proof that a child
            # was executed/materialized. These fields have identical semantics
            # in the generator, adapter, publisher and current-byte sandbox.
            "executionObserved": (
                value.get("executionObserved") is True
                and _canon(value.get("lastOutcome")) not in
                {"profile unavailable", "not generated", "accepted", "verified", "success"}
            ),
            "materializedMutationObserved": value.get("materializedMutationObserved") is True,
        })

    # Keep every execution key for deterministic replay exclusions, newest
    # verdict first. Prompts independently select only recent narrative rows.
    # De-duplicate keys so the newest verdict supersedes any older outcome.
    recent: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in reversed(out):
        key = (
            str(row.get("mutationFingerprint") or "").casefold(),
            str(row.get("mutationContextFingerprint") or "").casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        recent.append(row)
    return recent

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

def _route_synthesis_policy(
    status: object,
    failure_class: object,
    route_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    """Describe whether runtime synthesis may trust, extend or must rediscover routes.

    Current census status is the authority. Structured route DATA is an input to
    traversal/runtime synthesis, never permission to invent a route when current
    proof is absent.
    """
    status_key = _canon(status).replace("_", " ")
    failure_key = _canon(failure_class).replace("_", " ")
    contract = dict(route_contract or {})
    proven = 0
    for key in ("provenRouteCount", "runtimePlanRouteCount"):
        try:
            proven = max(proven, int(contract.get(key) or 0))
        except (TypeError, ValueError):
            pass
    live = contract.get("liveEvidence")
    if isinstance(live, dict):
        try:
            proven = max(proven, int(live.get("validatedRoutes") or 0))
        except (TypeError, ValueError):
            pass

    if status_key == "no proof":
        return {
            "mode": "rediscover_by_traversal",
            "runtimeSynthesisAllowed": False,
            "routeAuthority": "current_census_no_proof",
            "next": [
                "provider_authority_or_hub",
                "search_or_lookup",
                "detail",
                "season_episode_if_needed",
                "player_or_embed",
                "terminal_media",
            ],
        }
    if status_key == "route proven":
        return {
            "mode": "reuse_proven_route_then_advance_chain",
            "runtimeSynthesisAllowed": True,
            "routeAuthority": "current_route_proof",
            "forbidBlindSearchRediscovery": True,
            "provenRouteCount": proven,
        }
    if status_key == "chain reached":
        return {
            "mode": "continue_proven_chain_to_terminal",
            "runtimeSynthesisAllowed": True,
            "routeAuthority": "current_chain_proof",
            "forbidBlindSearchRediscovery": True,
            "provenRouteCount": proven,
        }
    if status_key == "candidate ok":
        return {
            "mode": "replay_current_candidate_before_new_route",
            "runtimeSynthesisAllowed": True,
            "routeAuthority": "current_candidate_proof",
            "forbidBlindSearchRediscovery": True,
            "provenRouteCount": proven,
        }
    if "transport" in failure_key and proven <= 0:
        return {
            "mode": "rediscover_by_traversal",
            "runtimeSynthesisAllowed": False,
            "routeAuthority": "no_current_route_proof",
            "next": [
                "provider_authority_or_hub",
                "search_or_lookup",
                "detail",
                "player_or_embed",
                "terminal_media",
            ],
        }
    return {
        "mode": "use_current_route_authority",
        "runtimeSynthesisAllowed": True,
        "routeAuthority": "current_provider_data",
        "provenRouteCount": proven,
    }


def request_from_checkout(root: str | Path, provider_id: str) -> RepairRequest:
    """Build one bounded LLM request from a read-only NiakVIO checkout."""
    root = Path(root)
    wanted = _canon(provider_id)

    census = _load(root / "automation" / "provider-census-status.json", {})
    census_run = str(census.get("runId") or "") if isinstance(census, dict) else ""
    census_sharded = (
        _load(root / "automation" / f"provider-census-sharded-{census_run}.json", {})
        if census_run.isdigit()
        else {}
    )
    experience = _load(root / "automation" / "brain-repair-experience.json", {})
    memory = _load(root / "automation" / "brain-repair-memory.json", {})
    force_memory = _load(root / "automation" / "brain-llm-force-memory.json", {})
    current_repair = _load(root / "automation" / "provider-brain-repair-latest.json", {})
    targeted = _load(root / "automation" / "provider-targeted-regression-recovery-latest.json", {})
    waf = _load(root / "automation" / "provider-waf-browser-session-latest.json", {})
    retest = _load(root / "automation" / "provider-retest-brain-evidence-latest.json", {})
    retest_history = _load(root / "automation" / "provider-retest-brain-evidence-history.json", {})
    causal_memory = _load(root / "automation" / "brain-causal-diagnostics-history.json", {})
    user_client_reports = _load(root / "automation" / "user-client-provider-field-observations.json", {})
    android_tv_emulator = _load(root / "automation" / "brain-android-tv-emulator-history.json", {})
    refined = _load(root / "automation" / "provider-repair-batch-refined-latest.json", {})
    current_structure_payload = _load(
        root / "automation" / "provider-current-structure-evidence.json",
        {},
    )

    row: dict[str, Any] = {}
    for candidate in census.get("providers") or []:
        if isinstance(candidate, dict) and _canon(candidate.get("provider")) == wanted:
            row = candidate
            break

    provider_context = build_provider_context(root, provider_id)
    failure = classify_census_failure(row)
    coverage = (
        provider_context.get("runtime_variant_coverage")
        if isinstance(provider_context.get("runtime_variant_coverage"), dict)
        else {}
    )
    status_key = _canon(row.get("status")).replace("_", " ")
    if coverage.get("risk") == "high" and status_key in {"full ok", "partial ok"}:
        failure = "variant_coverage_gap"

    provider_experience: list[Any] = []
    if isinstance(experience, dict):
        for key in ("providers", "providerExperience", "experiences"):
            block = experience.get(key)
            if isinstance(block, dict):
                value = block.get(provider_id) or block.get(wanted)
                if value:
                    provider_experience.append(value)

    negative_memory = _provider_negative_memory(memory, provider_id)
    force_negative_memory = _provider_force_negative_memory(force_memory, provider_id)

    targeted_source_run = str(targeted.get("sourceCensusRunId") or "") if isinstance(targeted, dict) else ""
    targeted_current = (
        not targeted_source_run
        or not census_run
        or targeted_source_run == census_run
    )
    targeted_observation = (
        _provider_targeted_observation(targeted, provider_id)
        if targeted_current
        else {}
    )
    published_bundle = (
        provider_context.get("published_bundle")
        if isinstance(provider_context.get("published_bundle"), dict)
        else {}
    )
    current_repair_observation = _provider_current_repair_execution(
        current_repair,
        memory,
        provider_id,
        census_run_id=census_run,
        current_artifact_sha256=str(published_bundle.get("sha256") or ""),
        current_targeted_observation=targeted_observation,
    )
    if current_repair_observation and status_key not in {"full ok", "partial ok", "candidate ok"}:
        failure = str(current_repair_observation.get("failureClass") or failure)

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

    census_sharded_observation = _provider_sharded_observation(census_sharded, provider_id)
    dynamic_variant_gap = _dynamic_variant_coverage_gap(census_sharded_observation)
    if dynamic_variant_gap and status_key in {"full ok", "partial ok", "candidate ok"}:
        failure = "variant_coverage_gap"
    current_structure_observation = _provider_current_structure_evidence(
        current_structure_payload,
        provider_id,
    )
    active_manifest_scopes = []
    for candidate_path in (
        "manifest.json", "vf/manifest.json",
        "no-anime/manifest.json", "vf-no-anime/manifest.json",
    ):
        document = _load(root / candidate_path, {})
        if any(
            isinstance(item, dict)
            and _canon(item.get("id")) == wanted
            and item.get("enabled") is True
            for item in (document.get("scrapers") or [])
        ):
            active_manifest_scopes.append(candidate_path)
    user_client_observation = _provider_user_client_field_observation(
        user_client_reports, provider_id,
        active_manifest_scopes=active_manifest_scopes,
    )
    retest_observation = _provider_retest_observation(
        retest, census, provider_id,
        current_bundle_sha256=str(published_bundle.get("sha256") or row.get("providerArtifactSha256") or ""),
    )
    retest_history_observations = _provider_retest_history_observations(
        retest_history, provider_id,
        current_bundle_sha256=str(published_bundle.get("sha256") or row.get("providerArtifactSha256") or ""),
        current_census_run_id=census_run,
    )
    causal_diagnostic_priors = _provider_causal_diagnostic_priors(
        causal_memory, provider_id,
        current_bundle_sha256=str(published_bundle.get("sha256") or ""),
    )
    android_tv_observations = _provider_android_tv_emulator_observations(
        android_tv_emulator, provider_id,
        current_bundle_sha256=str(published_bundle.get("sha256") or ""),
        active_manifest_scopes=active_manifest_scopes,
    )
    waf_observation = _provider_waf_observation(
        waf, provider_id,
        current_bundle_sha256=str(published_bundle.get("sha256") or row.get("providerArtifactSha256") or ""),
    )
    targeted_stages = {
        str(value or "").strip().casefold()
        for value in (targeted_observation.get("debugStages") or {}).values()
        if str(value or "").strip()
    }
    targeted_network = [
        item
        for rows in (targeted_observation.get("network") or {}).values()
        if isinstance(rows, list)
        for item in rows
        if isinstance(item, dict)
    ]
    provider_origin_network = [
        item
        for item in targeted_network
        if str(item.get("host") or "").strip().casefold() not in {
            "api.themoviedb.org",
            "www.themoviedb.org",
        }
    ]
    targeted_explicit_waf = "provider_waf_challenge" in targeted_stages
    targeted_provider_waf = (
        bool(provider_origin_network)
        and (
            targeted_explicit_waf
            or (
                all(int(item.get("status") or 0) in {401, 403, 429} for item in provider_origin_network)
                and (
                    targeted_stages <= {"provider_waf_challenge", "provider_network_http_error"}
                    or not targeted_stages
                )
            )
        )
        and not targeted_observation.get("playableLanes")
        and not targeted_observation.get("verifiedLanes")
    )
    content_profiles = set(waf_observation.get("contentProfiles") or [])
    browser_outcomes = set(waf_observation.get("browserOutcomes") or [])
    residential_outcomes = set(waf_observation.get("residentialOutcomes") or [])
    browser_content_reached = (
        "browser_content_reached" in browser_outcomes
        or "browser_content_reached" in residential_outcomes
    )
    native_like_content_reached = bool(
        content_profiles & {"nuvio-tv-ua-browser", "nuvio-tv-direct-http-approx", "nuvio-tv-okhttp-jvm"}
    )
    replay_rows = [
        row for row in (waf_observation.get("residentialReplay") or [])
        if isinstance(row, dict)
    ]
    replay_provider_signal = bool(replay_rows) and all(
        row.get("identitySafe") is True
        and int(row.get("contradictions") or 0) == 0
        and not (
            {
                str(row.get("debugStage") or "").strip().casefold(),
                *{
                    str(value or "").strip().casefold()
                    for value in row.get("sampleDebugStages") or []
                    if str(value or "").strip()
                },
            }
            & {"provider_waf_challenge", "provider_network_timeout", "timeout"}
        )
        and str(row.get("status") or "").strip().casefold() != "timeout"
        and "timeout" not in {
            str(value or "").strip().casefold()
            for value in row.get("sampleStatuses") or []
            if str(value or "").strip()
        }
        for row in replay_rows
    )
    persistent_waf = bool(browser_outcomes) and bool(residential_outcomes) and all(
        "challenge_persisted" in outcome
        for outcome in (browser_outcomes | residential_outcomes)
        if outcome
    )

    if targeted_provider_waf and replay_provider_signal:
        # Full provider replay through the residential exit outranks a narrow
        # WAF seed. If the actual provider runtime still reaches a clean
        # identity-safe zero/error after residential routing, keep the normal
        # provider failure class so Brain can repair it.
        pass
    elif targeted_provider_waf and persistent_waf:
        failure = "transport_environment_gap"
    elif targeted_provider_waf and browser_content_reached and native_like_content_reached:
        # The seed URL is reachable with audited Nuvio-like transport, but no
        # full provider replay has yet isolated a provider-local failure.
        failure = "client_transport_gap"
    elif targeted_explicit_waf:
        # A current provider probe has already classified an actual provider
        # request as an interactive challenge. HTTP 200 does not make that a
        # provider-code defect; keep it outside mutation until stronger replay
        # evidence proves a provider-local failure.
        failure = "provider_transport_gap"

    refined_groups = _provider_refined_groups(
        refined,
        provider_id,
        census_run_id=str(census.get("runId") or ""),
    )

    census_prior = {
        "sourceCensusRunId": census_run,
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
        "testedThisRun": row.get("testedThisRun") is True,
        "residentialProviderReplayClass": row.get("residentialProviderReplayClass"),
        "residentialProviderReplayEvidence": row.get("residentialProviderReplayEvidence") or [],
        "harnessTransportClass": row.get("harnessTransportClass"),
        "harnessTransportEvidence": row.get("harnessTransportEvidence") or [],
    }

    route_contract = (
        dict(provider_context.get("route_contract"))
        if isinstance(provider_context.get("route_contract"), dict)
        else {}
    )
    route_contract["synthesisPolicy"] = _route_synthesis_policy(
        row.get("status"),
        failure,
        route_contract,
    )
    if current_structure_observation:
        current_routes = [
            str(value.get("path") or "")
            for value in current_structure_observation.get("routes") or []
            if isinstance(value, dict) and str(value.get("path") or "").startswith("/")
        ][:12]
        if current_routes:
            route_contract["currentObservedRoutes"] = current_routes
            route_contract["currentObservedRoutesAuthority"] = "observation-only"
        provider_context["current_structure_evidence"] = current_structure_observation
    provider_context["route_contract"] = route_contract
    provider_context["advisor_experiment_history"] = [
        *negative_memory,
        # FORCE ingestion returns newest first, whereas prompt history keeps
        # a recent suffix. Store chronological order consistently here.
        *reversed(force_negative_memory),
    ]
    references = build_validated_reference_patterns(
        root,
        provider_id,
        str(failure),
        census,
        target_context=provider_context,
        limit=3,
    )
    if references:
        provider_context["validated_reference_patterns"] = references

    return RepairRequest(
        provider_id=provider_id,
        failure_class=str(failure),
        status=str(row.get("status") or ""),
        supported_types=[str(x) for x in supported][:8],
        census_prior=census_prior,
        observations=[
            {"source": "census_current", "value": census_prior},
            *(
                [{"source": "official-android-tv-emulator", "value": item}
                 for item in android_tv_observations]
            ),
            *(
                [{"source": "user-client-field-report", "value": user_client_observation}]
                if user_client_observation else []
            ),
            *(
                [{"source": "historical-provider-retest-media", "value": item}
                 for item in retest_history_observations]
            ),
            *(
                [{"source": "historical-brain-causal-diagnosis", "value": item}
                 for item in causal_diagnostic_priors]
            ),
            *(
                [{"source": "current-provider-retest-media", "value": retest_observation}]
                if retest_observation else []
            ),
            *(
                [{"source": "fast-repair-current", "value": current_repair_observation}]
                if current_repair_observation else []
            ),
            *(
                [{"source": "runtime-variant-coverage-current", "value": coverage}]
                if coverage else []
            ),
            *(
                [{"source": "targeted-regression-current", "value": targeted_observation}]
                if targeted_observation else []
            ),
            *(
                [{"source": "census-sharded-current", "value": census_sharded_observation}]
                if census_sharded_observation else []
            ),
            *(
                [{"source": "current-provider-structure", "value": current_structure_observation}]
                if current_structure_observation else []
            ),
            *(
                [{"source": "waf-client-differential-current", "value": waf_observation}]
                if waf_observation else []
            ),
            *(
                [{"source": "refined-repair-batch-current", "value": refined_groups}]
                if refined_groups else []
            ),
            {"source": "brain-repair-experience", "value": provider_experience[:4]},
            {"source": "brain-repair-memory", "value": list(reversed(negative_memory[-4:]))},
            *(
                [{"source": "brain-force-sandbox-memory", "value": force_negative_memory}]
                if force_negative_memory else []
            ),
        ],
        provider_context=provider_context,
    )
