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
            "evidence": ["player reached"],
            "mutations": [{"scope": "provider_js", "operation": "replace extractor"}],
            "tests": ["known positive movie"],
            "abstain": False,
            "abstain_reason": ""
        })
        proposal = BrainPlanner(StaticBackend(response)).plan(
            RepairRequest(provider_id="demo", failure_class="terminal_extractor")
        )
        self.assertEqual(proposal.strategy, "repair_terminal_extractor")

    def test_rejects_forbidden_scope(self):
        response = json.dumps({
            "provider_id": "demo",
            "diagnosis": "guess",
            "strategy": "rewrite_core",
            "confidence": 0.9,
            "mutations": [{"scope": "core", "operation": "rewrite"}]
        })
        with self.assertRaises(ValueError):
            BrainPlanner(StaticBackend(response)).plan(
                RepairRequest(provider_id="demo", failure_class="unknown")
            )

if __name__ == "__main__":
    unittest.main()
