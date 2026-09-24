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

    def test_advisor_only_high_confidence_prior_synthesizes_without_llm(self):
        planner = BrainPlanner(ExplodingBackend())
        outcome = BrainOrchestrator(planner).run(
            RepairRequest(
                provider_id="demo",
                failure_class="route_proven_gap",
                status="ROUTE PROVEN",
                advisor_only=True,
            )
        )
        self.assertEqual(outcome.routing.mode, "deterministic_advisor")
        self.assertIsNotNone(outcome.proposal)
        self.assertEqual(
            outcome.proposal.strategy,
            "search_detail_player_terminal_traversal",
        )
        self.assertEqual(outcome.proposal.mutations, [])
        self.assertTrue(outcome.proposal.experiment)
        self.assertIn("route_policy", outcome.proposal.experiment)

    def test_advisor_negative_memory_rotates_to_new_experiment_without_llm(self):
        from niakvio_brain_llm.advisor_experiments import experiment_fingerprint, next_advisor_experiment

        initial = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            advisor_only=True,
        )
        first = next_advisor_experiment(initial, "search_detail_player_terminal_traversal")
        first_fp = experiment_fingerprint(first)
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            advisor_only=True,
            census_prior={"dominantIssue": "provider_waf_challenge"},
            provider_context={
                "advisor_experiment_history": [{
                    "profile": "proven_route_terminal_traversal_v1",
                    "llmAdvisorExperimentFingerprint": first_fp,
                    "consecutiveFailures": 1,
                    "lastOutcome": "rejected",
                    "lastReason": "provider_waf_challenge",
                }],
            },
        )
        planner = BrainPlanner(ExplodingBackend())
        outcome = BrainOrchestrator(planner).run(request)
        self.assertEqual(outcome.routing.mode, "deterministic_advisor")
        self.assertNotEqual(experiment_fingerprint(outcome.proposal.experiment), first_fp)
        self.assertTrue(outcome.proposal.experiment["session_bootstrap"])

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
