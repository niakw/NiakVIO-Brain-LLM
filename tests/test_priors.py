import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.priors import build_causal_prior

class PriorTests(unittest.TestCase):
    def test_exact_provider_history_becomes_provider_prior(self):
        prior = build_causal_prior(
            RepairRequest(provider_id="movix", failure_class="api_discovery_gap"),
            [{
                "experience_id": "hist-movix",
                "failure_class": "api_discovery_gap",
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

if __name__ == "__main__":
    unittest.main()
