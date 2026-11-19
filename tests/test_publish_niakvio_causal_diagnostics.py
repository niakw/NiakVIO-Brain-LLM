"""Private TV model diagnoses are durable redacted hypotheses, never repairs."""
import importlib.util
import json
import unittest
from pathlib import Path


FILE = Path(__file__).resolve().parents[1] / "scripts/publish_niakvio_causal_diagnostics.py"
spec = importlib.util.spec_from_file_location("brain_causal_diag", FILE)
assert spec and spec.loader
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


class CausalDiagnosticMemoryTests(unittest.TestCase):
    sha = "a" * 40
    brain = "b" * 40
    digest = "c" * 64

    def row(self, provider="french-manga", **changes):
        record = {
            "diagnostic_only": True,
            "provider_mutation_authority": False,
            "ok": True,
            "provider": provider,
            "failure_class": "candidate_replay_gap",
            "diagnostic_exact_bundle_sha256": self.digest,
            "routing": {
                "mode": "llm_diagnose",
                "target_layer": "unknown",
                "strategy": "trace_tv_hls_403_headers_client_fetch_and_decoded_video",
                "allowed_mutations": [],
                "reason": "HTTP 403 + cookie=SECRET https://signed.example/test",
            },
            "proposal": {
                "target_layer": "client",
                "diagnosis": "https://private.example/?token=SECRET",
                "strategy": "probe origin headers",
                "mutations": [],
                "abstain": False,
                "tests": ["do not release provider without real video"],
            },
        }
        record.update(changes)
        return record

    def test_keeps_only_abstract_same_source_diagnosis(self):
        rows = pub.candidate([self.row()], source_sha=self.sha, brain_sha=self.brain)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["providerArtifactSha256"], self.digest)
        self.assertEqual(r["modelStatus"], "completed")
        self.assertEqual(r["hypothesisLayer"], "client")
        self.assertTrue(r["historicalOnly"])
        for key in ("proofAuthority", "publicationAuthority",
                    "providerMutationAuthority", "nativePlaybackAuthority"):
            self.assertFalse(r[key])
        text = json.dumps(pub.merge({}, rows))
        for secret in ("https://", "private.example", "signed.example",
                       "cookie", "SECRET", "token"):
            self.assertNotIn(secret, text)

    def test_mutation_or_missing_bundle_cannot_be_stored(self):
        bad = [
            self.row(provider_mutation_authority=True),
            self.row(diagnostic_only=False),
            self.row(diagnostic_exact_bundle_sha256=""),
            self.row(routing={**self.row()["routing"],
                              "allowed_mutations": ["provider_patch"]}),
            self.row(proposal={**self.row()["proposal"],
                               "mutations": [{"scope": "provider_js", "replace": "evil"}]}),
            self.row(routing={**self.row()["routing"], "mode": "llm_repair"}),
        ]
        self.assertEqual(pub.candidate(bad, source_sha=self.sha, brain_sha=self.brain), [])
        with self.assertRaises(ValueError):
            pub.candidate([self.row()], source_sha="not_sha", brain_sha=self.brain)

    def test_failed_diagnosis_is_not_success(self):
        r = pub.candidate([
            self.row(ok=False, error="TimeoutError private-host"),
            self.row(provider="sadisflix", proposal=None, ok=True),
            self.row(provider="nakios", proposal={
                **self.row()["proposal"], "abstain": True,
            }),
        ], source_sha=self.sha, brain_sha=self.brain)
        self.assertEqual([x["modelStatus"] for x in r],
                         ["model_error", "route_only", "abstained"])
        self.assertEqual({x["providerId"] for x in r},
                         {"french-manga", "sadisflix", "nakios"})

    def test_multiple_providers_and_versions_stay_separate(self):
        first = pub.merge({}, pub.candidate([self.row()],
                                            source_sha=self.sha, brain_sha=self.brain))
        second = pub.merge(first, pub.candidate(
            [self.row(provider="sadisflix")],
            source_sha="d"*40, brain_sha=self.brain))
        self.assertEqual(second["providerCount"], 2)
        self.assertEqual(second["observationCount"], 2)
        same = pub.merge(second, pub.candidate(
            [self.row(provider="sadisflix")],
            source_sha="d"*40, brain_sha=self.brain))
        self.assertEqual(same["observationCount"], 2)
        changed = pub.merge(same, pub.candidate(
            [self.row(diagnostic_exact_bundle_sha256="e"*64)],
            source_sha=self.sha, brain_sha=self.brain))
        self.assertEqual(changed["observationCount"], 3)
        self.assertFalse(changed["publicationAuthority"])

    def test_workflow_retains_fifth_artifact_and_delete_private_model_context(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/niakvio-private-guidance.yml").read_text("utf-8")
        self.assertIn("publish_niakvio_causal_diagnostics.py", workflow)
        self.assertIn("cp niakvio-causal-diagnostics.json brain/guidance/", workflow)
        self.assertIn("FIELD_NIAKVIO_GUIDANCE_PUBLISH files=5", workflow)
        self.assertIn("rm -f private-documents.jsonl", workflow)


if __name__ == "__main__":
    unittest.main()
