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
from niakvio_brain_llm.retrieval import ExperienceStore
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import BrainPlanner


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

    def test_official_tv_sync_bridge_negative_reaches_force_even_when_top_six_crowded(self):
        candidate = "c" * 64
        negative = {
            "experience_id": "native-bridge-negative:44620517326:" + candidate[:16],
            "source": "official-tv-executed-negative",
            "providers": ["french-manga"],
            "failure_class": "synchronous_native_fetch_no_parallelism",
            "strategy": "require_nonblocking_native_fetch_capability_or_evidence_backed_origin_priority",
            "result": "rejected_executed_no_improvement",
            "source_niakvio_sha": "a" * 40,
            "official_client_sha": "b" * 40,
            "candidate_js_sha256": candidate,
            "proof_authority": False,
            "prior_only": True,
            "signedUrl": "https://private.invalid/?token=SECRET",
        }
        # Six lexical same-provider success histories can crowd a normal
        # similarity result. FORCE must explicitly reserve the last negative.
        positives = [{
            "experience_id": "old-success-" + str(i),
            "source": "historical-case",
            "providers": ["french-manga"],
            "failure_class": "media_extraction_gap",
            "strategy": "crawl_embed",
            "result": "validated",
            "proof_authority": False,
        } for i in range(16)]
        store = ExperienceStore(positives + [negative])
        reserved = store.same_provider_executed_negatives("french-manga", limit=2)
        self.assertEqual(len(reserved), 1)
        self.assertEqual(reserved[0]["experience_id"], negative["experience_id"])
        prompt_hints = _bounded_force_hosted_negative_hints(reserved, "french-manga")
        self.assertEqual(len(prompt_hints), 1)
        hint = prompt_hints[0]
        self.assertEqual(hint["mechanism"], "native_blocking_bridge_defeats_js_promise_hedge")
        self.assertEqual(hint["scope"], "client_transport_and_common_providerbase")
        self.assertFalse(hint["proof_authority"])
        self.assertFalse(hint["provider_mutation_authority"])
        self.assertTrue(hint["do_not_repeat_js_only_hedge_without_nonblocking_host_bridge"])
        for forbidden in ("private.invalid", "SECRET", "token=", "https://"):
            self.assertNotIn(forbidden, json.dumps(prompt_hints))
        planner = BrainPlanner(backend=object(), store=store)
        request = RepairRequest(
            provider_id="french-manga", failure_class="media_extraction_gap",
            status="REGRESSION PROVIDER", allowed_mutations=["provider_patch"]
        )
        prepared, _, _, _, _ = planner._prepare(request, compact_force=True)
        self.assertTrue(any(row.get("experience_id") == negative["experience_id"]
                            for row in prepared))
        self.assertEqual(
            store.same_provider_executed_negatives("sadisflix"), []
        )
        for key, forged in (
            ("proof_authority", True),
            ("prior_only", False),
            ("candidate_js_sha256", "https://private.invalid"),
            ("official_client_sha", "broken"),
        ):
            bad = dict(negative)
            bad[key] = forged
            self.assertEqual(
                ExperienceStore([bad]).same_provider_executed_negatives("french-manga"),
                [], key
            )

    def test_malformed_archived_acceptance_count_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / "automation" / "hosted-repair-evidence"
            directory.mkdir(parents=True)
            for i, invalid in enumerate(("not-a-number", "0", None, False, 1)):
                report = {
                    "provider": "sekai",
                    "sourceNiakvioSha": "a" * 40,
                    "sourceBrainLlmSha": "b" * 40,
                    "publicationAuthority": False,
                    "acceptedProviderCount": invalid,
                }
                (directory / f"4432799336{i}.json").write_text(json.dumps(report))
                (directory / f"4432799336{i}-evaluation.json").write_text(
                    json.dumps({"currentSha": "a" * 40, "rows": [{
                        "provider": "sekai", "accepted": False,
                        "executionObserved": True,
                        "materializedMutationObserved": True,
                        "reason": "decoded_repair_no_new_fixture_control",
                        "mutationFingerprint": "c" * 64,
                    }]})
                )
            self.assertEqual(collect_hosted_replay_negatives(root), [])

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
