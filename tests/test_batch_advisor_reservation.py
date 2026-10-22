from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

from niakvio_brain_llm.advisor_experiments import (
    experiment_fingerprint,
    failed_advisor_fingerprints,
    next_advisor_experiment,
)
from niakvio_brain_llm.contracts import RepairRequest


SPEC = importlib.util.spec_from_file_location(
    "batch_advisor_reservation",
    Path(__file__).resolve().parents[1] / "scripts" / "plan_batch_from_checkout.py",
)
assert SPEC and SPEC.loader
batch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(batch)


class BatchAdvisorReservationTests(unittest.TestCase):
    def request(self, history):
        return RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            advisor_only=True,
            provider_context={"advisor_experiment_history": history},
        )

    def outcome(self, experiment):
        return SimpleNamespace(proposal=SimpleNamespace(experiment=experiment))

    def test_reserving_next_candidate_preserves_all_executed_failures(self):
        history = [
            {
                "llmAdvisorExperimentFingerprint": f"{index:064x}",
                "consecutiveFailures": 1,
                "executionObserved": True,
                "lastOutcome": "rejected",
            }
            for index in range(1, 80)
        ]
        request = self.request(history)
        blocked_before = failed_advisor_fingerprints(request)
        experiment = next_advisor_experiment(request, "search_detail_player_terminal_traversal")
        self.assertTrue(batch._reserve_advisor_experiment(request, self.outcome(experiment)))
        self.assertEqual(len(request.provider_context["advisor_experiment_history"]), 80)
        self.assertTrue(blocked_before <= failed_advisor_fingerprints(request))
        self.assertFalse(batch._reserve_advisor_experiment(request, self.outcome(experiment)))
        following = next_advisor_experiment(request, "search_detail_player_terminal_traversal")
        self.assertNotEqual(experiment_fingerprint(experiment), experiment_fingerprint(following))

    def test_unexecuted_candidate_can_be_reserved_then_cannot_repeat(self):
        experiment = next_advisor_experiment(self.request([]), "search_detail_player_terminal_traversal")
        fingerprint = experiment_fingerprint(experiment)
        for row in (
            {"executionObserved": False, "lastOutcome": "rejected"},
            {"lastOutcome": "profile_unavailable"},
            {"lastOutcome": "success"},
        ):
            with self.subTest(row=row):
                request = self.request([{
                    **row,
                    "llmAdvisorExperimentFingerprint": fingerprint,
                    "consecutiveFailures": 1,
                }])
                self.assertEqual(
                    experiment_fingerprint(next_advisor_experiment(request, "search_detail_player_terminal_traversal")),
                    fingerprint,
                )
                self.assertTrue(batch._reserve_advisor_experiment(request, self.outcome(experiment)))
                self.assertFalse(batch._reserve_advisor_experiment(request, self.outcome(experiment)))

    def test_executed_and_legacy_failed_candidates_remain_blocked(self):
        experiment = next_advisor_experiment(self.request([]), "search_detail_player_terminal_traversal")
        for execution in ({"executionObserved": True}, {}):
            with self.subTest(execution=execution):
                request = self.request([{
                    **execution,
                    "llmAdvisorExperimentFingerprint": experiment_fingerprint(experiment),
                    "consecutiveFailures": 1,
                    "lastOutcome": "rejected",
                }])
                self.assertFalse(batch._reserve_advisor_experiment(request, self.outcome(experiment)))


if __name__ == "__main__":
    unittest.main()
