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
                    "scripts/provider_patches/demo_runtime_v1.py": "HEAD\nfunction resolve(){var media=null; if(!media)return null;}\n" + ("A" * 10000) + "\nvar tailValue=1;\nTAIL",
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
        windows = payload["mutation_target"]["source_windows"]
        self.assertLessEqual(sum(len(row["source"]) for row in windows), 2600)
        joined = "\n".join(row["source"] for row in windows)
        self.assertIn("HEAD", joined)
        self.assertIn("function resolve()", joined)
        self.assertTrue(payload["output_contract"]["source_windows_are_exact_current_bytes"])
        self.assertEqual(len(payload["current_observations"]), 2)
        self.assertNotIn("retrieved_experiences", payload)
        self.assertNotIn("retrieved_documents", payload)
        self.assertNotIn("published_bundle", payload)
        self.assertEqual(payload["output_contract"]["file_edit_format"], "unit_id_replace")
        self.assertTrue(payload["output_contract"]["unit_id_selects_exact_current_bytes"])
        self.assertTrue(payload["output_contract"]["model_never_copies_find_bytes"])
        self.assertTrue(payload["output_contract"]["brain_resolves_window_occurrence_by_causal_focus"])
        self.assertTrue(payload["output_contract"]["brain_resolves_global_anchor_uniqueness"])
        self.assertEqual([row["id"] for row in windows], [f"w{i}" for i in range(1, len(windows) + 1)])
        self.assertTrue(all(isinstance(row.get("focus_offset"), int) for row in windows))
        source = request.provider_context["registered_patch_sources"]["scripts/provider_patches/demo_runtime_v1.py"]
        self.assertTrue(all(row["source"] == source[row["offset"]:row["end_offset"]] for row in windows))
        units = payload["mutation_target"]["editable_units"]
        self.assertTrue(units)
        self.assertTrue(all(row["source"] == source[row["offset"]:row["end_offset"]] for row in units))
        self.assertTrue(all(len(row["source"]) <= 700 for row in units))
        self.assertTrue(any(row.get("kind") == "statement_sequence" for row in units))
        self.assertTrue(any(row["source"].count(";") >= 2 for row in units if row.get("kind") == "statement_sequence"))
        self.assertTrue(all(row["window_id"] in {window["id"] for window in windows} for row in units))


    def test_force_edit_units_include_bounded_causal_function(self):
        source = (
            "function noise(){return 1;} "
            "function confirmLinks(page){var raw=page.url;if(!raw)return [];return [raw];} "
            "function unrelated(){return 2;}"
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        units = payload["mutation_target"]["editable_units"]
        causal = [row for row in units if row.get("kind") == "function_unit"]
        self.assertTrue(causal)
        self.assertIn("function confirmLinks", causal[0]["source"])
        self.assertNotIn("function unrelated", causal[0]["source"])
        self.assertLessEqual(len(causal[0]["source"]), 1800)

    def test_force_validation_retry_uses_focused_context(self):
        source = (
            "H" * 5000
            + "\nfunction confirmLink(){ return '/confirm/' + id; }\n"
            + "I" * 2200
            + "\nfunction internalLink(){ return '/internal/' + id; }\n"
            + "J" * 2200
            + "\nfunction resolveMedia(){ return url.includes('.m3u8') ? url : null; }\n"
            + "T" * 5000
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            observations=[
                {
                    "stage": "force_validation_feedback",
                    "reason": "syntax_error",
                    "correction_index": 1,
                    "instruction": "previous edit rejected",
                },
                {"stage": "player", "blob": "Z" * 5000},
                {"stage": "detail", "blob": "Y" * 5000},
            ],
            census_prior={"blob": "C" * 5000},
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
                "validated_reference_patterns": [
                    {
                        "provider": "healthy",
                        "status": "FULL OK",
                        "source_kind": "registered_bloc:x",
                        "technical_features": ["fetch", "iframe", "m3u8"],
                        "snippet": "S" * 1100,
                    }
                ],
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        windows = payload["mutation_target"]["source_windows"]
        self.assertLessEqual(sum(len(row["source"]) for row in windows), 2200)
        self.assertLessEqual(len(windows), 2)
        self.assertEqual(len(payload["current_observations"]), 1)
        self.assertEqual(payload["current_observations"][0]["stage"], "force_validation_feedback")
        self.assertEqual(payload["validated_reference_patterns"], [])
        self.assertEqual(payload["census_prior"], {})
        self.assertEqual(payload["output_contract"]["validation_retry_context"], "focused")

    def test_force_prompt_targets_family_relevant_middle_windows(self):
        source = (
            "H" * 5000
            + "\nfunction confirmLink(){ return '/confirm/' + id; }\n"
            + "I" * 2200
            + "\nfunction internalLink(){ return '/internal/' + id; }\n"
            + "J" * 2200
            + "\nfunction resolveMedia(){ return url.includes('.m3u8') ? url : null; }\n"
            + "T" * 5000
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        windows = payload["mutation_target"]["source_windows"]
        joined = "\n".join(row["source"] for row in windows)
        self.assertLessEqual(sum(len(row["source"]) for row in windows), 2600)
        self.assertIn("confirmLink", joined)
        self.assertIn("internalLink", joined)
        self.assertIn("resolveMedia", joined)
        self.assertTrue(all("...<middle-clipped>..." not in row["source"] for row in windows))

    def test_force_initial_prompt_is_compact_and_keeps_one_optional_reference(self):
        source = (
            "H" * 5000
            + "\nfunction confirmLink(){ return '/confirm/' + id; }\n"
            + "I" * 2200
            + "\nfunction resolveMedia(){ return url.includes('.m3u8') ? url : null; }\n"
            + "T" * 5000
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            observations=[
                {"stage": "player", "blob": "Z" * 5000},
                {"stage": "detail", "blob": "Y" * 5000},
                {"stage": "other", "blob": "X" * 5000},
            ],
            census_prior={"blob": "C" * 5000},
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": source,
                },
                "validated_reference_patterns": [
                    {
                        "provider": "healthy-a",
                        "status": "FULL OK",
                        "source_kind": "registered_bloc:a",
                        "technical_features": ["fetch", "iframe", "m3u8"],
                        "snippet": "S" * 1100,
                    },
                    {
                        "provider": "healthy-b",
                        "status": "FULL OK",
                        "source_kind": "registered_bloc:b",
                        "technical_features": ["fetch", "json"],
                        "snippet": "R" * 1100,
                    },
                ],
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        windows = payload["mutation_target"]["source_windows"]
        self.assertLessEqual(sum(len(row["source"]) for row in windows), 2600)
        self.assertLessEqual(len(windows), 3)
        self.assertEqual(len(payload["current_observations"]), 2)
        self.assertEqual(len(payload["validated_reference_patterns"]), 1)
        self.assertLessEqual(len(payload["validated_reference_patterns"][0]["snippet"]), 520)
        self.assertEqual(payload["census_prior"], {})
        self.assertEqual(payload["output_contract"]["validation_retry_context"], "compact_initial")

    def test_force_prompt_references_are_optional_and_novelty_allowed(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={
                "runtimeMutationFilename": "providers/demo.js",
                "runtimeMutationSource": "function resolve(){return null;}",
                "validated_reference_patterns": [{
                    "provider": "healthy",
                    "status": "FULL OK",
                    "source_kind": "registered_bloc:x",
                    "technical_features": ["fetch", "iframe", "m3u8"],
                    "snippet": "async function resolvePlayer(){return '<ROUTE>';}",
                    "proof_authority": False,
                    "copy_policy": "pattern_reference_only",
                    "novelty_allowed": True,
                }],
            },
        )
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "chain_terminal_extractor_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        self.assertEqual(len(payload["validated_reference_patterns"]), 1)
        self.assertTrue(payload["reference_policy"]["may_adapt_combine_or_ignore"])
        self.assertTrue(payload["reference_policy"]["novel_provider_local_mechanisms_allowed"])
        self.assertTrue(payload["reference_policy"]["reference_is_not_proof"])

    def test_force_prompt_preserves_all_allowed_mutation_scopes(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": "const x = 1;",
                },
                "runtimeMutationFilename": "providers/demo.js",
                "runtimeMutationSource": "function resolve(){ return 1; }",
            },
        )
        scopes = ["provider_bloc", "provider_data", "provider_js", "provider_patch"]
        payload = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "proven_route_terminal_traversal_v1"},
            {"allow_mutations": True, "allowed_scopes": scopes},
        )
        self.assertEqual(payload["mutation_policy"]["allowed_scopes"], scopes)
        self.assertEqual(payload["mutation_target"]["scope"], "provider_patch")
        self.assertEqual(payload["new_bloc_target"]["scope"], "provider_bloc")

        patch_only = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "proven_route_terminal_traversal_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"]},
        )
        self.assertEqual(patch_only["mutation_target"]["scope"], "provider_patch")
        self.assertEqual(patch_only["new_bloc_target"], {})

        bloc_only = build_force_prompt_payload(
            request,
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "proven_route_terminal_traversal_v1"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        self.assertEqual(bloc_only["mutation_target"], {})
        self.assertEqual(bloc_only["new_bloc_target"]["scope"], "provider_bloc")

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
