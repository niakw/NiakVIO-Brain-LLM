"""Historical Retest negatives survive other providers' runs without proof authority."""
import unittest
from niakvio_brain_llm.niakvio_adapter import _provider_retest_history_observations


class RetestHistoryTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 64
        self.payload = {
            "schemaVersion": 1,
            "authority": "historical-exact-bundle-diagnostics-only",
            "proofAuthority": False,
            "publicationAuthority": False,
            "rows": [{
                "provider": "demo",
                "providerArtifactSha256": self.sha,
                "sourceCensusRunId": "123-retest",
                "sourceNiakvioSha": "b" * 40,
                "lane": "anime",
                "playable": 2,
                "verified": 0,
                "identityReasons": ["duration_incomplete_hls",
                                    "insufficient_identity_metadata",
                                    "https://secret.example"],
                "url": "https://secret.example/private",
                "proofAuthority": False,
                "publicationAuthority": False,
                "nativePlaybackAuthority": False,
            }],
        }

    def get(self, payload=None, provider="demo", sha=None, current_run="124-retest"):
        return _provider_retest_history_observations(
            self.payload if payload is None else payload, provider,
            current_bundle_sha256=self.sha if sha is None else sha,
            current_census_run_id=current_run,
        )

    def test_keeps_only_matching_js_and_negative_codes(self):
        records = self.get()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source"], "historical-exact-js-retest")
        self.assertEqual(records[0]["sourceCensusRunId"], "123-retest")
        self.assertEqual(records[0]["identityReasons"],
                         ["duration_incomplete_hls", "insufficient_identity_metadata"])
        self.assertEqual(records[0]["verified"], 0)
        self.assertTrue(records[0]["historicalOnly"])
        self.assertFalse(records[0]["proofAuthority"])
        self.assertFalse(records[0]["nativePlaybackAuthority"])
        self.assertNotIn("url", records[0])

    def test_no_stale_provider_or_js_promotion(self):
        self.assertEqual(self.get(provider="other"), [])
        self.assertEqual(self.get(sha="c" * 64), [])
        self.assertEqual(self.get(sha=""), [])
        self.assertEqual(self.get(current_run="123-retest"), [])

    def test_refuse_invalid_envelope_or_claimed_authority(self):
        for key, value in (
            ("authority", "current-retest-observation-only"),
            ("publicationAuthority", True),
            ("proofAuthority", True),
            ("schemaVersion", 2),
        ):
            with self.subTest(key=key):
                payload = dict(self.payload)
                payload[key] = value
                self.assertEqual(self.get(payload), [])
        for key in ("proofAuthority", "nativePlaybackAuthority", "publicationAuthority"):
            payload = {**self.payload, "rows": [{**self.payload["rows"][0], key: True}]}
            self.assertEqual(self.get(payload), [])

    def test_limit_history_per_provider(self):
        rows = []
        for index in range(100, 120):
            rows.append({**self.payload["rows"][0],
                         "sourceCensusRunId": f"{index}-retest"})
        self.assertEqual(len(self.get({**self.payload, "rows": rows})), 4)


if __name__ == "__main__":
    unittest.main()
