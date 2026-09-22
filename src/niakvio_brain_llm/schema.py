from __future__ import annotations

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
