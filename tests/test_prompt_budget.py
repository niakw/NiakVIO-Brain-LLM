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
                "route_contract": {
                    "capability": "html_scraper",
                    "learnedRoutes": ["/?s={query}"],
                    "candidateRoutes": ["/detail/{slug}", "/player/{id}"],
                },
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
assert ctx.get("route_contract", {}).get("learnedRoutes") == ["/?s={query}"]
if "published_bundle" in ctx:
    assert len(ctx["published_bundle"].get("providerBlocks") or []) <= 1

print("bounded advisor prompt context contract passed")


class AdvisorOnlyVariantRequest(FakeRequest):
    def to_dict(self):
        data = super().to_dict()
        data["provider_id"] = "coflix"
        data["failure_class"] = "variant_coverage_gap"
        data["status"] = "FULL OK"
        data["advisor_only"] = True
        data["allowed_mutations"] = ["provider_bloc", "provider_patch"]
        data["provider_context"]["runtime_variant_coverage"] = {
            "riskKind": "variant-coverage-truncation",
            "dimensions": ["player", "server", "source", "quality"],
            "lanes": [
                {
                    "lane": lane,
                    "announcedVariantCandidates": 19,
                    "streamsReturned": 2,
                    "state": "returned-subset",
                    "announcedQualityHeights": [360, 480, 720, 1080, 2160],
                    "notes": "x" * 2000,
                }
                for lane in ("anime", "movie", "tv")
            ],
        }
        data["provider_context"]["advisor_experiment_history"] = [
            {
                "failureClass": "variant_coverage_gap",
                "lastReason": "blocked current sandbox " + ("z" * 2000),
                "observedPipelineStage": "player",
                "experimentFingerprint": str(i) * 64,
            }
            for i in range(32)
        ]
        data["observations"].append({
            "source": "census-sharded-current",
            "value": {
                "fanout": {
                    "movie": {
                        "announcedVariantCandidates": 19,
                        "streamsReturned": 2,
                        "state": "returned-subset",
                        "announcedQualityHeights": [360, 480, 720, 1080, 2160],
                    }
                },
                "structureHints": ["player->server->variants"] * 20,
            },
        })
        return data


advisor_payload = build_prompt_payload(
    AdvisorOnlyVariantRequest(),
    experiences,
    documents,
    {
        "confidence": 0.95,
        "target_layer": "provider",
        "strategy_prior": "enumerate_stream_variants_before_global_cap",
    },
    {
        "allow_mutations": True,
        "allowed_scopes": ["provider_bloc", "provider_patch"],
        "required_tests": ["playback", "identity", "variant-coverage"],
    },
)
advisor_encoded = json.dumps(advisor_payload, ensure_ascii=True, separators=(",", ":"))
assert len(advisor_encoded) <= 7800, len(advisor_encoded)
assert advisor_payload["context_budget"]["serialized_user_chars"] <= 7600
assert advisor_payload["context_budget"]["mode"] == "advisor-only"
assert advisor_payload["mutation_policy"]["allow_mutations"] is False
assert advisor_payload["mutation_policy"]["allowed_scopes"] == []
advisor_ctx = advisor_payload["request"]["provider_context"]
assert advisor_ctx.get("runtime_variant_coverage", {}).get("riskKind") == "variant-coverage-truncation"
assert advisor_payload["request"]["advisor_only"] is True


class ExtremeAdvisorVariantRequest(AdvisorOnlyVariantRequest):
    def to_dict(self):
        data = super().to_dict()
        # Reproduce the real Coflix failure mode: several simultaneously rich
        # current-evidence contracts survive normal compaction and can still
        # exceed the advisor payload budget.
        data["census_prior"] = {
            f"lane_{i}": {f"k{j}": "c" * 1200 for j in range(8)}
            for i in range(8)
        }
        data["provider_context"]["route_contract"] = {
            f"route_{i}": {
                "path": "/player/" + ("r" * 600),
                "role": "player-resolver",
                "method": "GET",
                "notes": "n" * 1200,
            }
            for i in range(8)
        }
        data["provider_context"]["current_structure_evidence"] = {
            f"group_{i}": {
                "originHost": "current.example",
                "routes": ["/detail/" + ("x" * 500)] * 8,
                "fanout": {
                    "groupCount": 8,
                    "groupVariantCounts": [19] * 8,
                    "indexedVariantCount": 152,
                },
            }
            for i in range(8)
        }
        data["provider_context"]["runtime_variant_coverage"] = {
            "riskKind": "variant-coverage-truncation",
            "dimensions": ["player", "server", "source", "quality"],
            "lanes": [
                {
                    "lane": f"lane-{i}",
                    "announcedVariantCandidates": 19,
                    "streamsReturned": 2,
                    "state": "returned-subset",
                    "notes": "v" * 1200,
                }
                for i in range(8)
            ],
        }
        data["observations"] = [
            {
                "source": source,
                "value": {f"k{j}": "o" * 1200 for j in range(8)},
            }
            for source in (
                "current-provider-structure",
                "census-sharded-current",
                "runtime-variant-coverage-current",
                "targeted-regression-current",
                "census_current",
                "other",
            )
        ]
        return data


extreme_payload = build_prompt_payload(
    ExtremeAdvisorVariantRequest(),
    experiences,
    documents,
    {
        "confidence": 0.95,
        "target_layer": "provider",
        "strategy_prior": "enumerate_stream_variants_before_global_cap",
        "failure_signature": "variant-coverage-gap:coflix",
    },
    {
        "allow_mutations": True,
        "allowed_scopes": ["provider_bloc", "provider_patch"],
        "required_tests": ["playback", "identity", "variant-coverage"],
    },
)
extreme_encoded = json.dumps(extreme_payload, ensure_ascii=True, separators=(",", ":"))
assert len(extreme_encoded) <= 7800, len(extreme_encoded)
assert extreme_payload["context_budget"]["serialized_user_chars"] <= 7600
assert extreme_payload["context_budget"]["essential_current_evidence"] is True
assert extreme_payload["mutation_policy"]["allow_mutations"] is False
extreme_ctx = extreme_payload["request"]["provider_context"]
assert extreme_ctx["runtime_variant_coverage"]["riskKind"] == "variant-coverage-truncation"
assert "current_structure_evidence" in extreme_ctx
assert "route_contract" in extreme_ctx
assert extreme_payload["request"]["observations"][0]["source"] == "current-provider-structure"
assert any(
    row.get("source") == "census-sharded-current"
    for row in extreme_payload["request"]["observations"]
)
