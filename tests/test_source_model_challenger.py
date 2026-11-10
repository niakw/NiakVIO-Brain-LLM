from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from niakvio_brain_llm.contracts import RepairRequest
from benchmark.source_model_challenger import TOPOLOGIES, classify_proposal, production_first_scope_request
from scripts.publish_niakvio_force_mutations import validate_current_provider_bloc_anchors
from benchmark.source_replay_evidence import summarize_deep_report


class SourceModelChallengerContract(unittest.TestCase):


    def test_deep_replay_real_environment_string_is_not_sha_authority(self):
        sha = "a" * 40
        report = {
            "environment": "github-hosted/ubuntu",
            "results": [{
                "key": "published:4khdhub",
                "status": "provider_unreachable",
                "tests": [{"streams_playable": 0, "identity_verified_streams": 0}],
                "evidence": {"failure_classes": ["no_provider_request_observed"]},
            }],
        }
        result = summarize_deep_report(report, provider="4khdhub", source_sha=sha)
        self.assertEqual(result["sourceSha"], sha)
        self.assertEqual(result["status"], "provider_unreachable")
        self.assertEqual(result["playable"], 0)
        self.assertFalse(result["validated"])
        self.assertTrue(result["candidateMaterialized"])
        self.assertTrue(result["sandboxExecuted"])
        self.assertFalse(result["published"])

    def test_deep_replay_never_merges_playable_and_identity_from_different_fixtures(self):
        report = {
            "results": [{
                "key": "published:allanime",
                "status": "degraded",
                "tests": [
                    {"streams_playable": 1, "identity_verified_streams": 0},
                    {"streams_playable": 0, "identity_verified_streams": 1},
                ],
            }],
        }
        result = summarize_deep_report(report, provider="allanime", source_sha="b"*40)
        self.assertFalse(result["validated"])
        self.assertEqual(result["identityMatchedPlayable"], 0)

    def test_deep_replay_requires_exact_provider_and_nonempty_fixture(self):
        source = {"results": [{"key": "published:other", "status": "healthy", "tests": []}]}
        with self.assertRaisesRegex(ValueError, "provider identity"):
            summarize_deep_report(source, provider="moviesmod", source_sha="c"*40)
        with self.assertRaisesRegex(ValueError, "SHA"):
            summarize_deep_report(source, provider="moviesmod", source_sha="unknown")

    def test_deep_replay_positive_requires_playable_same_fixture_identity(self):
        report = {
            "results": [{
                "key": "published:yflix", "status": "healthy",
                "tests": [{"streams_playable": 2, "identity_verified_streams": 1}],
            }],
        }
        result = summarize_deep_report(report, provider="yflix", source_sha="d"*40)
        self.assertEqual(result["identityMatchedPlayable"], 1)
        self.assertTrue(result["validated"])

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

    def test_production_scope_first_matches_actual_shared_selector(self):
        from niakvio_brain_llm.force_scope_order import select_force_scopes
        request = RepairRequest(
            provider_id="demo", failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            allowed_mutations=["provider_data", "provider_patch", "provider_bloc"],
            provider_context={
                "runtimeMutationSource": "function resolver(){return resolvePlayer(url);}",
                "runtime_template_prior": {"reuseBeforeNovelBloc": True},
                "override": {"official_site": "https://site.invalid"},
                "registered_patch_sources": {"scripts/provider_patches/demo.py": "MANAGED_FIX_ID"},
            },
        )
        before = list(request.allowed_mutations)
        scoped, chosen = production_first_scope_request(request)
        self.assertEqual(chosen, select_force_scopes(request)[0])
        self.assertEqual(chosen, "provider_bloc")
        self.assertEqual(scoped.allowed_mutations, ["provider_bloc"])
        self.assertEqual(request.allowed_mutations, before)

    def test_four_independent_architectures(self):
        self.assertEqual(set(TOPOLOGIES),
                         {"4khdhub", "allanime", "moviesmod", "yflix"})
        self.assertEqual(len(set(TOPOLOGIES.values())), 4)

    def test_workflow_never_uploads_unreviewed_candidate_bytes(self):
        from pathlib import Path
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/source-model-challenger-cpu.yml").read_text()
        self.assertIn('--provider "$PROVIDER_ID" --canonical-force --model-only-force',workflow)
        self.assertIn("provider_id: [4khdhub, allanime, moviesmod, yflix]", workflow)
        self.assertIn("python -m benchmark.source_model_challenger", workflow)
        from benchmark import source_model_challenger as source_challenger
        import inspect
        self.assertIn("allow_deterministic_force=not args.model_only_force",
                      inspect.getsource(source_challenger.main))
        self.assertIn("apply_brain_llm_force_mutations.py",workflow)
        self.assertIn('materialize_provider_v3_one.py "$PROVIDER_ID"',workflow)
        self.assertIn('--provider "$PROVIDER_ID"',workflow)
        self.assertIn('brain-qwen35-9b-real-source-diagnostic-${{ matrix.provider_id }}',workflow)
        self.assertIn("node scripts/health_check.mjs --deep",workflow)
        self.assertIn("python -m benchmark.source_replay_evidence",workflow)
        uploaded=workflow.split("      - name: Upload sanitized read-only diagnostics",1)[1]
        self.assertNotIn("private-",uploaded)
        self.assertNotIn("provider-overrides.json",uploaded)
        self.assertNotIn("providers/",uploaded)


    def test_hosted_adapter_has_no_paid_workflow_entrypoint(self):
        # Explicit operator CLI opt-in cannot silently become a billable GitHub
        # Action. Existing tests.test_no_paid_api owns this policy globally.
        root = Path(__file__).resolve().parents[1]
        self.assertFalse((root / ".github/workflows/hosted-source-model-challenger.yml").exists())
        script = (root / "benchmark/source_model_challenger.py").read_text()
        self.assertIn('--backend", choices=("local", "hosted")', script)
        self.assertIn('HostedResponsesBackend.from_environment(', script)
        self.assertIn('hosted challenger must use constrained model-only FORCE', script)
        self.assertIn('hosted source challenger allows exactly one requested provider', script)

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
