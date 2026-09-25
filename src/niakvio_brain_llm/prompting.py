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

    if "published_bundle" in context and isinstance(context["published_bundle"], dict):
        published = dict(context["published_bundle"])
        blocks = published.get("providerBlocks")
        if isinstance(blocks, list):
            published["providerBlocks"] = [
                {
                    "id": str(row.get("id") or "")[:180],
                    "source": _clip(str(row.get("source") or ""), 3400 if mutation_allowed else 2200),
                }
                for row in blocks[:2]
                if isinstance(row, dict)
            ]
        context["published_bundle"] = published
    if "registered_patch_sources" in context and isinstance(context["registered_patch_sources"], dict):
        sources = list(context["registered_patch_sources"].items())
        source_limit = 2200 if mutation_allowed else 1800
        max_sources = 2 if mutation_allowed else 1
        context["registered_patch_sources"] = {
            str(path)[:180]: _clip(source, source_limit)
            for path, source in sources[:max_sources]
        }
    if "authored_module" in context:
        # Force mutation planning should spend context on the registered provider
        # Bloc first. Keep only a small authored-module fallback for providers
        # whose registered Bloc does not expose the needed contract.
        source_limit = 1200 if mutation_allowed else (2200 if not high_confidence else 1200)
        context["authored_module"] = _clip(context["authored_module"], source_limit)
    if "override" in context:
        context["override"] = _clip(
            context["override"],
            900 if mutation_allowed else 700,
        )
    if "hub" in context:
        context["hub"] = _clip(context["hub"], 450 if mutation_allowed else 700)

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
        "source": _clip(row.get("source"), 80),
        "private_memory": bool(row.get("private_memory")),
        "proof_authority": bool(row.get("proof_authority")),
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

    if mutation_allowed:
        # Force is a code/data synthesis phase, not a research pass. Current
        # provider bytes + current failure evidence + one nearest experience are
        # enough; broad docs/private history only increase prefill latency and
        # were causing every 4-slot CPU request to time out.
        experience_limit = 1
        document_limit = 0
        experience_text_limit = 320
        document_text_limit = 0
    else:
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


def _head_tail(value: Any, head: int, tail: int) -> str:
    text = str(value or "").strip()
    if len(text) <= head + tail + 40:
        return text
    return text[:head] + "\n...<middle-clipped>...\n" + text[-tail:]


def build_force_prompt_payload(
    request: RepairRequest,
    causal_prior: dict[str, Any] | None = None,
    mutation_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Minimal provider-local context for CPU-bound Force synthesis.

    The Force model does not need RAG documents, historical prose, verification
    tests or the complete provider context. Deterministic NiakVIO already owns
    those. Give the model only current causal state plus the exact authored
    mutation surface it is allowed to edit.
    """
    prior = causal_prior or {}
    policy = mutation_policy or {}
    context = request.provider_context or {}

    registered = context.get("registered_patch_sources")
    target: dict[str, Any] = {}
    if isinstance(registered, dict) and registered:
        path, source = next(iter(registered.items()))
        target = {
            "scope": "provider_patch",
            "path": str(path)[:240],
            "source": _head_tail(source, 3600, 1200),
        }
    elif context.get("authored_module"):
        target = {
            "scope": "provider_js",
            "path": f"engine_v2/providers/{request.provider_id}.mjs",
            "source": _head_tail(context.get("authored_module"), 3600, 1200),
        }
    elif context.get("override"):
        target = {
            "scope": "provider_data",
            "path": "provider-overrides.json > provider_patches[provider_id]",
            "source": _clip(context.get("override"), 1800),
        }

    observations = [
        _compact(row, string_limit=260)
        for row in (request.observations or [])[:3]
    ]
    census = _compact(request.census_prior or {}, string_limit=320)
    allowed_scopes = list(policy.get("allowed_scopes") or request.allowed_mutations or [])

    return {
        "provider_id": request.provider_id,
        "failure_class": request.failure_class,
        "status": request.status,
        "supported_types": list(request.supported_types or [])[:4],
        "causal_prior": {
            "target_layer": prior.get("target_layer"),
            "confidence": prior.get("confidence"),
            "strategy_prior": prior.get("strategy_prior"),
        },
        "mutation_policy": {
            "allow_mutations": bool(policy.get("allow_mutations")),
            "allowed_scopes": allowed_scopes[:3],
            "force_abstain": bool(policy.get("force_abstain")),
            "reason": _clip(policy.get("reason"), 260),
        },
        "current_observations": observations,
        "census_prior": census,
        "mutation_target": target,
        "output_contract": {
            "max_mutations": 1,
            "provider_local_only": True,
            "unified_diff_against_exact_source": target.get("scope") in {"provider_patch", "provider_js"},
        },
    }
