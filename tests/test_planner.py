import json
import unittest

from niakvio_brain_llm.backend import StaticBackend
from niakvio_brain_llm.contracts import RepairRequest
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
            RepairRequest(provider_id="demo", failure_class="terminal_extractor")
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
            "mutations": [{"scope": "core", "operation": "rewrite"}]
        })
        with self.assertRaises(ValueError):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(provider_id="demo", failure_class="unknown")
            )

    def test_non_provider_layer_forces_abstention(self):
        response = json.dumps({
            "provider_id": "demo",
            "diagnosis": "CI challenge only",
            "strategy": "retest_representative_harness",
            "confidence": 0.82,
            "target_layer": "harness",
            "mutations": [],
            "tests": ["native transport replay"],
            "abstain": False
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(provider_id="demo", failure_class="provider_waf_challenge")
        )
        self.assertTrue(proposal.abstain)
        self.assertEqual(proposal.target_layer, "harness")

if __name__ == "__main__":
    unittest.main()
