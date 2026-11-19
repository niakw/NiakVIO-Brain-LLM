"""A current Retest is Brain diagnostic context only on matching executed JS."""
import copy
import unittest
from niakvio_brain_llm.niakvio_adapter import _provider_retest_observation


class CurrentRetestEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.bundle = "b" * 64
        self.census = {
            "runId": "12345-retest", "triggerSha": self.sha,
            "providers": [{"provider": "demo", "status": "CANDIDATE OK",
                           "testedThisRun": True}],
        }
        self.payload = {
            "schemaVersion": 1, "authority": "current-retest-observation-only",
            "sourceNiakvioSha": self.sha, "sourceCensusRunId": "12345-retest",
            "proofAuthority": False, "publicationAuthority": False,
            "rows": [{
                "provider": "demo", "providerArtifactSha256": self.bundle,
                "lane": "anime", "status": "playable_unverified",
                "debugStage": "provider_returned_streams",
                "fixture": {"mediaType": "anime", "tmdbId": "95479",
                            "season": 1, "episode": 1},
                "raw": 2, "playable": 2, "verified": 0,
                "identityReasons": ["insufficient_identity_metadata",
                                    "duration_incomplete_hls",
                                    "https://forbidden.example/auth"],
                "proofAuthority": False, "publicationAuthority": False,
                "nativePlaybackAuthority": False,
                "url": "https://forbidden.example/media?secret",
            }],
        }

    def observe(self, payload=None, census=None, digest=None):
        return _provider_retest_observation(
            self.payload if payload is None else payload,
            self.census if census is None else census,
            "demo",
            current_bundle_sha256=self.bundle if digest is None else digest,
        )

    def test_exact_source_keeps_only_sanitized_current_failure(self):
        row = self.observe()
        self.assertEqual(row["source"], "same-js-current-retest")
        self.assertEqual(row["identityReasons"], [
            "insufficient_identity_metadata", "duration_incomplete_hls",
        ])
        self.assertEqual(row["fixture"], {
            "mediaType": "anime", "tmdbId": "95479", "season": 1, "episode": 1,
        })
        self.assertEqual(row["playable"], 2)
        self.assertEqual(row["verified"], 0)
        self.assertIs(row["proofAuthority"], False)
        self.assertIs(row["nativePlaybackAuthority"], False)
        self.assertNotIn("url", row)
        self.assertNotIn("host", row)

    def test_missing_or_stale_bundle_denied(self):
        for digest in ("", "b" * 63, "c" * 64):
            with self.subTest(digest=digest):
                self.assertEqual(self.observe(digest=digest), {})

    def test_stale_census_or_source_denied(self):
        for field, value in (
            ("runId", "different-retest"),
            ("triggerSha", "c" * 40),
        ):
            with self.subTest(field=field):
                census = copy.deepcopy(self.census)
                census[field] = value
                self.assertEqual(self.observe(census=census), {})
        for field, value in (
            ("sourceCensusRunId", "outdated-retest"),
            ("sourceNiakvioSha", "d" * 40),
            ("proofAuthority", True),
            ("publicationAuthority", True),
        ):
            with self.subTest(field=field):
                payload = copy.deepcopy(self.payload)
                payload[field] = value
                self.assertEqual(self.observe(payload=payload), {})

    def test_never_forge_proof_or_admit_disabled(self):
        for field in ("proofAuthority", "publicationAuthority",
                      "nativePlaybackAuthority"):
            payload = copy.deepcopy(self.payload)
            payload["rows"][0][field] = True
            self.assertEqual(self.observe(payload=payload), {})
        for status, tested in (("DISABLED", True), ("CANDIDATE OK", False)):
            census = copy.deepcopy(self.census)
            census["providers"][0].update(status=status, testedThisRun=tested)
            self.assertEqual(self.observe(census=census), {})
        payload = copy.deepcopy(self.payload)
        payload["rows"][0]["provider"] = "other"
        self.assertEqual(self.observe(payload=payload), {})


if __name__ == "__main__":
    unittest.main()
