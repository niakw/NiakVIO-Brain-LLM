"""Verify actual advisor boundary never recycles executed-negative experiments.

The representative rows mirror the Learning 42499436716 contract: a high-
confidence route prior with no verified media. They are contract observations,
not claims of playable streams or provider repairs.
"""
from __future__ import annotations

import json
import unittest

from niakvio_brain_llm.advisor_experiments import (
    DEFAULTS,
    _generic_variants,
    _targeted_variants,
    experiment_fingerprint,
    failed_advisor_fingerprints,
)
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import BrainPlanner


STRATEGY = "search_detail_player_terminal_traversal"
MODEL_EXPERIMENT = {
    **DEFAULTS["search-detail-player-terminal-traversal"],
    "role_order": list(DEFAULTS["search-detail-player-terminal-traversal"]["role_order"]),
}


class ReplayBackend:
    def __init__(self, experiment=MODEL_EXPERIMENT):
        self.experiment = experiment
        self.calls = 0
        self.max_tokens = 256

    def complete(self, *, system, user, response_schema=None):
        self.calls += 1
        assert response_schema["properties"]["provider_id"]["const"] == "4khdhub"
        assert response_schema["properties"]["strategy"]["const"] == STRATEGY
        return json.dumps({
            "provider_id": "4khdhub",
            "strategy": STRATEGY,
            "confidence": 0.96,
            "target_layer": "provider",
            "experiment": self.experiment,
            "abstain": False,
            "abstain_reason": "",
        })


def request(history):
    return RepairRequest(
        provider_id="4khdhub",
        failure_class="route_proven_gap",
        status="ROUTE PROVEN",
        advisor_only=True,
        provider_context={"advisor_experiment_history": history},
    )


def negative(experiment, *, executed=True):
    return {
        "llmAdvisorExperimentFingerprint": experiment_fingerprint(experiment),
        "consecutiveFailures": 3,
        "failures": 3,
        "successes": 0,
        "lastOutcome": "rejected",
        "lastReason": "required_category_playable_proof:movie,tv",
        "executionObserved": executed,
    }


class RuntimeNegativeNoveltyTests(unittest.TestCase):
    def test_replayed_executed_negative_is_replaced_before_reservation(self):
        bad = negative(MODEL_EXPERIMENT)
        backend = ReplayBackend()
        req = request([bad])
        proposal = BrainPlanner(backend).plan(req)
        self.assertFalse(proposal.abstain)
        self.assertEqual(backend.calls, 1)
        self.assertEqual(proposal.target_layer, "provider")
        self.assertEqual(proposal.strategy, STRATEGY)
        self.assertEqual(proposal.mutations, [])
        self.assertNotEqual(
            experiment_fingerprint(proposal.experiment),
            experiment_fingerprint(MODEL_EXPERIMENT),
        )
        self.assertNotIn(experiment_fingerprint(proposal.experiment), failed_advisor_fingerprints(req))
        self.assertTrue(proposal.tests)
        self.assertTrue(all(key in proposal.experiment for key in MODEL_EXPERIMENT))

    def test_fresh_model_hypothesis_remains_untouched(self):
        backend = ReplayBackend()
        proposal = BrainPlanner(backend).plan(request([]))
        self.assertFalse(proposal.abstain)
        self.assertEqual(proposal.experiment, MODEL_EXPERIMENT)

    def test_unexecuted_negative_does_not_block_a_new_hypothesis(self):
        row = negative(MODEL_EXPERIMENT, executed=False)
        proposal = BrainPlanner(ReplayBackend()).plan(request([row]))
        self.assertFalse(proposal.abstain)
        self.assertEqual(proposal.experiment, MODEL_EXPERIMENT)

    def test_all_bounded_variants_exhausted_abstains_instead_of_repeating(self):
        history = [
            negative(experiment)
            for experiment in [MODEL_EXPERIMENT, *_targeted_variants(MODEL_EXPERIMENT, "playable"), *_generic_variants(MODEL_EXPERIMENT)]
        ]
        req = request(history)
        proposal = BrainPlanner(ReplayBackend()).plan(req)
        self.assertTrue(proposal.abstain)
        self.assertEqual(proposal.experiment, {})
        self.assertEqual(proposal.mutations, [])
        self.assertIn("new current causal evidence", proposal.abstain_reason)

    def test_incomplete_model_experiment_with_negatives_fails_closed(self):
        backend = ReplayBackend(experiment={})
        with self.assertRaisesRegex(ValueError, "complete bounded schema"):
            BrainPlanner(backend).plan(request([negative(MODEL_EXPERIMENT)]))


if __name__ == "__main__":
    unittest.main()
