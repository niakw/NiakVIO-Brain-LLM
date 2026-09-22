import json
import unittest

from niakvio_brain_llm.backend import StaticBackend
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.orchestrator import BrainOrchestrator
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.retrieval import ExperienceStore


class ExplodingBackend:
    def complete(self, **kwargs):
        raise AssertionError("LLM must not be called on deterministic route")


class OrchestratorTests(unittest.TestCase):
    def test_deterministic_harness_path_never_calls_llm(self):
        planner = BrainPlanner(ExplodingBackend())
        outcome = BrainOrchestrator(planner).run(
            RepairRequest(
                provider_id="demo",
                failure_class="transport_environment_gap",
                status="HARNESS MISMATCH",
            )
        )
        self.assertEqual(outcome.routing.mode, "deterministic")
        self.assertIsNone(outcome.proposal)

    def test_probe_path_never_calls_llm(self):
        store = ExperienceStore([{
            "failure_class": "api_discovery_gap",
            "providers": ["movix"],
            "strategy": "discover_api_from_current_page_and_bundles",
        }])
        planner = BrainPlanner(ExplodingBackend(), store)
        outcome = BrainOrchestrator(planner, store).run(
            RepairRequest(
                provider_id="movix",
                failure_class="api_discovery_gap",
                provider_context={"override": "{}"},
                observations=[{"signal": "fixed endpoint 403"}],
            )
        )
        self.assertEqual(outcome.routing.mode, "probe")
        self.assertIsNone(outcome.proposal)

    def test_llm_repair_calls_model_only_with_routed_scope(self):
        store = ExperienceStore([{
            "failure_class": "api_discovery_gap",
            "providers": ["movix"],
            "strategy": "discover_api_from_current_page_and_bundles",
        }])
        response = json.dumps({
            "provider_id": "movix",
            "diagnosis": "current API discovered from bundle",
            "strategy": "discover_api_from_current_page_and_bundles",
            "confidence": 0.96,
            "target_layer": "provider",
            "evidence": ["current bundle probe"],
            "mutations": [{
                "scope": "provider_data",
                "operation": "set",
                "path": "candidate_api_recipe.base",
                "value": "https://api.movix.fun",
            }],
            "tests": ["replay current movie fixture"],
            "abstain": False,
            "abstain_reason": "",
        })
        planner = BrainPlanner(StaticBackend(response), store)
        outcome = BrainOrchestrator(planner, store).run(
            RepairRequest(
                provider_id="movix",
                failure_class="api_discovery_gap",
                provider_context={"override": "{}"},
                observations=[{
                    "source": "current_bundle_probe",
                    "candidate_api_url": "https://api.movix.fun",
                }],
            )
        )
        self.assertEqual(outcome.routing.mode, "llm_repair")
        self.assertIsNotNone(outcome.proposal)
        self.assertEqual(
            outcome.proposal.mutations[0]["scope"],
            "provider_data",
        )


if __name__ == "__main__":
    unittest.main()
