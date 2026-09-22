import unittest

from niakvio_brain_llm.verification_plan import recommended_tests

class VerificationPlanTests(unittest.TestCase):
    def test_api_discovery_requires_fresh_evidence_then_replay(self):
        tests = recommended_tests(
            "discover_api_from_current_page_and_bundles",
            target_layer="provider",
            mutation_policy={"force_abstain": True},
        )
        self.assertEqual(tests[0], "collect_required_current_evidence")
        self.assertIn("validate_discovered_provider_owned_api", tests)

    def test_unknown_provider_strategy_has_safe_fallback(self):
        tests = recommended_tests(
            "new_provider_strategy",
            target_layer="provider",
            mutation_policy={},
        )
        self.assertIn("validate_playback_identity_and_non_regression", tests)

if __name__ == "__main__":
    unittest.main()
