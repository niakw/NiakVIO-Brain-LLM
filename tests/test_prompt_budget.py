from __future__ import annotations

import json

from niakvio_brain_llm.prompting import build_prompt_payload


class FakeRequest:
    def to_dict(self):
        return {
            "provider_id": "synthetic",
            "failure_class": "route_proven_gap",
            "status": "ROUTE PROVEN",
            "supported_types": ["movie", "tv"],
            "allowed_mutations": ["provider_patch"],
            "observations": [
                {"source": "x", "value": "o" * 5000, "nested": [{"text": "n" * 5000}]}
                for _ in range(10)
            ],
            "census_prior": {"blob": "c" * 8000},
            "provider_context": {
                "source_repo": "niakw/NiakVIO",
                "read_only": True,
                "provider_id": "synthetic",
                "published_bundle": {
                    "filename": "providers/synthetic.js",
                    "version": "1",
                    "supportedTypes": ["movie", "tv"],
                    "formats": ["m3u8"],
                    "providerBlocks": [
                        {"id": f"B{i}", "source": "p" * 10000}
                        for i in range(4)
                    ],
                },
                "registered_patch_scripts": [
                    f"scripts/provider_patches/p{i}.cjs" for i in range(8)
                ],
                "registered_patch_sources": {
                    f"scripts/provider_patches/p{i}.cjs": "s" * 12000
                    for i in range(4)
                },
                "authored_module": "a" * 12000,
                "override": "v" * 6000,
                "hub": "h" * 6000,
                "advisor_experiment_history": [
                    {"lastReason": "r" * 1000, "observed": "x" * 1000}
                    for _ in range(40)
                ],
                "unbounded_private_or_irrelevant_context": "z" * 50000,
            },
        }


experiences = [
    {
        "experience_id": str(i),
        "providers": ["synthetic"],
        "failure_class": "route_proven_gap",
        "strategy": "strategy",
        "lesson": "e" * 5000,
    }
    for i in range(6)
]
documents = [
    {"source": "doc", "path": "x", "text": "d" * 10000}
    for _ in range(4)
]

payload = build_prompt_payload(
    FakeRequest(),
    experiences,
    documents,
    {"confidence": 0.5, "target_layer": "provider", "strategy_prior": "repair"},
    {"allow_mutations": False, "allowed_scopes": []},
)
encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
assert len(encoded) <= 7800, len(encoded)
assert payload["context_budget"]["serialized_user_chars"] <= 7600
ctx = payload["request"]["provider_context"]
assert "unbounded_private_or_irrelevant_context" not in ctx
assert len(ctx.get("advisor_experiment_history") or []) <= 6
if "published_bundle" in ctx:
    assert len(ctx["published_bundle"].get("providerBlocks") or []) <= 1

print("bounded advisor prompt context contract passed")
