from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from niakvio_brain_llm.contracts import RepairRequest
from benchmark.source_model_challenger import TOPOLOGIES, classify_proposal
from scripts.publish_niakvio_force_mutations import validate_current_provider_bloc_anchors


class SourceModelChallengerContract(unittest.TestCase):

    def test_real_source_anchor_contract_across_four_independent_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "providers").mkdir()
            (root / "manifest.json").write_text(json.dumps({
                "scrapers": [{"id": name, "filename": f"providers/{name}.js"}
                             for name in TOPOLOGIES]
            }), encoding="utf-8")
            candidate = {"scope": "provider_bloc",
                         "find": "return decodeProviderPayload(raw);",
                         "replace": "return decodeProviderPayload(raw || '');"}
            for provider in TOPOLOGIES:
                path = root / "providers" / f"{provider}.js"
                path.write_text(
                    "/* BEGIN NIAKVIO_PROVIDER */\n"
                    "return decodeProviderPayload(raw);\n"
                    "/* STARTFIX:CORE.IDENTITY */\n"
                    "return coreGuard();\n"
                    "/* END NIAKVIO_PROVIDER */\n", encoding="utf-8")
                self.assertTrue(validate_current_provider_bloc_anchors(root, provider, [candidate]))
                for bad_find in ["return missing();", "return coreGuard();"]:
                    with self.assertRaisesRegex(ValueError, "absent or non-unique"):
                        validate_current_provider_bloc_anchors(
                            root, provider, [{**candidate, "find": bad_find}]
                        )
                path.write_text(
                    "/* BEGIN NIAKVIO_PROVIDER */\n"
                    "return decodeProviderPayload(raw);\n"
                    "return decodeProviderPayload(raw);\n"
                    "/* END NIAKVIO_PROVIDER */\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "absent or non-unique"):
                    validate_current_provider_bloc_anchors(root, provider, [candidate])

    def test_non_bloc_mutation_does_not_require_runtime_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(validate_current_provider_bloc_anchors(
                Path(tmp), "unregistered", [{"scope": "provider_data"}]
            ))

    def test_four_independent_architectures(self):
        self.assertEqual(set(TOPOLOGIES),
                         {"4khdhub", "allanime", "moviesmod", "yflix"})
        self.assertEqual(len(set(TOPOLOGIES.values())), 4)

    def test_workflow_never_uploads_unreviewed_candidate_bytes(self):
        from pathlib import Path
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/source-model-challenger-cpu.yml").read_text()
        self.assertIn("--provider 4khdhub --canonical-force",workflow)
        self.assertIn("python -m benchmark.source_model_challenger", workflow)
        from benchmark import source_model_challenger as source_challenger
        import inspect
        self.assertIn("planner.plan(request, compact_force=True)",
                      inspect.getsource(source_challenger.main))
        self.assertIn("apply_brain_llm_force_mutations.py",workflow)
        self.assertIn("materialize_provider_v3_one.py 4khdhub",workflow)
        self.assertIn("node scripts/health_check.mjs --deep",workflow)
        uploaded=workflow.split("      - name: Upload sanitized read-only diagnostics",1)[1]
        self.assertNotIn("private-",uploaded)
        self.assertNotIn("provider-overrides.json",uploaded)
        self.assertNotIn("providers/",uploaded)

    def test_registered_provider_patch_is_not_a_false_negative(self):
        from benchmark.source_model_challenger import classify_proposal
        path = "scripts/provider_patches/already_registered.py"
        request = RepairRequest(
            provider_id="4khdhub", failure_class="route_proven_gap",
            provider_context={"registered_patch_scripts": [path]},
            allowed_mutations=["provider_patch"],
        )
        diff = (
            f"--- a/{path}\\n+++ b/{path}\\n@@ -1 +1 @@\\n"
            "-old\\n+new\\n"
        )
        proposal = SimpleNamespace(
            mutations=[{"scope": "provider_patch", "operation": "unified_diff",
                        "path": path, "diff": diff}],
            target_layer="provider", strategy="repair", abstain=False,
        )
        with patch("benchmark.source_model_challenger.build_causal_prior",
                   return_value={"target_layer": "provider", "strategy_prior": "repair"}):
            with patch("benchmark.source_model_challenger.build_mutation_policy",
                       return_value={"allow_mutations": True,
                                     "allowed_scopes": ["provider_patch"]}):
                with tempfile.TemporaryDirectory() as tmp:
                    allowed = classify_proposal(request, proposal,
                                                niakvio_root=Path(tmp))
                    forbidden = classify_proposal(
                        RepairRequest(provider_id="4khdhub",
                                      failure_class="route_proven_gap",
                                      allowed_mutations=["provider_patch"],
                                      provider_context={"registered_patch_scripts": []}),
                        proposal, niakvio_root=Path(tmp))
        self.assertTrue(allowed["mutationDslValid"])
        self.assertTrue(allowed["canonicalApplyEligible"])
        self.assertFalse(forbidden["mutationDslValid"])
        self.assertFalse(forbidden["canonicalApplyEligible"])

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
