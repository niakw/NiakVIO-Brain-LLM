from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

DATA_OPERATIONS = {"set", "delete", "append"}
JS_OPERATIONS = {"unified_diff"}
PATCH_OPERATIONS = {"unified_diff"}

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
PLACEHOLDER_MARKERS = (
    "api.example",
    "example.com",
    ".example/",
    "changeme",
    "replace_me",
    "placeholder",
    "diff_to_",
    "<current",
    "<replace",
    "todo:",
)

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

def _string_values(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _string_values(item)

def _reject_placeholders(value: Any) -> None:
    for text in _string_values(value):
        lowered = text.casefold()
        if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
            raise ValueError("mutation contains placeholder or synthetic value")

def _require_http_url(value: Any) -> None:
    if not isinstance(value, str):
        raise ValueError("URL mutation value must be a string")
    parsed = urlparse(value)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"} or not host or "." not in host:
        raise ValueError("URL mutation value must be a concrete http(s) URL")
    if host.endswith(".example") or host in {"example.com", "localhost"}:
        raise ValueError("URL mutation value cannot use a placeholder host")

def validate_mutation(
    provider_id: str,
    mutation: dict[str, Any],
    *,
    allowed_patch_paths: set[str] | None = None,
) -> None:
    scope = str(mutation.get("scope") or "")
    operation = str(mutation.get("operation") or "")

    if scope == "provider_data":
        if operation not in DATA_OPERATIONS:
            raise ValueError(f"unsupported provider_data operation: {operation}")
        path = str(mutation.get("path") or "")
        parts = _data_parts(path)
        if not parts:
            raise ValueError(
                "provider_data path must be a safe path relative to provider_patches[provider_id]"
            )

        if operation in {"set", "append"}:
            if "value" not in mutation:
                raise ValueError("provider_data set/append requires a value")
            value = mutation.get("value")
            _reject_placeholders(value)
            if path in {
                "official_hub",
                "official_site",
                "candidate_api_recipe.base",
                "api_recipe.base",
            }:
                _require_http_url(value)
        return

    if scope == "provider_patch":
        if operation not in PATCH_OPERATIONS:
            raise ValueError(f"unsupported provider_patch operation: {operation}")
        path = str(mutation.get("path") or "")
        allowed = set(allowed_patch_paths or set())
        if not path.startswith("scripts/provider_patches/") or path not in allowed:
            raise ValueError("provider_patch must target an already-registered provider Bloc")
        diff = str(mutation.get("diff") or "")
        if not diff or len(diff) > 24000:
            raise ValueError("missing or oversized provider_patch diff")
        _reject_placeholders(diff)
        if not ("--- " in diff and "+++ " in diff and "@@" in diff):
            raise ValueError("provider_patch mutation must contain a concrete unified diff")
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
        _reject_placeholders(diff)
        if not ("--- " in diff and "+++ " in diff and "@@" in diff):
            raise ValueError("provider_js mutation must contain a concrete unified diff")
        return

    raise ValueError(f"unsupported mutation scope: {scope}")

def validate_mutations(
    provider_id: str,
    mutations: list[dict[str, Any]],
    *,
    allowed_patch_paths: set[str] | None = None,
) -> None:
    for mutation in mutations:
        validate_mutation(
            provider_id,
            mutation,
            allowed_patch_paths=allowed_patch_paths,
        )
