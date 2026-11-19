"""Official NuvioTV emulator feedback must reach Brain routing, never mutation."""
import json
import unittest
from types import SimpleNamespace
from niakvio_brain_llm.niakvio_adapter import _provider_android_tv_emulator_observations
from niakvio_brain_llm.routing import route_request

# Exercise the exact workflow-facing adapter without a heavyweight model.
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "scripts/route_android_tv_emulator_feedback.py"
spec = spec_from_file_location("tv_emulator_feedback_route", source)
assert spec and spec.loader
script = module_from_spec(spec)
spec.loader.exec_module(script)


class AndroidTVRouteLoopTests(unittest.TestCase):
    sha = "a" * 40
    digest = "b" * 64
    native_run_id = "44520778916"

    def ledger(self):
        return {
            "schemaVersion": 1,
            "authority": "official-android-tv-emulator-diagnostic-only",
            "primaryClient": "tv",
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False, "providerMutationAuthority": False,
            "rows": [{
                "sourceNiakvioSha": self.sha,
                "nativeRunId": self.native_run_id,
                "provider": "french-manga",
                "fixture": "jujutsu-kaisen-s01e01",
                "manifestScope": "manifest.json",
                "providerArtifactSha256": self.digest,
                "appSelected": True,
                "quickJsPhases": ["call"],
                "quickJsReturned": 0,
                "nativeExtractionZeroObserved": True,
                "proofAuthority": False, "publicationAuthority": False,
                "nativePlaybackAuthority": False, "providerMutationAuthority": False,
                "url": "https://token.example/do-not-leak?cookie=SECRET",
            }],
        }

    def fake_request(self, *, observations=True):
        report = self.ledger()
        rows = _provider_android_tv_emulator_observations(
            report, "french-manga",
            current_bundle_sha256=self.digest,
            active_manifest_scopes=["manifest.json"],
        ) if observations else []
        return SimpleNamespace(
            advisor_only=False,
            observations=[{"source": "official-android-tv-emulator", "value": x}
                          for x in rows],
        )

    def test_brain_routes_exact_tv_zero_as_diagnostic_only(self):
        def factory(root, provider):
            self.assertEqual(provider, "french-manga")
            return self.fake_request()
        def router(request):
            self.assertTrue(request.advisor_only)
            return SimpleNamespace(
                mode="llm_diagnose", target_layer="client",
                strategy="trace_tv_quickjs_media_context_and_transport",
                allowed_mutations=["provider_js"],
            )
        result = script.build(self.ledger(), self.sha, self.native_run_id,
                              checkout="unused", request_builder=factory,
                              router=router)
        self.assertEqual(result["primaryClient"], "tv")
        self.assertEqual(result["routeCount"], 1)
        self.assertEqual(result["routes"][0]["mode"], "llm_diagnose")
        self.assertEqual(result["routes"][0]["nextStep"],
                         "source_pinned_brain_causal_diagnosis")
        self.assertFalse(result["routes"][0]["providerMutationAuthority"])
        self.assertFalse(result["modelExecuted"])
        self.assertNotIn("allowed_mutations", json.dumps(result))
        for sensitive in ("token.example", "cookie", "SECRET", "https://"):
            self.assertNotIn(sensitive, json.dumps(result))

    def test_historical_other_run_not_rerouted(self):
        for sha, run in ((self.sha, "44520778917"),
                         ("c" * 40, self.native_run_id)):
            with self.subTest(sha=sha, run=run):
                r = script.build(self.ledger(), sha, run, checkout="unused",
                                 request_builder=lambda *_: self.fail("stale routed"))
                self.assertEqual(r["routeCount"], 0)

    def test_bundle_mismatch_never_routes(self):
        r = script.build(self.ledger(), self.sha, self.native_run_id, checkout="unused",
                         request_builder=lambda *_: self.fake_request(observations=False))
        self.assertEqual(r["routeCount"], 0)

    def test_forged_authority_or_scope_never_routes(self):
        for field, value in (
            ("proofAuthority", True),
            ("nativePlaybackAuthority", True),
            ("providerMutationAuthority", True),
            ("manifestScope", "no-anime/manifest.json"),
        ):
            ledger = self.ledger()
            ledger["rows"][0][field] = value
            r = script.build(ledger, self.sha, self.native_run_id, checkout="unused",
                             request_builder=lambda *_: self.fail("forged routed"))
            self.assertEqual(r["routeCount"], 0)

    def test_untrusted_envelope_rejected(self):
        for key, value in (
            ("schemaVersion", 2),
            ("primaryClient", "desktop"),
            ("proofAuthority", True),
            ("authority", "verified-tv-player"),
        ):
            ledger = self.ledger()
            ledger[key] = value
            with self.assertRaises(ValueError):
                script.build(ledger, self.sha, self.native_run_id, checkout="unused")


if __name__ == "__main__":
    unittest.main()
