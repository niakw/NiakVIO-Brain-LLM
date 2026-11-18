"""Exact current playable preflight outranks stale provider-repair census labels."""
import copy
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.live_context_ingest import attach_live_runtime_evidence
from niakvio_brain_llm.live_evidence import current_baseline_requires_proof_refresh
from niakvio_brain_llm.policy import build_mutation_policy
from niakvio_brain_llm.priors import build_causal_prior


SHA = "a" * 40


def live_fixture():
    return {
        "provider": "demo",
        "sourceSha": SHA,
        "preflight_status": "healthy",
        "preflight_playable": 2,
        "preflight_identity_contradictions": 0,
        "fixture_selection_complete": True,
        "fixture_evidence": [
            {
                "fixture": "Movie",
                "category": "movie",
                "status": "healthy",
                "streamsReturned": 1,
                "streamsPlayable": 1,
                "decodedMediaControls": 0,
            },
            {
                "fixture": "Show S01E01",
                "category": "tv",
                "status": "healthy",
                "streamsReturned": 1,
                "streamsPlayable": 1,
                "decodedMediaControls": 0,
            },
        ],
        "network_evidence": [
            {"fixture": "Movie", "stage": "media", "status": 206},
            {"fixture": "Show S01E01", "stage": "media", "status": 206},
        ],
        "publicationAuthority": False,
    }


class LivePlayableProofRefreshTests(unittest.TestCase):
    def request(self):
        return RepairRequest(
            provider_id="demo",
            status="REGRESSION PROVIDER JS",
            failure_class="chain_terminal_gap",
            allowed_mutations=["provider_bloc", "provider_js"],
            provider_context={
                "runtimeMutationSource": "function getStreams(){return [];}",
                "authored_module": "export function getStreams(){return [];}",
            },
        )

    def test_reachable_is_live_transport_evidence_not_playback_proof(self):
        live = live_fixture()
        live["preflight_status"] = "reachable"
        live["preflight_playable"] = 0
        live["fixture_evidence"][0]["streamsReturned"] = 0
        live["fixture_evidence"][0]["streamsPlayable"] = 0
        request = self.request()
        result = attach_live_runtime_evidence(
            request, live, source_sha=SHA,
            explicit_providers=["demo"], repair_mode=True,
        )
        self.assertTrue(result["fixture_selection_complete"])
        self.assertEqual(request.provider_context["live_runtime_evidence"]["preflight_status"], "reachable")
        self.assertEqual(request.failure_class, "chain_terminal_gap")
        self.assertNotEqual(request.failure_class, "proof_freshness_gap")

    def test_missing_live_fixture_completeness_cannot_authorize_repair_context(self):
        for variant in ("missing", None, "true", 1, False):
            with self.subTest(variant=variant):
                live = live_fixture()
                if variant == "missing":
                    live.pop("fixture_selection_complete")
                else:
                    live["fixture_selection_complete"] = variant
                request = self.request()
                with self.assertRaisesRegex(ValueError, "fixture set is incomplete"):
                    attach_live_runtime_evidence(
                        request, live, source_sha=SHA,
                        explicit_providers=["demo"], repair_mode=True,
                    )
                self.assertNotIn("live_runtime_evidence", request.provider_context)

    def test_complete_current_playable_baseline_routes_to_core_proof_refresh(self):
        request = self.request()
        metrics = attach_live_runtime_evidence(
            request, live_fixture(), source_sha=SHA,
            explicit_providers=["demo"], repair_mode=True,
        )
        self.assertEqual(request.failure_class, "proof_freshness_gap")
        self.assertEqual(metrics["fixture_count"], 2)
        self.assertFalse(metrics["historical_prior_overridden"])
        prior = build_causal_prior(request, [])
        self.assertEqual(prior["target_layer"], "core")
        policy = build_mutation_policy(request, prior)
        self.assertFalse(policy["allow_mutations"])
        self.assertTrue(policy["force_abstain"])
        self.assertEqual(policy["allowed_scopes"], [])

    def test_any_current_fixture_without_playable_media_keeps_provider_gap(self):
        for mutate in (
            lambda live: live["fixture_evidence"][1].update(
                streamsReturned=0, streamsPlayable=0
            ),
            lambda live: live.update(preflight_playable=1),
            lambda live: live.update(preflight_status="no_streams"),
            lambda live: live.update(preflight_identity_contradictions=1),
            lambda live: live.update(fixture_selection_complete=False),
        ):
            live = live_fixture()
            mutate(live)
            request = self.request()
            if live["fixture_selection_complete"] is False:
                with self.assertRaisesRegex(ValueError, "fixture set is incomplete"):
                    attach_live_runtime_evidence(
                        request, live, source_sha=SHA,
                        explicit_providers=["demo"], repair_mode=True,
                    )
                continue
            attach_live_runtime_evidence(
                request, live, source_sha=SHA,
                explicit_providers=["demo"], repair_mode=True,
            )
            self.assertEqual(request.failure_class, "chain_terminal_gap")

    def test_helper_fails_closed_on_unobserved_or_malformed_counts(self):
        live = live_fixture()
        self.assertTrue(current_baseline_requires_proof_refresh(live))
        for malformed in (
            {"streamsReturned": "1", "streamsPlayable": 1},
            {"streamsReturned": 1, "streamsPlayable": True},
            {"streamsReturned": 1, "streamsPlayable": 2},
        ):
            candidate = copy.deepcopy(live)
            candidate["fixture_evidence"][0].update(malformed)
            self.assertFalse(current_baseline_requires_proof_refresh(candidate))


if __name__ == "__main__":
    unittest.main()
