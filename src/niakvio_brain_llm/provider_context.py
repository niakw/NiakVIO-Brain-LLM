from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

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
            if sources:
                context["registered_patch_sources"] = sources
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
