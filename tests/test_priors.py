import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.priors import build_causal_prior, taxonomy_layer

class PriorTests(unittest.TestCase):
    def test_exact_provider_history_becomes_provider_prior(self):
        prior = build_causal_prior(
            RepairRequest(provider_id="movix", failure_class="provider_specific_gap"),
            [{
                "experience_id": "hist-movix",
                "failure_class": "provider_specific_gap",
                "providers": ["movix"],
                "strategy": "discover_api",
            }],
        )
        self.assertEqual(prior["target_layer"], "provider")
        self.assertGreater(prior["confidence"], 0.9)

    def test_harness_status_overrides_provider_history(self):
        prior = build_causal_prior(
            RepairRequest(
                provider_id="demo",
                failure_class="api_discovery_gap",
                status="HARNESS MISMATCH",
            ),
            [{
                "failure_class": "api_discovery_gap",
                "providers": ["demo"],
            }],
        )
        self.assertEqual(prior["target_layer"], "harness")

    def test_harness_status_keeps_compatible_canonical_strategy(self):
        prior = build_causal_prior(
            RepairRequest(
                provider_id="demo",
                failure_class="transport_environment_gap",
                status="HARNESS/ENV BLOCKED",
            ),
            [],
        )
        self.assertEqual(prior["target_layer"], "harness")
        self.assertEqual(
            prior["strategy_prior"],
            "compare_browser_native_residential_profiles_without_provider_mutation",
        )

    def test_harness_status_drops_incompatible_provider_strategy(self):
        prior = build_causal_prior(
            RepairRequest(
                provider_id="demo",
                failure_class="api_discovery_gap",
                status="HARNESS MISMATCH",
            ),
            [],
        )
        self.assertEqual(prior["target_layer"], "harness")
        self.assertNotIn("strategy_prior", prior)

    def test_client_transport_gap_uses_specific_architecture_strategy(self):
        prior = build_causal_prior(
            RepairRequest(
                provider_id="demo",
                failure_class="transport_environment_gap",
                status="CLIENT TRANSPORT GAP",
                census_prior={"harnessTransportClass": "browser-profile-only-both-networks"},
            ),
            [],
        )
        self.assertEqual(prior["target_layer"], "harness")
        self.assertEqual(prior["strategy_prior"], "native_tls_browser_differential_v1")
        self.assertGreaterEqual(prior["confidence"], 0.99)

    def test_targeted_interactive_challenge_overrides_provider_transport_taxonomy(self):
        prior = build_causal_prior(
            RepairRequest(
                provider_id="demo",
                failure_class="provider_transport_gap",
                status="CHAIN REACHED",
                observations=[{
                    "source": "targeted-regression-current",
                    "value": {
                        "debugStages": {"movie": "provider_waf_challenge"},
                        "network": {"movie": [{"host": "provider.example", "status": 200}]},
                    },
                }],
            ),
            [],
        )
        self.assertEqual(prior["target_layer"], "harness")
        self.assertEqual(prior["source"], "targeted_interactive_challenge")
        self.assertEqual(
            prior["strategy_prior"],
            "compare_browser_native_residential_profiles_without_provider_mutation",
        )
        self.assertGreaterEqual(prior["confidence"], 0.99)

    def test_residential_provider_replay_outranks_targeted_waf_prior(self):
        prior = build_causal_prior(
            RepairRequest(
                provider_id="demo",
                failure_class="route_proven_gap",
                status="ROUTE PROVEN",
                observations=[
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
                                "lane": "movie",
                                "status": "no_streams",
                                "debugStage": "provider_zero_before_provider_network",
                                "raw": 0,
                                "playable": 0,
                                "verified": 0,
                                "contradictions": 0,
                                "identitySafe": True,
                            }],
                        },
                    },
                ],
            ),
            [],
        )
        self.assertEqual(prior["target_layer"], "provider")
        self.assertEqual(prior["source"], "failure_class_taxonomy")
        self.assertEqual(prior["strategy_prior"], "search_detail_player_terminal_traversal")

    def test_chain_replay_outranks_targeted_waf_prior(self):
        prior = build_causal_prior(
            RepairRequest(
                provider_id="demo",
                failure_class="chain_terminal_gap",
                status="CHAIN REACHED",
                observations=[
                    {
                        "source": "targeted-regression-current",
                        "value": {"debugStages": {"movie": "provider_waf_challenge"}},
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
            ),
            [],
        )
        self.assertEqual(prior["target_layer"], "provider")
        self.assertEqual(prior["strategy_prior"], "terminal_media_extractor_with_playback_validation")

    def test_chain_terminal_taxonomy_is_provider(self):
        prior = build_causal_prior(
            RepairRequest(provider_id="demo", failure_class="chain_terminal_gap"),
            [],
        )
        self.assertEqual(prior["target_layer"], "provider")
        self.assertGreaterEqual(prior["confidence"], 0.95)

    def test_pre_network_gate_taxonomy_is_core(self):
        prior = build_causal_prior(
            RepairRequest(provider_id="global", failure_class="media_type_pre_network_gate"),
            [],
        )
        self.assertEqual(prior["target_layer"], "core")
        self.assertGreaterEqual(prior["confidence"], 0.95)

    def test_historical_core_classes_are_normalized(self):
        for failure in (
            "playback_identity_gap",
            "runtime_compatibility_gap",
            "provider_identity_collision",
            "provider_reconstruction_integrity",
            "media_validation_gap",
            "runtime_timeout_gap",
            "structured_parse_gap",
            "state_authority_gap",
            "activation_proof_gap",
            "proof_freshness_gap",
        ):
            with self.subTest(failure=failure):
                self.assertEqual(taxonomy_layer(failure), "core")

    def test_historical_provider_classes_are_normalized(self):
        for failure in (
            "provider_backend_isolation",
            "typed_api_execution",
            "identity_mismatch",
            "provider_transport_gap",
            "route_proven_gap",
            "chain_terminal_gap",
            "candidate_replay_gap",
            "media_extraction_gap",
        ):
            with self.subTest(failure=failure):
                self.assertEqual(taxonomy_layer(failure), "provider")

if __name__ == "__main__":
    unittest.main()
