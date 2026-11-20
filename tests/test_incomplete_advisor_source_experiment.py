"""A novel advisor source diagnosis cannot masquerade as runnable old-profile guidance."""
import json
import unittest
from unittest.mock import patch

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import BrainPlanner


class IncompleteAdvisorBackend:
    max_tokens = 256
    def complete(self, *, system, user, response_schema=None):
        return json.dumps({
            "provider_id": "anime-sama",
            "strategy": "catalogue-inline-source-contract-discriminator",
            "confidence": 0.94,
            "target_layer": "provider",
            "experiment": {},
            "abstain": False,
            "abstain_reason": "",
        })


def request(native_parent=True):
    run, sha, digest = "44781039914", "a" * 40, "b" * 64
    tv = {
        "client": "tv", "historicalOnly": True, "appSelected": True,
        "readerEvidenceComplete": True, "nativeExtractionZeroObserved": True,
        "sourceRunId": run, "sourceNiakvioSha": sha,
        "providerArtifactSha256": digest, "fixture": "mushoku-tensei-s01e01",
        "manifestScope": "manifest.json",
        "nativeSourceScriptShapePatterns": ["script_http_missing", "script_html_2xx"],
        "proofAuthority": False, "publicationAuthority": False,
        "nativePlaybackAuthority": False, "providerMutationAuthority": False,
    }
    independent = {
        "source": "independent-ci-source-shape", "historicalOnly": True,
        "nativeParentRunId": run, "nativeParentSourceSha": sha,
        "currentProviderArtifactSha256": digest, "fixture": "mushoku-tensei-s01e01",
        "manifestScope": "manifest.json", "probeRunId": "44798438960",
        "catalogueSlugUnverified": "mushoku-tensei",
        "independentNetworkNotOfficialClient": True,
        "catalogueIdentityVerified": False,
        "episodeIdentityVerified": False, "sourceContractVerifiedOnOfficialTv": False,
        "proofAuthority": False, "publicationAuthority": False,
        "nativePlaybackAuthority": False, "providerMutationAuthority": False,
        "sourceObservations": [{
            "originHost": "anime-sama.to",
            "seasonSourceShape": "catalogue_inline_token_episode",
            "seasonPageStatus": 200, "inlineTokenSeasonObserved": True,
            "legacyScriptStatus": 403,
        }],
    }
    return RepairRequest(
        provider_id="anime-sama", failure_class="route_proven_gap",
        status="REGRESSION PROVIDER", supported_types=["anime"],
        advisor_only=True, allowed_mutations=[],
        observations=(
            ([{"source": "official-android-tv-emulator", "value": tv}]
             if native_parent else [])
            + [{"source": "independent-catalogue-source-probe", "value": independent}]
        ),
    )


class IncompleteAdvisorExperimentTests(unittest.TestCase):
    def test_native_attested_incomplete_experiment_is_hypothesis_not_repair(self):
        prior = {"target_layer": "provider", "confidence": 0.96,
                 "strategy_prior": "search-detail-player-terminal-traversal"}
        with (
            patch("niakvio_brain_llm.planner.build_causal_prior", return_value=prior),
            patch("niakvio_brain_llm.planner.failed_advisor_fingerprints", return_value={"f" * 64}),
        ):
            result = BrainPlanner(IncompleteAdvisorBackend()).plan(request())
        self.assertEqual(result.strategy, "catalogue-inline-source-contract-discriminator")
        self.assertEqual(result.target_layer, "provider")
        self.assertTrue(result.abstain)
        self.assertIn("no bounded executable experiment", result.abstain_reason)
        self.assertEqual(result.experiment, {})
        self.assertEqual(result.mutations, [])

    def test_unattested_incomplete_experiment_still_fails_closed(self):
        prior = {"target_layer": "provider", "confidence": 0.91}
        with (
            patch("niakvio_brain_llm.planner.build_causal_prior", return_value=prior),
            patch("niakvio_brain_llm.planner.failed_advisor_fingerprints", return_value={"f" * 64}),
        ):
            with self.assertRaisesRegex(ValueError, "lacks a complete bounded schema"):
                BrainPlanner(IncompleteAdvisorBackend()).plan(request(native_parent=False))


if __name__ == "__main__":
    unittest.main()
