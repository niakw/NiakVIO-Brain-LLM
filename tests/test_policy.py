import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.policy import build_mutation_policy

class PolicyTests(unittest.TestCase):
    def test_api_discovery_without_fresh_candidate_must_not_patch(self):
        request = RepairRequest(
            provider_id="movix",
            failure_class="api_discovery_gap",
            provider_context={"override": "{}"},
            observations=[{"signal": "fixed endpoint 403"}],
        )
        policy = build_mutation_policy(request, {
            "target_layer": "provider",
            "strategy_prior": "discover_api_from_current_page_and_bundles",
        })
        self.assertFalse(policy["allow_mutations"])
        self.assertTrue(policy["force_abstain"])

    def test_api_discovery_with_fresh_candidate_can_patch_data(self):
        request = RepairRequest(
            provider_id="movix",
            failure_class="api_discovery_gap",
            provider_context={"override": "{}"},
            observations=[{
                "source": "current_bundle_probe",
                "candidate_api_url": "https://api.movix.fun",
            }],
        )
        policy = build_mutation_policy(request, {
            "target_layer": "provider",
            "strategy_prior": "discover_api_from_current_page_and_bundles",
        })
        self.assertTrue(policy["allow_mutations"])
        self.assertEqual(policy["allowed_scopes"], ["provider_data"])

    def test_candidate_replay_never_mutates(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="candidate_replay_gap",
            provider_context={"override": "{}", "authored_module": "code"},
        )
        policy = build_mutation_policy(request, {
            "target_layer": "provider",
            "strategy_prior": "same_provider_candidate_program_replay",
        })
        self.assertFalse(policy["allow_mutations"])
        self.assertFalse(policy["force_abstain"])

if __name__ == "__main__":
    unittest.main()
