from __future__ import annotations

import re
from typing import Any

DATA_OPERATIONS = {"set", "delete", "append"}
JS_OPERATIONS = {"unified_diff"}

# provider_data paths are always relative to:
# provider-overrides.json -> provider_patches[provider_id]
ALLOWED_DATA_ROOTS = {
    "capability",
    "official_hub",
    "official_site",
    "manifest_overrides",
    "domain_substitutions",
    "published_types",
    "identity_input",
    "learned_routes",
    "candidate_learned_routes",
    "provider_lego_scripts",
    "provider_lego_options",
    "candidate_api_recipe",
    "api_recipe",
    "route_data_state",
    "runtime_domain_replacements",
    "preserve_embed_urls",
    "notes",
}

PATH_PART = re.compile(r"^[A-Za-z0-9_-]+$")

def _data_parts(path: str) -> list[str]:
    if not path or len(path) > 240:
        return []
    if "/" in path or "\\" in path or ".." in path:
        return []
    parts = [part for part in path.replace("[", ".").replace("]", "").split(".") if part]
    if not parts:
        return []
    forbidden = {"__proto__", "prototype", "constructor"}
    if any(part.casefold() in forbidden or not PATH_PART.match(part) for part in parts):
        return []
    if parts[0] not in ALLOWED_DATA_ROOTS:
        return []
    return parts

def validate_mutation(provider_id: str, mutation: dict[str, Any]) -> None:
    scope = str(mutation.get("scope") or "")
    operation = str(mutation.get("operation") or "")

    if scope == "provider_data":
        if operation not in DATA_OPERATIONS:
            raise ValueError(f"unsupported provider_data operation: {operation}")
        path = str(mutation.get("path") or "")
        if not _data_parts(path):
            raise ValueError(
                "provider_data path must be a safe path relative to provider_patches[provider_id]"
            )
        return

    if scope == "provider_js":
        if operation not in JS_OPERATIONS:
            raise ValueError(f"unsupported provider_js operation: {operation}")
        path = str(mutation.get("path") or "")
        allowed = f"engine_v2/providers/{provider_id}.mjs"
        if path != allowed:
            raise ValueError("provider_js patch must target the provider-authored module only")
        diff = str(mutation.get("diff") or "")
        if not diff or len(diff) > 24000:
            raise ValueError("missing or oversized provider_js diff")
        return

    raise ValueError(f"unsupported mutation scope: {scope}")

def validate_mutations(provider_id: str, mutations: list[dict[str, Any]]) -> None:
    for mutation in mutations:
        validate_mutation(provider_id, mutation)
