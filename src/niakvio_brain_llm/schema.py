from __future__ import annotations

from copy import deepcopy
from typing import Any

DATA_ROOT_PATTERN = (
    r"^(capability|official_hub|official_site|manifest_overrides|domain_substitutions|"
    r"published_types|identity_input|learned_routes|candidate_learned_routes|"
    r"provider_lego_scripts|provider_lego_options|candidate_api_recipe|api_recipe|"
    r"route_data_state|runtime_domain_replacements|preserve_embed_urls|notes)"
    r"(\.[A-Za-z0-9_-]+)*$"
)

DATA_MUTATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["scope", "operation", "path"],
    "properties": {
        "scope": {"type": "string", "const": "provider_data"},
        "operation": {"type": "string", "enum": ["set", "delete", "append"]},
        "path": {"type": "string", "maxLength": 240, "pattern": DATA_ROOT_PATTERN},
        "value": {},
    },
}

JS_MUTATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["scope", "operation", "path", "diff"],
    "properties": {
        "scope": {"type": "string", "const": "provider_js"},
        "operation": {"type": "string", "const": "unified_diff"},
        "path": {"type": "string", "maxLength": 300},
        "diff": {"type": "string", "minLength": 1, "maxLength": 24000},
    },
}

PROVIDER_PATCH_MUTATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["scope", "operation", "path", "diff"],
    "properties": {
        "scope": {"type": "string", "const": "provider_patch"},
        "operation": {"type": "string", "const": "unified_diff"},
        "path": {"type": "string", "maxLength": 300},
        "diff": {"type": "string", "minLength": 1, "maxLength": 24000},
    },
}

EXPERIMENT_SPEC_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "route_policy": {"type":"string","enum":["owned_only","owned_plus_peer","owned_plus_peer_generic"]},
        "recipe_policy": {"type":"string","enum":["current_only","current_plus_provider","current_plus_provider_peer"]},
        "role_order": {"type":"array","maxItems":7,"uniqueItems":True,"items":{"type":"string","enum":["search","detail","episode","player","source","api","other"]}},
        "terminal_only": {"type":"boolean"},
        "alias_search": {"type":"boolean"},
        "response_salvage": {"type":"boolean"},
        "document_request_mining": {"type":"boolean"},
        "session_bootstrap": {"type":"boolean"},
        "max_depth": {"type":"integer","minimum":2,"maximum":6},
        "max_pages": {"type":"integer","minimum":6,"maximum":36},
        "max_embeds": {"type":"integer","minimum":6,"maximum":36},
        "max_recipe_passes": {"type":"integer","minimum":1,"maximum":6},
    },
}

REPAIR_PROPOSAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "provider_id",
        "diagnosis",
        "strategy",
        "confidence",
        "target_layer",
        "evidence",
        "mutations",
        "tests",
        "abstain",
        "abstain_reason",
    ],
    "properties": {
        "provider_id": {"type": "string"},
        "diagnosis": {"type": "string", "maxLength": 1200},
        "strategy": {"type": "string", "maxLength": 240},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "target_layer": {
            "type": "string",
            "enum": ["provider", "core", "harness", "network", "unknown"],
        },
        "evidence": {
            "type": "array",
            "maxItems": 12,
            "items": {"type": "string", "maxLength": 500},
        },
        "experiment": deepcopy(EXPERIMENT_SPEC_SCHEMA),
        "mutations": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "oneOf": [
                    deepcopy(DATA_MUTATION_SCHEMA),
                    deepcopy(PROVIDER_PATCH_MUTATION_SCHEMA),
                    deepcopy(JS_MUTATION_SCHEMA),
                ]
            },
        },
        "tests": {
            "type": "array",
            "maxItems": 12,
            "items": {"type": "string", "maxLength": 500},
        },
        "abstain": {"type": "boolean"},
        "abstain_reason": {"type": "string", "maxLength": 1000},
    },
}

def proposal_schema_for(
    provider_id: str,
    causal_prior: dict[str, Any] | None = None,
    mutation_policy: dict[str, Any] | None = None,
    provider_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    schema = deepcopy(REPAIR_PROPOSAL_SCHEMA)
    schema["properties"]["provider_id"] = {"type": "string", "const": provider_id}

    mutation_variants = schema["properties"]["mutations"]["items"]["oneOf"]
    js_variant = next(
        variant for variant in mutation_variants
        if variant["properties"]["scope"].get("const") == "provider_js"
    )
    js_variant["properties"]["path"] = {
        "type": "string",
        "const": f"engine_v2/providers/{provider_id}.mjs",
    }

    patch_variant = next(
        variant for variant in mutation_variants
        if variant["properties"]["scope"].get("const") == "provider_patch"
    )
    patch_paths = [
        str(value).strip()
        for value in (provider_context or {}).get("registered_patch_scripts") or []
        if str(value).strip().startswith("scripts/provider_patches/")
    ][:8]
    if patch_paths:
        patch_variant["properties"]["path"] = {
            "type": "string",
            "enum": list(dict.fromkeys(patch_paths)),
        }

    prior = causal_prior or {}
    confidence = float(prior.get("confidence") or 0.0)
    layer = str(prior.get("target_layer") or "unknown")
    strategy = str(prior.get("strategy_prior") or "")

    if confidence >= 0.90:
        if layer in {"provider", "core", "harness", "network"}:
            schema["properties"]["target_layer"]["enum"] = [layer]
        if strategy:
            schema["properties"]["strategy"] = {
                "type": "string",
                "const": strategy,
            }
        if layer == "provider":
            if "experiment" not in schema["required"]:
                schema["required"].append("experiment")
            schema["properties"]["experiment"]["required"] = [
                "route_policy",
                "recipe_policy",
                "role_order",
                "terminal_only",
                "alias_search",
                "response_salvage",
                "document_request_mining",
                "session_bootstrap",
                "max_depth",
                "max_pages",
                "max_embeds",
                "max_recipe_passes",
            ]

    policy = mutation_policy or {}
    allow_mutations = bool(policy.get("allow_mutations", True))
    allowed_scopes = set(policy.get("allowed_scopes") or [])
    force_abstain = bool(policy.get("force_abstain", False))

    if not allow_mutations:
        schema["properties"]["mutations"]["maxItems"] = 0
    elif allowed_scopes:
        schema["properties"]["mutations"]["items"]["oneOf"] = [
            variant for variant in mutation_variants
            if variant["properties"]["scope"].get("const") in allowed_scopes
        ]
        schema["properties"]["tests"]["minItems"] = 1

    if force_abstain:
        schema["properties"]["abstain"] = {"type": "boolean", "const": True}
        schema["properties"]["tests"]["minItems"] = 1

    return schema
