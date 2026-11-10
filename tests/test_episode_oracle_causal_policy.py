import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.policy import build_mutation_policy
from niakvio_brain_llm.priors import build_causal_prior
from niakvio_brain_llm.verification_plan import recommended_tests


class ReverseEngineeredEpisodeOracleRouting(unittest.TestCase):
    """No source-only oracle is permission to mutate an individual provider."""

    def test_shared_season_coordinate_loss_is_not_a_provider_patch(self):
        request = RepairRequest(
            provider_id="animevost-fr", status="ROUTE PROVEN",
            failure_class="episode-coordinate-loss",
        )
        prior = build_causal_prior(request, [])
        self.assertEqual(prior["target_layer"], "core")
        self.assertEqual(
            prior["strategy_prior"], "preserve_episodic_bindings_before_materialization"
        )
        policy = build_mutation_policy(request, prior)
        self.assertFalse(policy["allow_mutations"])
        self.assertTrue(policy["force_abstain"])
        checks = recommended_tests(
            prior["strategy_prior"], target_layer="core", mutation_policy=policy
        )
        self.assertIn(
            "verify_compiler_preserves_season_zero_and_provider_correlated_id", checks
        )
        self.assertIn(
            "replay_materialized_current_provider_bytes_against_real_terminal_media", checks
        )

    def test_foreign_subtitle_track_is_a_shared_identity_problem(self):
        request = RepairRequest(
            provider_id="demo", status="CHAIN REACHED",
            failure_class="subtitle-episode-association-gap",
        )
        prior = build_causal_prior(request, [])
        self.assertEqual(prior["target_layer"], "core")
        policy = build_mutation_policy(request, prior)
        self.assertFalse(policy["allow_mutations"])
        checks = recommended_tests(
            prior["strategy_prior"], target_layer="core", mutation_policy=policy
        )
        self.assertIn(
            "reject_explicit_foreign_episode_caption_without_dropping_valid_media",
            checks,
        )
        self.assertIn(
            "replay_real_media_and_external_subtitles_with_episode_identity",
            checks,
        )

    def test_live_empty_catalogue_is_not_a_positive_repair_oracle(self):
        # A 200 JSON response containing results=[] provides transport proof,
        # not playable episode or repaired-provider evidence.
        request = RepairRequest(
            provider_id="animevost-fr", status="ROUTE PROVEN",
            failure_class="provider-transport-gap",
            observations=[{
                "source": "current_network_probe",
                "value": {
                    "httpStatus": 200, "resultCount": 0,
                    "terminalMediaVerified": False,
                },
            }],
        )
        prior = build_causal_prior(request, [])
        self.assertEqual(prior["target_layer"], "provider")
        # No new positive repair fact is manufactured from the empty API.
        self.assertNotIn("validated_repair", prior)


if __name__ == "__main__":
    unittest.main()
