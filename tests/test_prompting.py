import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import build_force_prompt_payload, build_prompt_payload

class PromptingTests(unittest.TestCase):
    def test_large_context_is_bounded(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="unknown",
            provider_context={
                "authored_module": "x" * 20000,
                "override": "y" * 10000,
            },
            observations=[{"blob": "z" * 10000}],
        )
        payload = build_prompt_payload(request, [{
            "failure_class": "unknown",
            "strategy": "inspect",
            "lesson": "l" * 10000,
        }])
        self.assertLess(len(payload["request"]["provider_context"]["authored_module"]), 2300)
        self.assertLess(len(payload["request"]["observations"][0]["blob"]), 700)
        self.assertLess(len(payload["retrieved_experiences"][0]["lesson"]), 700)

    def test_high_confidence_prior_uses_focused_rag_budget(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={"override": "{}"},
        )
        experiences = [
            {"experience_id": str(i), "failure_class": "chain_terminal_gap", "lesson": "x"}
            for i in range(5)
        ]
        documents = [
            {"path": f"d{i}.md", "text": "x" * 2000}
            for i in range(4)
        ]
        payload = build_prompt_payload(
            request,
            experiences,
            documents,
            {"target_layer": "provider", "confidence": 0.96},
            {"allow_mutations": True},
        )
        self.assertEqual(payload["context_budget"]["mode"], "focused")
        self.assertEqual(len(payload["retrieved_experiences"]), 1)
        self.assertEqual(len(payload["retrieved_documents"]), 0)

    def test_force_mutation_context_prefers_registered_bloc_sources(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            provider_context={
                "published_bundle": {
                    "filename": "providers/demo--nuvio--abc.js",
                    "version": "1.2.3",
                    "providerBlocks": [
                        {"id": "PROVIDER.DEMO.RUNTIME.V1", "source": "P" * 10000},
                        {"id": "PROVIDER.DEMO.CONFIG.V1", "source": "Q" * 10000},
                        {"id": "PROVIDER.DEMO.EXTRA.V1", "source": "R" * 10000},
                    ],
                },
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": "A" * 10000,
                    "scripts/provider_patches/demo_extra_v1.py": "B" * 10000,
                    "scripts/provider_patches/demo_third_v1.py": "C" * 10000,
                },
                "authored_module": "M" * 10000,
                "override": "O" * 10000,
                "hub": "H" * 10000,
            },
        )
        payload = build_prompt_payload(
            request,
            [{"experience_id": "1", "lesson": "x" * 1000}],
            [{"path": "doc.md", "text": "x" * 4000}],
            {"target_layer": "provider", "confidence": 0.95},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        context = payload["request"]["provider_context"]
        # Advisor context keeps one representative Bloc; exact multi-Bloc source
        # remains available to compact Force and deterministic validation.
        self.assertEqual(len(context["published_bundle"]["providerBlocks"]), 1)
        self.assertLessEqual(
            max(len(v["source"]) for v in context["published_bundle"]["providerBlocks"]),
            3412,
        )
        self.assertEqual(context["published_bundle"]["filename"], "providers/demo--nuvio--abc.js")
        self.assertEqual(len(context["registered_patch_sources"]), 1)
        self.assertLessEqual(max(len(v) for v in context["registered_patch_sources"].values()), 2212)
        self.assertLess(len(context["authored_module"]), 1000)
        self.assertLess(len(context["override"]), 1000)
        self.assertLess(len(context["hub"]), 550)
        self.assertEqual(len(payload["retrieved_experiences"]), 1)
        self.assertEqual(payload["retrieved_documents"], [])

    def test_force_prompt_is_provider_local_and_drops_rag_bulk(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            observations=[{"stage": "player", "blob": "Z" * 5000} for _ in range(8)],
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": "HEAD" + ("A" * 10000) + "TAIL",
                    "scripts/provider_patches/demo_extra_v1.py": "B" * 10000,
                },
                "authored_module": "M" * 10000,
                "override": "O" * 10000,
                "published_bundle": {"providerBlocks": [{"source": "P" * 10000}]},
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "terminal_media_extractor_with_playback_validation"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        self.assertEqual(payload["mutation_target"]["scope"], "provider_patch")
        self.assertEqual(payload["mutation_target"]["path"], "scripts/provider_patches/demo_runtime_v1.py")
        self.assertLessEqual(len(payload["mutation_target"]["source"]), 12050)
        self.assertIn("HEAD", payload["mutation_target"]["source"])
        self.assertIn("TAIL", payload["mutation_target"]["source"])
        self.assertEqual(len(payload["current_observations"]), 3)
        self.assertNotIn("retrieved_experiences", payload)
        self.assertNotIn("retrieved_documents", payload)
        self.assertNotIn("published_bundle", payload)
        self.assertEqual(payload["output_contract"]["file_edit_format"], "unique_find_replace")
        self.assertTrue(payload["output_contract"]["find_must_be_exact_and_unique"])

    def test_brain_owned_required_tests_are_hidden_from_model(self):
        payload = build_prompt_payload(
            RepairRequest(provider_id="demo", failure_class="chain_terminal_gap"),
            [],
            [],
            {"target_layer": "provider", "confidence": 0.96},
            {
                "allow_mutations": False,
                "force_abstain": True,
                "required_tests": [
                    "replay_proven_chain_to_terminal_media",
                    "validate_media_signature_duration_and_identity",
                ],
            },
        )
        self.assertNotIn("required_tests", payload["mutation_policy"])
        self.assertTrue(payload["verification_owned_by_brain"])

if __name__ == "__main__":
    unittest.main()
