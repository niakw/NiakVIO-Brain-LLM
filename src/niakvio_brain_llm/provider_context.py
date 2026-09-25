from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

OPAQUE = re.compile(r"[A-Za-z0-9+/]{160,}={0,2}")
FIXDATA_LINE = re.compile(r"^.*FIXDATA:.*$", re.MULTILINE)

def _clip(text: str, limit: int) -> str:
    value = text.strip()
    return value if len(value) <= limit else value[:limit] + "\n/* clipped */"

def sanitize_source(text: str, *, limit: int = 5000) -> str:
    text = FIXDATA_LINE.sub("/* FIXDATA blob omitted */", text)
    text = OPAQUE.sub("<opaque-token-omitted>", text)
    return _clip(text, limit)

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

def build_provider_context(root: str | Path, provider_id: str) -> dict[str, Any]:
    root = Path(root)
    context: dict[str, Any] = {
        "source_repo": "niakw/NiakVIO",
        "read_only": True,
        "provider_id": provider_id,
    }

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
    # NiakVIO providers. Expose only already-registered scripts; the model may
    # edit an existing Bloc but may never invent or target an unrelated file.
    if isinstance(override_value, dict):
        scripts = [
            str(value).strip()
            for value in (override_value.get("provider_lego_scripts") or [])
            if str(value).strip().startswith("scripts/provider_patches/")
        ][:8]
        scripts = list(dict.fromkeys(scripts))
        if scripts:
            context["registered_patch_scripts"] = scripts
            sources: dict[str, str] = {}
            for relative in scripts[:4]:
                path = root / relative
                if path.is_file():
                    sources[relative] = sanitize_source(
                        path.read_text(encoding="utf-8", errors="replace"),
                        limit=5000,
                    )
            if sources:
                context["registered_patch_sources"] = sources

    return context
