from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

OPAQUE = re.compile(r"[A-Za-z0-9+/]{160,}={0,2}")
FIXDATA_COMMENT = re.compile(r"/\*\s*FIXDATA:.*?\*/", re.IGNORECASE | re.DOTALL)
URL = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
HOST = re.compile(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", re.IGNORECASE)
ROUTE_LITERAL = re.compile(r"([\"'])/(?![/*])[^\"'\n]{1,180}\1")
TECHNICAL_TOKENS = (
    "fetch", "headers", "cookie", "user-agent", "referer", "origin", "redirect",
    "timeout", "search", "detail", "episode", "watch", "player", "iframe", "embed",
    "confirm", "internal", "resolve", "m3u8", "mp4", "playlist", "json", "regex",
    "base64", "decrypt", "decode", "session", "token", "source",
)
FAMILY_REFERENCE_TOKENS = {
    "provider_transport_gap": {"fetch", "headers", "cookie", "user-agent", "referer", "origin", "redirect", "timeout", "session"},
    "route_proven_gap": {"search", "detail", "episode", "watch", "player", "iframe", "embed", "fetch", "resolve"},
    "chain_terminal_gap": {"confirm", "internal", "player", "iframe", "resolve", "m3u8", "mp4", "playlist", "source"},
}

def _clip(text: str, limit: int) -> str:
    value = text.strip()
    return value if len(value) <= limit else value[:limit] + "\n/* clipped */"

def sanitize_source(text: str, *, limit: int = 5000) -> str:
    text = FIXDATA_COMMENT.sub("/* FIXDATA blob omitted */", text)
    text = OPAQUE.sub("<opaque-token-omitted>", text)
    return _clip(text, limit)

def sanitize_exact_source(text: str) -> str:
    """Sanitize public provider source without changing its structural bytes."""
    text = FIXDATA_COMMENT.sub("/* FIXDATA blob omitted */", text)
    return OPAQUE.sub("<opaque-token-omitted>", text)

def _technical_features(text: str) -> set[str]:
    lowered = str(text or "").casefold()
    return {token for token in TECHNICAL_TOKENS if token in lowered}

def _sanitize_reference_source(text: str, provider_id: str, *, limit: int = 1400) -> str:
    """Keep transferable code shape while removing provider addressing/content."""
    value = sanitize_source(str(text or ""), limit=9000)
    value = URL.sub("<URL>", value)
    value = HOST.sub("<HOST>", value)
    value = ROUTE_LITERAL.sub(lambda m: m.group(1) + "<ROUTE>" + m.group(1), value)
    if provider_id:
        value = re.sub(re.escape(provider_id), "<PROVIDER>", value, flags=re.IGNORECASE)
    value = re.sub(r"PROVIDER\.[A-Z0-9_.-]+", "PROVIDER.<REFERENCE>", value, flags=re.IGNORECASE)
    return _clip(value, limit)

def _reference_snippet(source: str, failure_class: str, provider_id: str) -> str:
    cleaned = _sanitize_reference_source(source, provider_id, limit=5000)
    if len(cleaned) <= 1400:
        return cleaned
    tokens = list(FAMILY_REFERENCE_TOKENS.get(str(failure_class or "").strip().casefold(), set()))
    lowered = cleaned.casefold()
    positions = [lowered.find(token) for token in tokens if lowered.find(token) >= 0]
    center = min(positions) if positions else len(cleaned) // 2
    start = max(0, center - 450)
    end = min(len(cleaned), start + 1400)
    return cleaned[start:end]

def build_validated_reference_patterns(
    root: str | Path,
    target_provider_id: str,
    failure_class: str,
    census: dict[str, Any],
    *,
    target_context: dict[str, Any] | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return optional code references from current FULL OK providers."""
    root = Path(root)
    rows = census.get("providers") if isinstance(census, dict) else None
    if not isinstance(rows, list):
        return []
    target_id = str(target_provider_id or "").strip().casefold()
    target_context = target_context or build_provider_context(root, target_provider_id)
    target_sources: list[str] = []
    registered = target_context.get("registered_patch_sources")
    if isinstance(registered, dict):
        target_sources.extend(str(v) for v in registered.values())
    runtime = target_context.get("runtimeMutationSource")
    if runtime:
        target_sources.append(str(runtime))
    target_features = _technical_features("\n".join(target_sources))
    family_features = FAMILY_REFERENCE_TOKENS.get(
        str(failure_class or "").strip().casefold(),
        set(),
    )

    candidates: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        provider = str(row.get("provider") or "").strip()
        if not provider or provider.casefold() == target_id:
            continue
        status = str(row.get("status") or "").strip().casefold().replace("_", " ")
        if "full ok" not in status:
            continue
        context = build_provider_context(root, provider)
        sources: list[tuple[str, str]] = []
        peer_registered = context.get("registered_patch_sources")
        if isinstance(peer_registered, dict):
            for path, source in peer_registered.items():
                sources.append(("registered_bloc:" + str(path), str(source)))
        published = context.get("published_bundle")
        if isinstance(published, dict):
            for block in published.get("providerBlocks") or []:
                if isinstance(block, dict) and block.get("source"):
                    sources.append(("published_bloc:" + str(block.get("id") or ""), str(block.get("source"))))
        if not sources and context.get("authored_module"):
            sources.append(("authored_module", str(context.get("authored_module"))))
        for source_kind, source in sources[:4]:
            features = _technical_features(source)
            if not features:
                continue
            target_overlap = (
                len(features & target_features) / max(1, len(features | target_features))
                if target_features else 0.0
            )
            family_overlap = (
                len(features & family_features) / max(1, len(family_features))
                if family_features else 0.0
            )
            score = (0.65 * family_overlap) + (0.35 * target_overlap)
            if score <= 0:
                continue
            snippet = _reference_snippet(source, failure_class, provider)
            if not snippet:
                continue
            candidates.append((score, {
                "provider": provider,
                "status": "FULL OK",
                "source_kind": source_kind[:220],
                "technical_features": sorted(features)[:16],
                "snippet": snippet,
                "proof_authority": False,
                "copy_policy": "pattern_reference_only",
                "novelty_allowed": True,
            }))
    candidates.sort(key=lambda item: item[0], reverse=True)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for _, row in candidates:
        key = (str(row["provider"]), str(row["source_kind"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= max(0, min(int(limit), 3)):
            break
    return out

def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

def _safe_route(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        try:
            parts = urlsplit(raw)
            raw = parts.path or "/"
            if parts.query:
                # Keep query keys/placeholders but never full URL authority or fragments.
                raw += "?" + parts.query
        except ValueError:
            return ""
    if not raw.startswith("/"):
        return ""
    raw = re.sub(r"(?i)(authorization|cookie|token|secret|password|api[_-]?key)=([^&]+)", r"\1=<redacted>", raw)
    return raw[:260]


def _compact_route_contract(value: Any) -> dict[str, Any]:
    """Extract a small, structured route contract for runtime synthesis.

    The full provider override remains authoritative in NiakVIO. This projection
    exists only so the local Brain does not need to rediscover already-proven
    route structure from clipped JSON or large runtime source windows.
    """
    if not isinstance(value, dict):
        return {}

    out: dict[str, Any] = {}
    capability = str(value.get("capability") or "").strip()
    if capability:
        out["capability"] = capability[:80]
    route_state = str(value.get("route_data_state") or "").strip()
    if route_state:
        out["routeDataState"] = route_state[:40]

    def collect_routes(key: str, limit: int) -> list[str]:
        rows = value.get(key)
        if not isinstance(rows, list):
            return []
        result: list[str] = []
        for item in rows:
            route = _safe_route(item)
            if route and route not in result:
                result.append(route)
            if len(result) >= limit:
                break
        return result

    learned = collect_routes("learned_routes", 6)
    candidates = collect_routes("candidate_learned_routes", 8)
    if learned:
        out["learnedRoutes"] = learned
    if candidates:
        out["candidateRoutes"] = candidates

    plans: list[dict[str, Any]] = []
    for plan_key in ("search_request_plan", "provider_value_plan", "external_identity_plan"):
        rows = value.get(plan_key)
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            continue
        for raw in rows[:4]:
            if not isinstance(raw, dict):
                continue
            route = _safe_route(raw.get("route") or raw.get("path") or raw.get("endpoint"))
            spec = raw.get("requestSpec") if isinstance(raw.get("requestSpec"), dict) else {}
            method = str(raw.get("method") or spec.get("method") or "").strip().upper()
            role = str(raw.get("sourceRole") or raw.get("role") or "").strip()
            lanes = raw.get("semanticTypes") or raw.get("lanes") or []
            headers = spec.get("headers") if isinstance(spec.get("headers"), dict) else {}
            row: dict[str, Any] = {"kind": plan_key}
            if route:
                row["route"] = route
            if method:
                row["method"] = method[:12]
            if role:
                row["role"] = role[:80]
            if isinstance(lanes, list):
                safe_lanes = [str(x)[:20] for x in lanes[:4] if str(x).strip()]
                if safe_lanes:
                    row["lanes"] = safe_lanes
            if headers:
                safe_header_names = [
                    str(name)[:40]
                    for name in headers
                    if str(name).strip().casefold() not in {"authorization", "cookie", "set-cookie"}
                ][:8]
                if safe_header_names:
                    row["headerNames"] = safe_header_names
            if len(row) > 1:
                plans.append(row)
            if len(plans) >= 6:
                break
        if len(plans) >= 6:
            break
    if plans:
        out["plans"] = plans

    proof = value.get("route_proof")
    if isinstance(proof, dict):
        prefs = proof.get("canonicalExecutionPreference")
        compact_prefs: list[dict[str, Any]] = []
        if isinstance(prefs, list):
            for raw in prefs[:4]:
                if not isinstance(raw, dict):
                    continue
                row: dict[str, Any] = {}
                owner = str(raw.get("owner") or "").strip()
                route = _safe_route(raw.get("route"))
                lanes = raw.get("lanes") or []
                if owner:
                    row["owner"] = owner[:40]
                if route:
                    row["route"] = route
                if isinstance(lanes, list):
                    safe_lanes = [str(x)[:20] for x in lanes[:4] if str(x).strip()]
                    if safe_lanes:
                        row["lanes"] = safe_lanes
                if row:
                    compact_prefs.append(row)
        if compact_prefs:
            out["canonicalPreference"] = compact_prefs
        for source_key, target_key in (
            ("provenRouteCount", "provenRouteCount"),
            ("runtimePlanRouteCount", "runtimePlanRouteCount"),
        ):
            try:
                out[target_key] = max(0, int(proof.get(source_key) or 0))
            except (TypeError, ValueError):
                pass

    gate = value.get("live_route_gate")
    if isinstance(gate, dict):
        live: dict[str, Any] = {}
        for source_key, target_key in (
            ("provider_request_count", "providerRequests"),
            ("live_validated_route_count", "validatedRoutes"),
            ("runtime_derived_route_count", "runtimeDerivedRoutes"),
        ):
            try:
                live[target_key] = max(0, int(gate.get(source_key) or 0))
            except (TypeError, ValueError):
                pass
        state = str(gate.get("completion_state") or "").strip()
        if state:
            live["state"] = state[:60]
        if live:
            out["liveEvidence"] = live

    return out


def _provider_entry(data: Any, provider_id: str) -> Any:
    wanted = provider_id.strip().casefold()
    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).strip().casefold() == wanted:
                return value
        for container_key in ("providers", "overrides", "provider_patches", "hubs", "entries"):
            nested = data.get(container_key)
            if isinstance(nested, dict):
                for key, value in nested.items():
                    if str(key).strip().casefold() == wanted:
                        return value
            if isinstance(nested, list):
                for value in nested:
                    if not isinstance(value, dict):
                        continue
                    candidate = value.get("provider") or value.get("providerId") or value.get("id")
                    if str(candidate or "").strip().casefold() == wanted:
                        return value
    return None

def _published_provider_context(root: Path, provider_id: str) -> dict[str, Any] | None:
    manifest = _load_json(root / "manifest.json")
    rows = manifest.get("scrapers") if isinstance(manifest, dict) else None
    if not isinstance(rows, list):
        return None
    wanted = provider_id.strip().casefold()
    row = next(
        (
            value
            for value in rows
            if isinstance(value, dict)
            and str(value.get("id") or "").strip().casefold() == wanted
        ),
        None,
    )
    if not isinstance(row, dict):
        return None
    filename = str(row.get("filename") or "").strip()
    if not filename.startswith(("providers/", "provider-disabled/")):
        return None
    path = root / filename
    if not path.is_file():
        return None
    source = path.read_text(encoding="utf-8", errors="replace")
    runtime_mutation_source = ""
    provider_begin = "/* BEGIN NIAKVIO_PROVIDER */"
    provider_end = "/* END NIAKVIO_PROVIDER */"
    if source.count(provider_begin) == 1 and source.count(provider_end) == 1:
        begin_index = source.index(provider_begin)
        provider_end_index = source.index(provider_end, begin_index)
        first_core = source.find("/* STARTFIX:CORE.", begin_index, provider_end_index)
        runtime_limit = first_core if first_core >= 0 else provider_end_index
        runtime_mutation_source = sanitize_exact_source(
            source[begin_index:runtime_limit]
        )
    canonical = re.escape(provider_id.upper()).replace(r"\-", "[-_]")
    pattern = re.compile(
        rf"/\* STARTFIX:(PROVIDER\.{canonical}\.[A-Z0-9_.-]+) \*/"
        rf"(.*?)"
        rf"/\* CLOSEFIX:\1 \*/",
        re.IGNORECASE | re.DOTALL,
    )
    blocks: list[dict[str, str]] = []
    block_sources: dict[str, str] = {}
    for match in pattern.finditer(source):
        block_id = str(match.group(1) or "").upper()
        body = match.group(0)
        block_sources[block_id] = sanitize_exact_source(body)
        # Preserve both the beginning and the terminal resolver/export tail of
        # large runtime Blocs; either side can contain the actual failure cause.
        cleaned = sanitize_source(body, limit=9000)
        if len(body.strip()) > 9000:
            head = sanitize_source(body[:6500], limit=6600)
            tail = sanitize_source(body[-2200:], limit=2300)
            cleaned = head + "\n/* published Bloc middle clipped */\n" + tail
        blocks.append({"id": block_id, "source": cleaned})
        if len(blocks) >= 4:
            break
    return {
        "filename": filename,
        "version": str(row.get("version") or ""),
        "supportedTypes": list(row.get("supportedTypes") or []),
        "formats": list(row.get("formats") or []),
        "providerBlocks": blocks,
        "providerBlockSources": block_sources,
        "runtimeMutationFilename": filename,
        "runtimeMutationSource": runtime_mutation_source,
    }


def build_provider_context(root: str | Path, provider_id: str) -> dict[str, Any]:
    root = Path(root)
    context: dict[str, Any] = {
        "source_repo": "niakw/NiakVIO",
        "read_only": True,
        "provider_id": provider_id,
    }

    published = _published_provider_context(root, provider_id)
    if published is not None:
        context["published_bundle"] = {
            key: value
            for key, value in published.items()
            if key not in {"runtimeMutationFilename", "runtimeMutationSource", "providerBlockSources"}
        }
        if published.get("runtimeMutationSource"):
            context["runtimeMutationFilename"] = published.get("runtimeMutationFilename")
            context["runtimeMutationSource"] = published.get("runtimeMutationSource")

    authored = root / "engine_v2" / "providers" / f"{provider_id}.mjs"
    if authored.exists():
        context["authored_module"] = sanitize_source(
            authored.read_text(encoding="utf-8", errors="replace"),
            limit=5000,
        )

    override_value: Any = None
    for name, relative in (
        ("override", "provider-overrides.json"),
        ("hub", "provider-hubs.json"),
    ):
        value = _provider_entry(_load_json(root / relative), provider_id)
        if value is not None:
            if name == "override":
                override_value = value
            encoded = json.dumps(value, ensure_ascii=True, sort_keys=True)
            context[name] = sanitize_source(encoded, limit=2200)
            if name == "override":
                route_contract = _compact_route_contract(value)
                if route_contract:
                    context["route_contract"] = route_contract

    # Provider-local Blocs are the real authored mutation surface for current
    # NiakVIO providers. Existing scripts remain exact edit targets. A separate
    # bounded provider_bloc contract may synthesize a new managed Bloc from the
    # current provider-owned runtime source; it never grants arbitrary file paths.
    if isinstance(override_value, dict):
        scripts = [
            str(value).strip()
            for value in [
                *(override_value.get("patch_scripts") or []),
                *(override_value.get("provider_lego_scripts") or []),
            ]
            if str(value).strip().startswith("scripts/provider_patches/")
        ][:8]
        scripts = list(dict.fromkeys(scripts))
        if scripts:
            context["registered_patch_scripts"] = scripts
            sources: dict[str, str] = {}
            source_sha256: dict[str, str] = {}
            for relative in scripts[:4]:
                path = root / relative
                if path.is_file():
                    # Keep the exact sanitized Bloc internally. Prompting owns
                    # context clipping; compact Force find/replace validation must
                    # compare against real source rather than a synthetic clipped
                    # surrogate.
                    sources[relative] = sanitize_exact_source(
                        path.read_text(encoding="utf-8", errors="replace")
                    )
                    source_sha256[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            if sources:
                context["registered_patch_sources"] = sources
                context["registered_patch_sha256"] = source_sha256
                managed_ids: list[str] = []
                for source_text in sources.values():
                    managed_ids.extend(
                        str(match.group(1) or "").upper()
                        for match in re.finditer(
                            r"MANAGED_FIX_ID\s*=\s*[\"'](PROVIDER\.[A-Za-z0-9_.-]+)[\"']",
                            source_text,
                        )
                    )
                exact_blocks = (
                    published.get("providerBlockSources")
                    if isinstance(published, dict)
                    and isinstance(published.get("providerBlockSources"), dict)
                    else {}
                )
                preferred_ids = sorted(
                    set(managed_ids),
                    key=lambda value: (0 if ".RUNTIME." in value else 1, value),
                )
                preferred_id = next(
                    (value for value in preferred_ids if value in exact_blocks),
                    "",
                )
                if preferred_id:
                    context["preferredRuntimeMutationBlockId"] = preferred_id
                    context["preferredRuntimeMutationSource"] = exact_blocks[preferred_id]

    return context
