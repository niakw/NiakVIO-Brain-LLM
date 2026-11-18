"""Historical hosted FORCE evidence is replayed only as negative strategy memory."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

# GitHub's hosted NiakVIO harness checks out Brain as ./brain-llm; the
# project root also has a scripts package. Load this sibling script by its
# exact file path so root-package shadowing cannot silently switch importer.
import importlib.util

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_public_niakvio.py"
_SPEC = importlib.util.spec_from_file_location("niakvio_brain_public_import", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
collect_hosted_replay_negatives = _MOD.collect_hosted_replay_negatives
from niakvio_brain_llm.prompting import _bounded_force_hosted_negative_hints


class HostedNegativeLearningTests(unittest.TestCase):
    def test_only_exact_executed_materialized_negative_is_learned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / "automation" / "hosted-repair-evidence"
            directory.mkdir(parents=True)
            source_sha = "a" * 40
            brain_sha = "b" * 40
            fingerprint = "c" * 64
            report = {
                "provider": "sekai",
                "sourceNiakvioSha": source_sha,
                "sourceBrainLlmSha": brain_sha,
                "publicationAuthority": False,
                "acceptedProviderCount": 0,
            }
            evaluation = {
                "currentSha": source_sha,
                "rows": [{
                    "provider": "sekai",
                    "accepted": False,
                    "executionObserved": True,
                    "materializedMutationObserved": True,
                    "reason": "decoded_repair_no_new_fixture_control",
                    "mutationFingerprint": fingerprint,
                    "mutationSummary": [{
                        "scope": "provider_bloc",
                        "family": "slug_saga_inline_media",
                    }],
                    "rawMutation": "must never be ingested",
                }],
            }
            (directory / "44327993359.json").write_text(json.dumps(report))
            (directory / "44327993359-evaluation.json").write_text(
                json.dumps(evaluation)
            )
            # A superficially identical invalid report has no executed bytes.
            (directory / "44327993360.json").write_text(json.dumps(report))
            evaluation["rows"][0]["executionObserved"] = False
            (directory / "44327993360-evaluation.json").write_text(
                json.dumps(evaluation)
            )
            rows = collect_hosted_replay_negatives(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["providers"], ["sekai"])
            self.assertEqual(rows[0]["result"], "rejected_executed_no_improvement")
            self.assertEqual(rows[0]["source"], "hosted-executed-negative")
            self.assertFalse(rows[0]["proof_authority"])
            self.assertTrue(rows[0]["prior_only"])
            self.assertNotIn("must never be ingested", json.dumps(rows))
            selected = _bounded_force_hosted_negative_hints(rows, "sekai")
            self.assertEqual(len(selected), 1)
            self.assertEqual(selected[0]["mechanism"], "slug_saga_inline_media")
            self.assertEqual(selected[0]["mutation_fingerprint"], "c" * 16)
            self.assertFalse(selected[0]["proof_authority"])
            self.assertEqual(
                _bounded_force_hosted_negative_hints(rows, "frenchstream"), []
            )
            self.assertEqual(
                _bounded_force_hosted_negative_hints([
                    {**rows[0], "proof_authority": True}
                ], "sekai"), []
            )

    def test_non_false_publication_authority_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / "automation" / "hosted-repair-evidence"
            directory.mkdir(parents=True)
            (directory / "44327993359.json").write_text(json.dumps({
                "provider": "sekai",
                "sourceNiakvioSha": "a" * 40,
                "sourceBrainLlmSha": "b" * 40,
                "publicationAuthority": True,
                "acceptedProviderCount": 0,
            }))
            self.assertEqual(collect_hosted_replay_negatives(root), [])


if __name__ == "__main__":
    unittest.main()
