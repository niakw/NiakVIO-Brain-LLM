"""Regression: verified residential runtime evidence cannot vanish in CPU FORCE."""
import os
import unittest
from unittest.mock import patch

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import COMPACT_FORCE_SYSTEM_PROMPT
from niakvio_brain_llm.prompting import (
    _current_residential_provider_replay, build_force_prompt_payload,
)


def observed(matched=True):
    return [{
        "source": "waf-client-differential-current",
        "value": {
            "residentialReplayCurrentBundle": matched,
            "browserOutcomes": ["browser_content_reached"],
            "residentialOutcomes": ["browser_content_reached"],
            "nativeTvTransportStillUnproven": True,
            "residentialReplay": [{
                "lane": "anime",
                "status": "no_streams",
                "debugStage": "provider_zero_before_provider_network",
                "sampleDebugStages": ["provider_zero_before_provider_network"],
                "raw": 0,
                "playable": 0,
                "verified": 0,
                "identitySafe": True,
                "cookie": "very-private-secret",
                "url": "https://example.invalid/private?token=secret",
            }],
        },
    }]


class ResidentialPromptContractTests(unittest.TestCase):
    def test_only_matching_bundle_carries_execution_causality(self):
        result = _current_residential_provider_replay(observed())
        self.assertEqual(
            result["providerRuntime"][0]["debugStage"],
            "provider_zero_before_provider_network",
        )
        self.assertFalse(result["playbackProofAuthority"])
        self.assertTrue(result["mutateOnlyAfterCurrentCausalDiagnosis"])
        self.assertEqual(result["transport"]["githubBrowserOutcomes"], ["browser_content_reached"])
        self.assertNotIn("secret", repr(result))
        self.assertNotIn("example.invalid", repr(result))
        self.assertEqual(_current_residential_provider_replay(observed(False)), {})

    def test_not_lost_when_four_other_observations_take_priority(self):
        request = RepairRequest(
            provider_id="demo", status="REGRESSION PROVIDER",
            failure_class="route_proven_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": "async function getStreams(){const streams=[];return streams;}",
            },
            observations=[
                {"source": "current-provider-structure", "value": {"kind": "functions"}},
                {"source": "census-sharded-current", "value": {"kind": "census"}},
                {"source": "runtime-variant-coverage-current", "value": {"kind": "variants"}},
                {"source": "targeted-regression-current", "value": {"debugStages": {"anime": "provider_network_http_error"}}},
                *observed(),
            ],
        )
        with patch.dict(os.environ, {"NIAKVIO_FORCE_CPU_TIGHT_PROMPT": "1"}):
            payload = build_force_prompt_payload(
                request, {}, {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
            )
        replay = payload["current_residential_provider_replay"]
        self.assertEqual(replay["providerRuntime"][0]["debugStage"], "provider_zero_before_provider_network")
        self.assertFalse(replay["playbackProofAuthority"])
        self.assertIn("provider_zero_before_provider_network", COMPACT_FORCE_SYSTEM_PROMPT)

    def test_malformed_evidence_is_not_runtime_authority(self):
        for value in (None, {}, "invalid", {"residentialReplayCurrentBundle": True, "residentialReplay": {}}):
            with self.subTest(value=value):
                self.assertEqual(_current_residential_provider_replay([
                    {"source": "waf-client-differential-current", "value": value}
                ]), {})


if __name__ == "__main__":
    unittest.main()
