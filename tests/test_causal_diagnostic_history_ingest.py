"""Fifth guidance file must feed Brain's next cycle without becoming a proof oracle."""
import copy
import json
import unittest
from pathlib import Path

from niakvio_brain_llm.niakvio_adapter import _provider_causal_diagnostic_priors


class CausalHistoryIngestTests(unittest.TestCase):
    DIGEST = "c" * 64

    def setUp(self):
        self.row = {
            "providerId": "french-manga",
            "providerArtifactSha256": self.DIGEST,
            "sourceNiakvioSha": "a" * 40,
            "brainLlmSha": "b" * 40,
            "failureClass": "candidate_replay_gap",
            "strategy": "trace_tv_hls_403_headers_client_fetch_and_decoded_video",
            "routingLayer": "unknown", "hypothesisLayer": "network",
            "modelStatus": "abstained",
            "historicalOnly": True,
            "proofAuthority": False,
            "publicationAuthority": False,
            "providerMutationAuthority": False,
            "nativePlaybackAuthority": False,
            "url": "https://private.example/?token=SECRET",
            "freeText": "A secret, never include",
        }
        self.payload = {
            "schemaVersion": 1,
            "authority": "brain-source-pinned-causal-hypotheses-only",
            "proofAuthority": False,
            "publicationAuthority": False,
            "providerMutationAuthority": False,
            "nativePlaybackAuthority": False,
            "privateContentRetained": False,
            "rows": [self.row],
        }

    def read(self, payload=None, provider="french-manga", digest=None):
        return _provider_causal_diagnostic_priors(
            self.payload if payload is None else payload, provider,
            current_bundle_sha256=self.DIGEST if digest is None else digest,
        )

    def test_read_only_historical_same_bundle(self):
        rows = self.read()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["strategy"],
                         "trace_tv_hls_403_headers_client_fetch_and_decoded_video")
        self.assertEqual(row["modelStatus"], "abstained")
        self.assertEqual(row["hypothesisLayer"], "network")
        self.assertTrue(row["historicalOnly"])
        for key in ("proofAuthority", "publicationAuthority",
                    "providerMutationAuthority", "nativePlaybackAuthority"):
            self.assertIs(row[key], False)
        wire = json.dumps(rows)
        for secret in ("private.example", "SECRET", "freeText", "https://",
                       "token", "secret"):
            self.assertNotIn(secret, wire)

    def test_wrong_js_provider_unauthorized_envelope_rejected(self):
        self.assertEqual(self.read(digest="d" * 64), [])
        self.assertEqual(self.read(digest=""), [])
        self.assertEqual(self.read(provider="sadisflix"), [])
        for key, value in (
            ("proofAuthority", True),
            ("publicationAuthority", True),
            ("providerMutationAuthority", True),
            ("nativePlaybackAuthority", True),
            ("privateContentRetained", True),
            ("authority", "current-verified-playback"),
        ):
            altered = copy.deepcopy(self.payload)
            altered[key] = value
            with self.subTest(key=key):
                self.assertEqual(self.read(altered), [])

    def test_one_forged_row_does_not_poison_other_history(self):
        for key in ("proofAuthority", "publicationAuthority",
                    "providerMutationAuthority", "nativePlaybackAuthority",
                    "historicalOnly"):
            altered = copy.deepcopy(self.payload)
            altered["rows"][0][key] = not self.row[key]
            with self.subTest(key=key):
                self.assertEqual(self.read(altered), [])
        malformed = copy.deepcopy(self.payload)
        malformed["rows"][0]["strategy"] = "https://secret"
        self.assertEqual(self.read(malformed), [])
        malformed["rows"][0]["strategy"] = self.row["strategy"]
        malformed["rows"][0]["sourceNiakvioSha"] = "bad"
        self.assertEqual(self.read(malformed), [])

    def test_dedupe_limit_and_cross_provider(self):
        altered = copy.deepcopy(self.payload)
        altered["rows"] = [
            {**self.row, "sourceNiakvioSha": f"{i:040x}"}
            for i in range(40)
        ]
        rows = self.read(altered)
        self.assertEqual(len(rows), 4)
        same = copy.deepcopy(self.payload)
        same["rows"] = [self.row, self.row]
        self.assertEqual(len(self.read(same)), 1)

    def test_real_guidance_imports_history_before_routing_and_cleans_up(self):
        wf = (Path(__file__).resolve().parents[1] /
              ".github/workflows/niakvio-private-guidance.yml").read_text("utf-8")
        self.assertLess(wf.index("Reuse prior Brain causal diagnosis"),
                        wf.index("Route exact requested Repair cohort"))
        self.assertIn("guidance/niakvio-causal-diagnostics.json", wf)
        self.assertIn("niakvio/automation/brain-causal-diagnostics-history.json", wf)
        self.assertIn("rm -f niakvio/automation/brain-causal-diagnostics-history.json", wf)
        source = (Path(__file__).resolve().parents[1] /
                  "src/niakvio_brain_llm/niakvio_adapter.py").read_text("utf-8")
        self.assertIn('"source": "historical-brain-causal-diagnosis"', source)
        self.assertIn('_provider_causal_diagnostic_priors(', source)


if __name__ == "__main__":
    unittest.main()
