from __future__ import annotations

from typing import Any

DATA_OPERATIONS = {"set", "delete", "append"}
JS_OPERATIONS = {"unified_diff"}

def _safe_data_path(path: str) -> bool:
    if not path or len(path) > 240:
        return False
    forbidden = {"__proto__", "prototype", "constructor"}
    parts = [part for part in path.replace("[", ".").replace("]", "").split(".") if part]
    return bool(parts) and not any(part.casefold() in forbidden for part in parts)

def validate_mutation(provider_id: str, mutation: dict[str, Any]) -> None:
    scope = str(mutation.get("scope") or "")
    operation = str(mutation.get("operation") or "")

    if scope == "provider_data":
        if operation not in DATA_OPERATIONS:
            raise ValueError(f"unsupported provider_data operation: {operation}")
        path = str(mutation.get("path") or "")
        if not _safe_data_path(path):
            raise ValueError("unsafe or missing provider_data path")
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
