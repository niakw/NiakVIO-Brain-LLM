import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.retrieval import ExperienceStore
from niakvio_brain_llm.routing import route_request


class RoutingTests(unittest.TestCase):
    def test_full_ok_without_failure_skips_llm(self):
        decision = route_request(
            RepairRequest(provider_id="demo", failure_class="healthy", status="FULL OK")
        )
        self.assertEqual(decision.mode, "skip")
        self.assertFalse(decision.requires_llm)

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

    def test_unknown_failure_uses_llm_diagnosis_without_mutations(self):
        decision = route_request(
            RepairRequest(provider_id="demo", failure_class="novel_unknown_failure")
        )
        self.assertEqual(decision.mode, "llm_diagnose")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, [])


if __name__ == "__main__":
    unittest.main()
