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
