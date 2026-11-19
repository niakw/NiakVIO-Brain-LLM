"""Brain handles official TV emulator as primary diagnostic, never provider proof."""
import unittest

from niakvio_brain_llm.niakvio_adapter import _provider_android_tv_emulator_observations


class AndroidTVEmulatorMemoryTests(unittest.TestCase):
    sha = "a" * 64

    def report(self):
        return {
            "schemaVersion": 1,
            "authority": "official-android-tv-emulator-diagnostic-only",
            "primaryClient": "tv",
            "proofAuthority": False,
            "publicationAuthority": False,
            "nativePlaybackAuthority": False,
            "providerMutationAuthority": False,
            "rows": [{
                "provider": "french-manga",
                "providerArtifactSha256": self.sha,
                "sourceNiakvioSha": "b" * 40,
                "nativeRunId": "44514660418",
                "officialClientSha": "c" * 40,
                "manifestScope": "manifest.json",
                "fixture": "jujutsu-kaisen-s01e01",
                "requestType": "anime",
                "appSelected": True,
                "quickJsPhases": ["call", "result"],
                "quickJsErrors": ["none", "reference_error", "https://leak.invalid/x"],
                "quickJsReturned": 0,
                "playerStates": ["error", "https://secret.invalid"],
                "readerEvidenceComplete": False,
                "proofAuthority": False,
                "publicationAuthority": False,
                "nativePlaybackAuthority": False,
                "providerMutationAuthority": False,
                "privateUrl": "https://secret.invalid",
            }],
        }

    def get(self, data=None, sha=None, scopes=None):
        return _provider_android_tv_emulator_observations(
            data if data is not None else self.report(),
            "french-manga",
            current_bundle_sha256=self.sha if sha is None else sha,
            active_manifest_scopes=["manifest.json"] if scopes is None else scopes,
        )

    def test_consumes_non_authoritative_exact_js_telemetry(self):
        rows = self.get()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["client"], "tv")
        self.assertEqual(row["officialClientSha"], "c" * 40)
        self.assertEqual(row["requestType"], "anime")
        self.assertEqual(row["quickJsReturned"], 0)
        self.assertEqual(row["quickJsErrors"], ["reference_error"])
        self.assertEqual(row["playerStates"], ["error"])
        self.assertTrue(row["appSelected"])
        self.assertFalse(row["readerEvidenceComplete"])
        self.assertTrue(row["historicalOnly"])
        for flag in ("proofAuthority", "publicationAuthority",
                     "nativePlaybackAuthority", "providerMutationAuthority"):
            self.assertFalse(row[flag])
        self.assertNotIn("privateUrl", row)

    def test_client_ref_is_historical_and_fail_closed(self):
        actual = self.get()[0]
        self.assertEqual(actual["officialClientSha"], "c"*40)
        self.assertTrue(actual["historicalOnly"])
        self.assertFalse(actual["nativePlaybackAuthority"])
        for value in ("https://private.invalid/SECRET", "12345", "Z"*40):
            data = self.report()
            data["rows"][0]["officialClientSha"] = value
            rows = self.get(data)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["officialClientSha"], "")
        old = self.report()
        del old["rows"][0]["officialClientSha"]
        self.assertEqual(self.get(old)[0]["officialClientSha"], "")

    def test_mismatch_never_becomes_current_proof(self):
        self.assertEqual(self.get(sha="c" * 64), [])
        self.assertEqual(self.get(scopes=["vf/manifest.json"]), [])
        self.assertEqual(self.get(sha=""), [])
        for key in ("proofAuthority", "publicationAuthority", "nativePlaybackAuthority",
                    "providerMutationAuthority"):
            data = self.report()
            data["rows"][0][key] = True
            self.assertEqual(self.get(data), [])
            data = self.report()
            data[key] = True
            self.assertEqual(self.get(data), [])

    def test_reject_untrusted_run_or_wrong_media_scope(self):
        for key, value in (
            ("nativeRunId", "oops"),
            ("sourceNiakvioSha", "broken"),
            ("manifestScope", "no-anime/manifest.json"),
            ("requestType", "unknown"),
        ):
            data = self.report()
            data["rows"][0][key] = value
            self.assertEqual(self.get(data), [])

    def test_cross_provider_not_imported(self):
        data = self.report()
        data["rows"][0]["provider"] = "sadisflix"
        self.assertEqual(self.get(data), [])


if __name__ == "__main__":
    unittest.main()
