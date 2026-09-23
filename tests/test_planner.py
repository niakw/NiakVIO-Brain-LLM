import json
import unittest

from niakvio_brain_llm.backend import StaticBackend
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.planner import BrainPlanner

class PlannerTests(unittest.TestCase):
    def test_accepts_bounded_provider_mutation(self):
        response = json.dumps({
            "provider_id": "demo",
            "diagnosis": "terminal extractor changed",
            "strategy": "repair_terminal_extractor",
            "confidence": 0.8,
            "target_layer": "provider",
            "evidence": ["player reached"],
            "mutations": [{
                "scope": "provider_js",
                "operation": "unified_diff",
                "path": "engine_v2/providers/demo.mjs",
                "diff": "--- a/engine_v2/providers/demo.mjs\n+++ b/engine_v2/providers/demo.mjs\n@@\n-old\n+new"
            }],
            "tests": ["known positive movie"],
            "abstain": False,
            "abstain_reason": ""
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(
                provider_id="demo",
                failure_class="unknown_provider_gap",
                status="CHAIN REACHED",
                provider_context={"authored_module": "export default {}"},
            )
        )
        self.assertEqual(proposal.strategy, "repair_terminal_extractor")
        self.assertEqual(proposal.target_layer, "provider")

    def test_rejects_forbidden_scope(self):
        response = json.dumps({
            "provider_id": "demo",
            "diagnosis": "guess",
            "strategy": "rewrite_core",
            "confidence": 0.9,
            "target_layer": "provider",
            "mutations": [{"scope": "core", "operation": "rewrite"}],
            "tests": ["retest"],
            "abstain": False,
            "abstain_reason": ""
        })
        with self.assertRaises(ValueError):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(provider_id="demo", failure_class="unknown")
            )

    def test_non_provider_layer_is_bounded_abstention(self):
        response = json.dumps({
            "provider_id": "demo",
            "diagnosis": "transport environment differs",
            "strategy": "compare_browser_native_residential_profiles_without_provider_mutation",
            "confidence": 0.9,
            "target_layer": "harness",
            "evidence": ["browser/native differ"],
            "mutations": [],
            "tests": ["native transport replay"],
            "abstain": True,
            "abstain_reason": "provider mutation is not justified"
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(provider_id="demo", failure_class="transport_environment_gap")
        )
        self.assertTrue(proposal.abstain)
        self.assertEqual(proposal.target_layer, "harness")

    def test_private_chat_document_reaches_planner_prompt(self):
        planner = BrainPlanner(
            StaticBackend("{}"),
            documents=DocumentStore([{
                "kind": "document",
                "document_id": "private-1",
                "source": "niakvio-private-chat",
                "private_memory": True,
                "proof_authority": False,
                "path": "conversations/c1/index.json",
                "heading": "architecture",
                "role": "private_chat_signal",
                "authority": 55,
                "text": "Movix api discovery gap current route and provider repair strategy",
            }]),
        )
        _, documents, _, _, user = planner._prepare(
            RepairRequest(
                provider_id="movix",
                failure_class="api_discovery_gap",
                status="CHAIN REACHED",
            )
        )
        self.assertTrue(documents)
        self.assertEqual(documents[0]["source"], "niakvio-private-chat")
        self.assertIn("niakvio-private-chat", user)
        self.assertIn("Movix api discovery gap", user)

    def test_raw_proposal_skips_production_post_validation(self):
        response = json.dumps({
            "provider_id": "wrong-id",
            "diagnosis": "raw benchmark answer",
            "strategy": "wrong_strategy",
            "confidence": 0.5,
            "target_layer": "core",
            "evidence": [],
            "mutations": [],
            "tests": [],
            "abstain": False,
            "abstain_reason": ""
        })
        proposal = BrainPlanner(StaticBackend(response)).propose_raw(
            RepairRequest(provider_id="demo", failure_class="api_discovery_gap")
        )
        self.assertEqual(proposal.provider_id, "wrong-id")
        self.assertEqual(proposal.strategy, "wrong_strategy")

if __name__ == "__main__":
    unittest.main()
