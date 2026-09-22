from __future__ import annotations

from typing import Any

from .contracts import RepairRequest

def _clip(value: Any, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + "...<clipped>"

def _compact(value: Any, *, depth: int = 0) -> Any:
    if depth >= 4:
        return _clip(value, 500)
    if isinstance(value, dict):
        return {
            str(key)[:80]: _compact(item, depth=depth + 1)
            for key, item in list(value.items())[:24]
        }
    if isinstance(value, list):
        return [_compact(item, depth=depth + 1) for item in value[:12]]
    if isinstance(value, str):
        return _clip(value, 900)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _clip(value, 500)

def compact_request(request: RepairRequest) -> dict[str, Any]:
    data = request.to_dict()
    context = dict(data.get("provider_context") or {})
    if "authored_module" in context:
        context["authored_module"] = _clip(context["authored_module"], 5000)
    if "override" in context:
        context["override"] = _clip(context["override"], 1800)
    if "hub" in context:
        context["hub"] = _clip(context["hub"], 1400)
    data["provider_context"] = context
    data["observations"] = [_compact(item) for item in data.get("observations", [])[:8]]
    data["census_prior"] = _compact(data.get("census_prior") or {})
    return data

def compact_experience(row: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "experience_id",
        "providers",
        "failure_class",
        "symptom_families",
        "signals",
        "strategy",
        "avoid",
        "lesson",
        "_retrieval_score",
        "_structural_score",
    )
    return {key: _compact(row.get(key)) for key in keep if key in row}

def compact_document(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": _clip(row.get("path"), 180),
        "heading": _clip(row.get("heading"), 220),
        "role": _clip(row.get("role"), 100),
        "authority": row.get("authority"),
        "text": _clip(row.get("text"), 1500),
        "_document_score": row.get("_document_score"),
    }

def build_prompt_payload(
    request: RepairRequest,
    experiences: list[dict[str, Any]],
    documents: list[dict[str, Any]] | None = None,
    causal_prior: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "request": compact_request(request),
        "causal_prior": _compact(causal_prior or {}),
        "retrieved_experiences": [
            compact_experience(row) for row in experiences[:4]
        ],
        "retrieved_documents": [
            compact_document(row) for row in (documents or [])[:4]
        ],
    }
