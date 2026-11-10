from __future__ import annotations
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from niakvio_brain_llm.contracts import RepairRequest
from benchmark.source_model_challenger import TOPOLOGIES, classify_proposal


class SourceModelChallengerContract(unittest.TestCase):
    def test_four_independent_architectures(self):
        self.assertEqual(set(TOPOLOGIES),
                         {"4khdhub", "allanime", "moviesmod", "yflix"})
        self.assertEqual(len(set(TOPOLOGIES.values())), 4)

    def test_workflow_never_uploads_unreviewed_candidate_bytes(self):
        from pathlib import Path
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/source-model-challenger-cpu.yml").read_text()
        self.assertIn("--provider 4khdhub",workflow)
        self.assertIn("apply_brain_llm_force_mutations.py",workflow)
        self.assertIn("materialize_provider_v3_one.py 4khdhub",workflow)
        self.assertIn("node scripts/health_check.mjs --deep",workflow)
        uploaded=workflow.split("      - name: Upload sanitized read-only diagnostics",1)[1]
        self.assertNotIn("private-",uploaded)
        self.assertNotIn("provider-overrides.json",uploaded)
        self.assertNotIn("providers/",uploaded)

    def test_invalid_unbound_mutation_not_counted_as_admissible(self):
        request = RepairRequest(provider_id="moviesmod", failure_class="route_proven_gap",
                                provider_context={})
        proposal = SimpleNamespace(
            mutations=[{"scope": "provider_js", "path": "/tmp/unowned.js", "operation": "replace"}],
            target_layer="provider", strategy="repair", abstain=False)
        with patch("benchmark.source_model_challenger.build_causal_prior",
                   return_value={"target_layer": "provider", "strategy_prior": "repair"}):
            result = classify_proposal(request, proposal)
        self.assertFalse(result["mutationPolicyCompliant"])
        self.assertFalse(result["mutationDslValid"])
        self.assertFalse(result["published"])
        self.assertFalse(result["executed"])
        self.assertFalse(result["validated"])

    def test_abstention_without_patch_is_not_a_success(self):
        request = RepairRequest(provider_id="allanime", failure_class="chain_terminal_gap")
        proposal = SimpleNamespace(
            mutations=[], target_layer="provider", strategy="", abstain=True)
        with patch("benchmark.source_model_challenger.build_causal_prior",
                   return_value={"target_layer": "provider", "strategy_prior": ""}):
            result = classify_proposal(request, proposal)
        self.assertTrue(result["schemaValid"])
        self.assertEqual(result["mutationCount"], 0)
        self.assertFalse(result["mutationDslValid"])
        self.assertFalse(result["materialized"])
