from __future__ import annotations

from copy import deepcopy
from typing import Any

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
        "mutations": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "scope": {"enum": ["provider_data", "provider_js"]},
                    "operation": {"enum": ["set", "delete", "append", "unified_diff"]},
                    "path": {"type": "string", "maxLength": 300},
                    "value": {},
                    "diff": {"type": "string", "maxLength": 24000},
                },
                "required": ["scope", "operation", "path"],
                "additionalProperties": False,
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
) -> dict[str, Any]:
    schema = deepcopy(REPAIR_PROPOSAL_SCHEMA)
    schema["properties"]["provider_id"] = {"type": "string", "const": provider_id}

    prior = causal_prior or {}
    confidence = float(prior.get("confidence") or 0.0)
    layer = str(prior.get("target_layer") or "unknown")

    if confidence >= 0.90 and layer in {"provider", "core", "harness", "network"}:
        schema["properties"]["target_layer"]["enum"] = [layer]
        if layer != "provider":
            schema["properties"]["mutations"]["maxItems"] = 0
            schema["properties"]["abstain"] = {"type": "boolean", "const": True}

    return schema
