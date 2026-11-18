"""Reproduce bounded FORCE retry with current network and verification feedback.

The code under test receives a realistic high-cardinality sanitized response
trace. It must preserve the exact selected JS unit and request identities while
dropping optional duplicate hints before allowing CPU inference.
"""
import json
import os
import unittest
from unittest.mock import patch

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm import prompting


class ForceCpuRetryBudgetTests(unittest.TestCase):
    def test_large_retry_remains_within_cpu_limit_and_preserves_units(self):
        source = (
            "async function _crawlDirectMedia(query){\n"
            + "".join(f"const seen{i}=query;\n" for i in range(130))
            + "if (query && query.player) {\n"
            + "const playerData = extractPlayers(query);\n"
            + "return playerData.filter(Boolean);\n"
            + "}\nreturn [];\n}\n"
        )
        network = [
            {
                "fixture": "Sekai S01E01",
                "stage": ["search", "detail", "player", "source", "media"][i % 5],
                "status": 200,
                "response_structure": {
                    "kind": "html",
                    "tags": [
                        {"tag": "iframe", "attribute": "data-src",
                         "value": "non-authoritative-observation-" + "a" * 220}
                        for _ in range(10)
                    ],
                    "player_markup": {
                        "rows": [{"tag": "iframe", "count": 3, "value_kinds": {
                            "data-src": "relative_url"}}] * 8,
                    },
                },
                "functions": ["_crawlDirectMedia"],
            } for i in range(10)
        ]
        fixtures = [
            {
                "fixture": "Sekai S01E01",
                "category": "anime",
                "tmdbId": "1001",
                "season": 1,
                "episode": 1,
                "status": "no_streams",
                "streamsReturned": 0,
                "streamsPlayable": 0,
                "extra": {"observations": ["provider-observed-no-playback"] * 12},
            } for _ in range(7)
        ]
        request = RepairRequest(
            provider_id="sekai", failure_class="route_proven_gap",
            status="REGRESSION PROVIDER",
            observations=[{
                "source": "force-validation",
                "stage": "force_validation_feedback",
                "reason": "model_invalid",
                "value": {"error": "invalid edit body", "outcome": "rejected"},
            }],
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": source,
                "runtimeMutationFilename": "providers/sekai.js",
                "live_runtime_evidence": {
                    "active_functions": ["_crawlDirectMedia"],
                    "network_evidence": network,
                    "fixture_evidence": fixtures,
                    "previous_verification": {
                        "reason": "invalid_edit_not_materialized",
                        "executionObserved": False,
                        "candidate_network": network,
                    },
                },
                "same_provider_execution_prior": {
                    "recipes": [{"kind": "player_crawl", "notes": "old hint" * 25}] * 6
                },
            },
        )
        policy = {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]}
        with patch.dict(os.environ, {"NIAKVIO_FORCE_CPU_TIGHT_PROMPT": "1"}):
            compact = prompting.build_force_prompt_payload(request, {}, policy)
        with patch.dict(os.environ, {"NIAKVIO_FORCE_CPU_TIGHT_PROMPT": "0"}):
            unconstrained = prompting.build_force_prompt_payload(request, {}, policy)
        length = lambda x: len(json.dumps(x, ensure_ascii=True, separators=(",", ":")))
        self.assertLessEqual(length(compact), 12000)
        self.assertEqual(
            compact["new_bloc_target"]["editable_units"],
            unconstrained["new_bloc_target"]["editable_units"],
        )
        self.assertTrue(compact["new_bloc_target"]["editable_units"])
        self.assertEqual(compact["output_contract"]["validation_retry_context"], "focused")
        self.assertTrue(compact["mutation_policy"]["allow_mutations"])
        self.assertEqual(compact["current_fixture_evidence"][0]["tmdbId"], "1001")
        self.assertEqual(compact["current_fixture_evidence"][0]["episode"], 1)


if __name__ == "__main__":
    unittest.main()
