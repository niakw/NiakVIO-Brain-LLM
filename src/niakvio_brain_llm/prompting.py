from __future__ import annotations

from typing import Any

from .contracts import RepairRequest

def _clip(value: Any, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + "...<clipped>"

def _compact(value: Any, *, depth: int = 0, string_limit: int = 500) -> Any:
    if depth >= 4:
        return _clip(value, min(string_limit, 350))
    if isinstance(value, dict):
        return {
            str(key)[:80]: _compact(
                item,
                depth=depth + 1,
                string_limit=string_limit,
            )
            for key, item in list(value.items())[:20]
        }
    if isinstance(value, list):
        return [
            _compact(item, depth=depth + 1, string_limit=string_limit)
            for item in value[:10]
        ]
    if isinstance(value, str):
        return _clip(value, string_limit)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _clip(value, string_limit)

def compact_request(
    request: RepairRequest,
    *,
    high_confidence: bool,
    mutation_allowed: bool,
) -> dict[str, Any]:
    data = request.to_dict()
    context = dict(data.get("provider_context") or {})

    if "authored_module" in context:
        source_limit = 3200 if mutation_allowed else (2200 if not high_confidence else 1200)
        context["authored_module"] = _clip(context["authored_module"], source_limit)
    if "override" in context:
        context["override"] = _clip(
            context["override"],
            1200 if mutation_allowed else 700,
        )
    if "hub" in context:
        context["hub"] = _clip(context["hub"], 700)

    data["provider_context"] = context
    observation_limit = 500 if high_confidence else 650
    observation_count = 5 if high_confidence else 7
    data["observations"] = [
        _compact(item, string_limit=observation_limit)
        for item in data.get("observations", [])[:observation_count]
    ]
    data["census_prior"] = _compact(
        data.get("census_prior") or {},
        string_limit=450 if high_confidence else 600,
    )
    return data

def compact_experience(
    row: dict[str, Any],
    *,
    text_limit: int,
) -> dict[str, Any]:
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
    return {
        key: _compact(row.get(key), string_limit=text_limit)
        for key in keep
        if key in row
    }

def compact_document(
    row: dict[str, Any],
    *,
    text_limit: int,
) -> dict[str, Any]:
    return {
        "path": _clip(row.get("path"), 160),
        "heading": _clip(row.get("heading"), 180),
        "role": _clip(row.get("role"), 80),
        "authority": row.get("authority"),
        "text": _clip(row.get("text"), text_limit),
        "_document_score": row.get("_document_score"),
    }

def build_prompt_payload(
    request: RepairRequest,
    experiences: list[dict[str, Any]],
    documents: list[dict[str, Any]] | None = None,
    causal_prior: dict[str, Any] | None = None,
    mutation_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prior = causal_prior or {}
    policy = mutation_policy or {}
    # Verification tests are deterministic Brain policy. Do not spend LLM
    # context on re-sending a protocol the model is not allowed to weaken.
    model_policy = {
        key: value
        for key, value in policy.items()
        if key != "required_tests"
    }
    high_confidence = float(prior.get("confidence") or 0.0) >= 0.90
    mutation_allowed = bool(policy.get("allow_mutations"))

    experience_limit = 2 if high_confidence else 4
    document_limit = 1 if high_confidence else 2
    experience_text_limit = 420 if high_confidence else 600
    document_text_limit = 650 if high_confidence else 900

    return {
        "request": compact_request(
            request,
            high_confidence=high_confidence,
            mutation_allowed=mutation_allowed,
        ),
        "causal_prior": _compact(prior, string_limit=500),
        "mutation_policy": _compact(model_policy, string_limit=500),
        "verification_owned_by_brain": True,
        "retrieved_experiences": [
            compact_experience(row, text_limit=experience_text_limit)
            for row in experiences[:experience_limit]
        ],
        "retrieved_documents": [
            compact_document(row, text_limit=document_text_limit)
            for row in (documents or [])[:document_limit]
        ],
        "context_budget": {
            "mode": "focused" if high_confidence else "exploratory",
            "experience_limit": experience_limit,
            "document_limit": document_limit,
        },
    }
