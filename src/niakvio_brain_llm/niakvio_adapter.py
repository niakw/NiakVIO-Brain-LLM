from __future__ import annotations

import json
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
        if isinstance(raw, int):
            out[key] = max(0, min(raw, 65536 if key == "sampleBytes" else 99))
    for key, limit in (("classTokens", 16), ("idTokens", 12)):
        rows = value.get(key)
        if isinstance(rows, list):
            safe = [
                str(item)[:48]
                for item in rows[:limit]
                if str(item)
                and str(item)[0].isalpha()
                and all(ch.isalnum() or ch in "_-" for ch in str(item))
                and 2 <= len(str(item)) <= 48
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
            token = str(row.get("token") or "")[:48]
            if not (
                token
                and token[0].isalpha()
                and all(ch.isalnum() or ch in "_-" for ch in token)
                and 2 <= len(token) <= 48
            ):
                continue
            tags = [
                str(tag)[:16].lower()
                for tag in (row.get("tags") or [])[:4]
                if str(tag)
                and str(tag)[0].isalpha()
                and all(ch.isalnum() or ch in "_-" for ch in str(tag))
            ]
            safe_facts.append({
                "token": token,
                "count": max(0, min(int(row.get("count") or 0), 12)),
                "tags": tags,
                "selfHref": max(0, min(int(row.get("selfHref") or 0), 12)),
                "nestedAnchors": max(0, min(int(row.get("nestedAnchors") or 0), 24)),
                "signals": [
                    str(sig) for sig in (row.get("signals") or [])[:9]
                    if str(sig) in allowed_signals
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

    if not debug_stages and not statuses and not network:
        return {}
    return _provider_targeted_observation(
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

def _provider_waf_observation(payload: Any, provider_id: str) -> dict[str, Any]:
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
    if not rows and not replay_rows:
        return {}
    return {
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
            "executionObserved": True,
        })

    # Force memory is append-oriented. Current repair decisions must see the
    # newest executed negatives first: request_from_checkout deliberately puts
    # only a bounded prefix into observations. De-duplicate identical execution
    # keys while walking backwards so a repeated stale entry cannot crowd out
    # the latest provider_bloc verdict.
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
        if len(recent) >= 8:
            break
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
    targeted = _load(root / "automation" / "provider-targeted-regression-recovery-latest.json", {})
    waf = _load(root / "automation" / "provider-waf-browser-session-latest.json", {})
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
    force_negative_memory = _provider_force_negative_memory(force_memory, provider_id)

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
    census_sharded_observation = _provider_sharded_observation(census_sharded, provider_id)
    waf_observation = _provider_waf_observation(waf, provider_id)
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

    provider_context = build_provider_context(root, provider_id)
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
    provider_context["route_contract"] = route_contract
    provider_context["advisor_experiment_history"] = [
        *negative_memory,
        *force_negative_memory,
    ][-32:]
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
                [{"source": "targeted-regression-current", "value": targeted_observation}]
                if targeted_observation else []
            ),
            *(
                [{"source": "census-sharded-current", "value": census_sharded_observation}]
                if census_sharded_observation else []
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
            {"source": "brain-repair-memory", "value": negative_memory[:4]},
            *(
                [{"source": "brain-force-sandbox-memory", "value": force_negative_memory[:8]}]
                if force_negative_memory else []
            ),
        ],
        provider_context=provider_context,
    )
