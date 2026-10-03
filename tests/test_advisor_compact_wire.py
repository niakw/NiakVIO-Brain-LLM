import json
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import ADVISOR_SYSTEM_PROMPT, BrainPlanner
from niakvio_brain_llm.schema import EXPERIMENT_SPEC_SCHEMA, advisor_schema_for


class CaptureAdvisorBackend:
    max_tokens = 160

    def __init__(self):
        self.schema = None
        self.system = ""

    def complete(self, *, system, user, response_schema=None):
        self.system = system
        self.schema = response_schema
        provider = response_schema["properties"]["provider_id"]["const"]
        strategy_prop = response_schema["properties"]["strategy"]
        strategy = strategy_prop.get("const") or "provider_local_repair"
        layer = response_schema["properties"]["target_layer"]["enum"][0]
        return json.dumps({
            "provider_id": provider,
            "strategy": strategy,
            "confidence": 0.96,
            "target_layer": layer,
            "experiment": {
                "route_policy": "owned_plus_peer",
                "recipe_policy": "current_plus_provider",
                "role_order": ["detail", "player", "source"],
                "terminal_only": True,
                "alias_search": False,
                "response_salvage": True,
                "document_request_mining": False,
                "session_bootstrap": False,
                "max_depth": 4,
                "max_pages": 12,
                "max_embeds": 16,
                "max_recipe_passes": 3
            },
            "abstain": False,
            "abstain_reason": ""
        })


class AdvisorCompactWireTests(unittest.TestCase):
    def test_schema_omits_production_repair_payload(self):
        schema = advisor_schema_for(
            "coflix",
            {
                "confidence": 0.96,
                "target_layer": "provider",
                "strategy_prior": "mixed_embed_resolver"
            }
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["properties"]),
            {
                "provider_id", "strategy", "confidence", "target_layer",
                "experiment", "abstain", "abstain_reason"
            }
        )
        self.assertNotIn("mutations", schema["properties"])
        self.assertNotIn("evidence", schema["properties"])
        self.assertNotIn("tests", schema["properties"])
        self.assertEqual(schema["properties"]["strategy"]["const"], "mixed_embed_resolver")
        self.assertEqual(schema["properties"]["target_layer"]["enum"], ["provider"])
        self.assertEqual(
            set(schema["properties"]["experiment"]["required"]),
            set(EXPERIMENT_SPEC_SCHEMA["properties"])
        )

    def test_planner_reconstructs_full_proposal_locally(self):
        backend = CaptureAdvisorBackend()
        proposal = BrainPlanner(backend).plan(
            RepairRequest(
                provider_id="coflix",
                failure_class="variant_coverage_gap",
                status="FULL OK",
                advisor_only=True,
                provider_context={
                    "runtime_variant_coverage": {
                        "riskKind": "variant-coverage-truncation",
                        "dimensions": ["quality", "player", "source"]
                    }
                }
            )
        )
        self.assertEqual(backend.system, ADVISOR_SYSTEM_PROMPT)
        self.assertNotIn("mutations", backend.schema["properties"])
        self.assertEqual(proposal.provider_id, "coflix")
        self.assertEqual(proposal.diagnosis, "advisor-only strategy/experiment guidance")
        self.assertEqual(proposal.mutations, [])
        self.assertEqual(proposal.evidence, [])
        self.assertEqual(proposal.tests, [])
        self.assertTrue(proposal.experiment)


if __name__ == "__main__":
    unittest.main()
