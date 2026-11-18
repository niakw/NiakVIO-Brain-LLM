"""Only exact executed provider JS bytes may elevate residential replay to Brain causality."""
import unittest

from niakvio_brain_llm.niakvio_adapter import _provider_waf_observation


class ResidentialBundleProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "rows": [{
                "provider": "demo",
                "lane": "anime",
                "outcome": "browser_challenge_persisted",
                "residentialExitNodeProfile": {"outcome": "browser_content_reached"},
            }],
            "residentialProviderReplay": {
                "available": True,
                "rows": [{
                    "provider": "demo",
                    "lane": "anime",
                    "status": "no_streams",
                    "debugStage": "provider_zero_before_provider_network",
                    "contradictions": 0,
                    "identitySafe": True,
                    "providerArtifactSha256": "a" * 64,
                }],
            },
        }

    def test_exact_bundle_keeps_runtime_replay(self):
        row = _provider_waf_observation(
            self.report, "demo", current_bundle_sha256="a" * 64,
        )
        self.assertEqual(len(row["residentialReplay"]), 1)
        self.assertEqual(row["browserOutcomes"], ["browser_challenge_persisted"])

    def test_stale_bundle_is_only_a_transport_prior(self):
        for digest in ("b" * 64, ""):
            with self.subTest(digest=digest):
                self.report["residentialProviderReplay"]["rows"][0]["providerArtifactSha256"] = digest
                row = _provider_waf_observation(
                    self.report, "demo", current_bundle_sha256="a" * 64,
                )
                self.assertEqual(row["residentialReplay"], [])
                self.assertEqual(row["residentialOutcomes"], ["browser_content_reached"])
                self.assertEqual(row["browserOutcomes"], ["browser_challenge_persisted"])

    def test_absent_or_malformed_current_bundle_cannot_authorize_any_replay(self):
        for digest in ("", "invalid", "a" * 63):
            with self.subTest(digest=digest):
                row = _provider_waf_observation(
                    self.report, "demo", current_bundle_sha256=digest,
                )
                self.assertEqual(row["residentialReplay"], [])
                self.assertFalse(row["residentialReplayCurrentBundle"])
                self.assertEqual(row["browserOutcomes"], ["browser_challenge_persisted"])

    def test_other_provider_replay_never_admitted(self):
        row = _provider_waf_observation(
            self.report, "other", current_bundle_sha256="a" * 64,
        )
        self.assertEqual(row, {})


if __name__ == "__main__":
    unittest.main()
