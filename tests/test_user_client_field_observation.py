"""User-reported Desktop/TV divergence is useful but never current media authority."""
import copy
import unittest
from niakvio_brain_llm.niakvio_adapter import _provider_user_client_field_observation


class UserClientFieldObservationTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "schemaVersion": 1,
            "authority": "non-authoritative-user-field-report",
            "reportedOn": "2026-11-19",
            "proofAuthority": False,
            "publicationAuthority": False,
            "sourceBundleVerified": False,
            "rows": [{
                "provider": "french-manga", "fixtureKnown": False,
                "clients": [
                    {"client": "desktop-macos", "observation": "stream-played",
                     "streamCountObserved": 1, "audioLanguagesObserved": ["fr"]},
                    {"client": "android-tv", "observation": "not-in-stream-list",
                     "url": "https://secret.example/path?token=PRIVATE"},
                ],
                "note": "do not reproduce player URL or unverified client SHA",
            }],
        }

    def observe(self, payload=None, provider="french-manga", scopes=None):
        return _provider_user_client_field_observation(
            self.payload if payload is None else payload,
            provider, active_manifest_scopes=(
                ["manifest.json", "vf/manifest.json"] if scopes is None else scopes
            ),
        )

    def test_field_report_identifies_client_differential_without_claiming_proof(self):
        record = self.observe()
        self.assertEqual(record["clients"][0]["audioLanguagesObserved"], ["fr"])
        self.assertEqual(record["clients"][0]["streamCountObserved"], 1)
        self.assertTrue(record["crossClientVisibilityDiscrepancy"])
        self.assertEqual(record["activeManifestScopesAtCheckout"],
                         ["manifest.json", "vf/manifest.json"])
        for key in ("proofAuthority", "publicationAuthority", "mutationAuthority",
                    "executedJsKnown", "appBuildKnown", "installedManifestKnown"):
            self.assertFalse(record[key])
        self.assertFalse(record["fixtureKnown"])
        # French-Manga must not be inferred on no-anime installations merely
        # because the Full Global/VF manifests contain it.
        with_variants = self.observe(scopes=[
            "manifest.json", "vf/manifest.json",
            "no-anime/manifest.json", "vf-no-anime/manifest.json",
        ])
        self.assertEqual(len(with_variants["activeManifestScopesAtCheckout"]), 4)
        self.assertNotIn("url", str(record))
        self.assertNotIn("secret.example", str(record))
        self.assertNotIn("PRIVATE", str(record))

    def test_vf_only_is_derived_from_checkout_not_user_claim(self):
        row = copy.deepcopy(self.payload["rows"][0])
        row["provider"] = "sadisflix"
        row["clients"] = [{"client": "unspecified", "observation": "not-in-stream-list"}]
        self.payload["rows"] = [row]
        result = self.observe(
            provider="sadisflix",
            scopes=["vf/manifest.json", "vf-no-anime/manifest.json"],
        )
        self.assertEqual(
            result["activeManifestScopesAtCheckout"],
            ["vf-no-anime/manifest.json", "vf/manifest.json"],
        )
        self.assertFalse(result["crossClientVisibilityDiscrepancy"])

    def test_fake_authority_and_unspecified_fixture_cannot_be_upgraded(self):
        for key, value in (
            ("proofAuthority", True),
            ("publicationAuthority", True),
            ("sourceBundleVerified", True),
            ("authority", "current-retest-observation-only"),
            ("reportedOn", "malicious"),
        ):
            with self.subTest(key=key):
                payload = copy.deepcopy(self.payload)
                payload[key] = value
                self.assertEqual(self.observe(payload), {})
        fake = copy.deepcopy(self.payload)
        fake["rows"][0]["fixtureKnown"] = True
        self.assertEqual(self.observe(fake), {})
        self.assertEqual(self.observe(provider="someone-else"), {})

    def test_discard_invalid_client_names_and_sensitive_languages(self):
        fake = copy.deepcopy(self.payload)
        fake["rows"][0]["clients"].extend([
            {"client": "https://example.com", "observation": "stream-played"},
            {"client": "android-mobile", "observation": "stream-played",
             "streamCountObserved": 900,
             "audioLanguagesObserved": ["https://secret.example?cookie=foo", "en-US"]},
        ])
        res = self.observe(fake)
        self.assertEqual(len(res["clients"]), 3)
        self.assertEqual(res["clients"][2]["audioLanguagesObserved"], ["en-us"])
        self.assertIsNone(res["clients"][2]["streamCountObserved"])
        self.assertNotIn("secret.example", str(res))


if __name__ == "__main__":
    unittest.main()
