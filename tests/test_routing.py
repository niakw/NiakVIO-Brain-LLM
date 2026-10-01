import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.repair_family import repair_family_descriptor
from niakvio_brain_llm.retrieval import ExperienceStore
from niakvio_brain_llm.routing import route_request


class RoutingTests(unittest.TestCase):
    def test_full_ok_without_failure_skips_llm(self):
        decision = route_request(
            RepairRequest(provider_id="demo", failure_class="healthy", status="FULL OK")
        )
        self.assertEqual(decision.mode, "skip")
        self.assertFalse(decision.requires_llm)

    def test_full_ok_variant_coverage_gap_routes_provider_synthesis(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="variant_coverage_gap",
                status="FULL OK",
                allowed_mutations=["provider_bloc"],
                provider_context={
                    "runtimeMutationSource": (
                        "function resolve(links){var out=[];"
                        "for(var i=0;i<links.length;i++){if(out.length>=4)break}"
                        "return out}"
                    ),
                    "runtime_variant_coverage": {
                        "riskKind": "variant-coverage-truncation",
                        "risk": "high",
                    },
                },
            )
        )
        self.assertEqual(decision.mode, "llm_repair")
        self.assertEqual(decision.target_layer, "provider")
        self.assertEqual(decision.strategy, "enumerate_stream_variants_before_global_cap")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, ["provider_bloc"])

    def test_harness_failure_is_deterministic(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="transport_environment_gap",
                status="HARNESS MISMATCH",
            )
        )
        self.assertEqual(decision.mode, "deterministic")
        self.assertEqual(decision.target_layer, "harness")
        self.assertFalse(decision.requires_llm)

    def test_confirmed_cross_network_browser_native_gap_uses_llm_architecture_diagnosis(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="transport_environment_gap",
                status="CLIENT TRANSPORT GAP",
                census_prior={"harnessTransportClass": "browser-profile-only-both-networks"},
            )
        )
        self.assertEqual(decision.mode, "llm_diagnose")
        self.assertEqual(decision.target_layer, "harness")
        self.assertEqual(decision.strategy, "native_tls_browser_differential_v1")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, [])

    def test_legacy_harness_mismatch_with_confirmed_differential_also_uses_llm(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="transport_environment_gap",
                status="HARNESS MISMATCH",
                census_prior={"harnessTransportClass": "browser-profile-only-both-networks"},
            )
        )
        self.assertEqual(decision.mode, "llm_diagnose")
        self.assertTrue(decision.requires_llm)

    def test_api_discovery_without_fresh_url_probes_first(self):
        store = ExperienceStore([{
            "experience_id": "movix",
            "failure_class": "api_discovery_gap",
            "providers": ["movix"],
            "strategy": "discover_api_from_current_page_and_bundles",
        }])
        decision = route_request(
            RepairRequest(
                provider_id="movix",
                failure_class="api_discovery_gap",
                status="NO PROOF",
                provider_context={"override": "{}"},
                observations=[{"signal": "fixed endpoint 403"}],
            ),
            store,
        )
        self.assertEqual(decision.mode, "probe")
        self.assertFalse(decision.requires_llm)

    def test_no_proof_provider_transport_requires_recognition_before_llm(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="provider_transport_gap",
                status="NO PROOF",
                allowed_mutations=["provider_patch", "provider_bloc"],
                provider_context={
                    "route_contract": {
                        "synthesisPolicy": {
                            "mode": "rediscover_by_traversal",
                            "runtimeSynthesisAllowed": False,
                        }
                    },
                    "runtimeMutationSource": "function resolve(){return [];}",
                },
            )
        )
        self.assertEqual(decision.mode, "probe")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, [])
        self.assertEqual(decision.strategy, "rediscover_current_provider_route_by_traversal")
        self.assertIn("persist newly proven route DATA", decision.next_actions)

    def test_rediscovery_policy_blocks_llm_even_if_status_is_not_no_proof(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="provider_transport_gap",
                status="ROUTE PROVEN",
                allowed_mutations=["provider_bloc"],
                provider_context={
                    "route_contract": {
                        "synthesisPolicy": {
                            "mode": "rediscover_by_traversal",
                            "runtimeSynthesisAllowed": False,
                        }
                    },
                    "runtimeMutationSource": "function resolve(){return [];}",
                },
            )
        )
        self.assertEqual(decision.mode, "probe")
        self.assertFalse(decision.requires_llm)

    def test_provider_patch_with_fresh_evidence_uses_llm(self):
        store = ExperienceStore([{
            "experience_id": "movix",
            "failure_class": "api_discovery_gap",
            "providers": ["movix"],
            "strategy": "discover_api_from_current_page_and_bundles",
        }])
        decision = route_request(
            RepairRequest(
                provider_id="movix",
                failure_class="api_discovery_gap",
                provider_context={"override": "{}"},
                observations=[{
                    "source": "current_bundle_probe",
                    "candidate_api_url": "https://api.movix.fun",
                }],
            ),
            store,
        )
        self.assertEqual(decision.mode, "llm_repair")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, ["provider_data"])

    def test_advisor_only_high_confidence_provider_strategy_is_deterministic(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="route_proven_gap",
                status="ROUTE PROVEN",
                advisor_only=True,
            )
        )
        self.assertEqual(decision.mode, "deterministic_advisor")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.target_layer, "provider")
        self.assertEqual(decision.strategy, "search_detail_player_terminal_traversal")
        self.assertEqual(decision.allowed_mutations, [])

    def test_advisor_only_failed_current_strategy_rotates_without_llm(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="route_proven_gap",
                status="ROUTE PROVEN",
                advisor_only=True,
                provider_context={
                    "advisor_experiment_history": [{
                        "profile": "proven_route_terminal_traversal_v1",
                        "llmAdvisorExperimentFingerprint": "a" * 64,
                        "consecutiveFailures": 2,
                        "lastOutcome": "rejected",
                    }],
                },
            )
        )
        self.assertEqual(decision.mode, "deterministic_advisor")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.strategy, "search_detail_player_terminal_traversal")
        self.assertEqual(decision.allowed_mutations, [])

    def test_advisor_only_candidate_replay_gets_bounded_experiment(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="candidate_replay_gap",
                status="CANDIDATE OK",
                advisor_only=True,
            )
        )
        self.assertEqual(decision.mode, "deterministic_advisor")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.strategy, "same_provider_candidate_program_replay")

    def test_validated_same_family_routes_before_llm(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            supported_types=["movie", "tv"],
            allowed_mutations=["provider_patch"],
            provider_context={
                "registered_patch_scripts":["scripts/provider_patches/demo_runtime_v1.py"],
                "registered_patch_sources":{
                    "scripts/provider_patches/demo_runtime_v1.py":"function classBlocks(html,cls){return []}"
                },
            },
            observations=[{
                "source":"targeted-regression-current",
                "value":{
                    "debugStages":{"movie":"provider_network_zero_result"},
                    "network":{"movie":[{"status":200}]},
                    "structureHints":[
                        "movie:classes=movie-card,movie-card-format;"
                        "classFacts=[movie-card;count=12;selfHref=1;nestedAnchors=24;"
                        "tags=a,div,span;signals=movie,series,year]"
                    ],
                },
            }],
        )
        family = repair_family_descriptor(request)
        store = ExperienceStore([{
            "experience_id":"family-1",
            "failure_class":"route_proven_gap",
            "result":"validated",
            "repair_family":family,
            "mechanismFamily":"balanced-class-container",
            "strategy":"balanced-class-container",
            "successCount":3,
            "failureCount":0,
        }])
        decision = route_request(request, store)
        self.assertEqual(decision.mode, "family_replay")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.strategy, "balanced-class-container")
        self.assertEqual(decision.allowed_mutations, ["provider_patch"])

    def test_clean_residential_replay_routes_provider_gap_to_llm_repair(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="route_proven_gap",
                status="ROUTE PROVEN",
                allowed_mutations=["provider_bloc"],
                provider_context={
                    "runtimeMutationSource": "function getStreams(item){return [];}",
                },
                observations=[
                    {
                        "source": "census_current",
                        "value": {"status": "ROUTE PROVEN"},
                    },
                    {
                        "source": "targeted-regression-current",
                        "value": {
                            "debugStages": {"movie": "provider_waf_challenge"},
                            "network": {"movie": [{"host": "provider.example", "status": 403}]},
                        },
                    },
                    {
                        "source": "waf-client-differential-current",
                        "value": {
                            "residentialReplay": [{
                                "status": "no_streams",
                                "debugStage": "provider_zero_before_provider_network",
                                "contradictions": 0,
                                "identitySafe": True,
                            }],
                        },
                    },
                ],
            )
        )
        self.assertEqual(decision.target_layer, "provider")
        self.assertEqual(decision.mode, "llm_repair")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, ["provider_bloc"])

    def test_unknown_failure_uses_llm_diagnosis_without_mutations(self):
        decision = route_request(
            RepairRequest(provider_id="demo", failure_class="novel_unknown_failure")
        )
        self.assertEqual(decision.mode, "llm_diagnose")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, [])


if __name__ == "__main__":
    unittest.main()
