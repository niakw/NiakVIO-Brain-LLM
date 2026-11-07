import importlib.util
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import _force_memory_blocks_mutations
from niakvio_brain_llm.niakvio_adapter import _provider_force_negative_memory

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_niakvio_force_mutations.py"
spec = importlib.util.spec_from_file_location("publish_force", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class ForceCandidatePublicationTests(unittest.TestCase):
    def setUp(self):
        self.old_request = mod.request_from_checkout
        self.old_validate = mod.validate_mutations
        self.old_memory = mod.load_force_memory
        mod.request_from_checkout = lambda _root, _provider: SimpleNamespace(
            provider_context={"registered_patch_scripts": []},
            allowed_mutations=["provider_data"],
        )
        mod.validate_mutations = lambda *_args, **_kwargs: None
        mod.load_force_memory = lambda _root: set()

    def tearDown(self):
        mod.request_from_checkout = self.old_request
        mod.validate_mutations = self.old_validate
        mod.load_force_memory = self.old_memory

    @staticmethod
    def row(value: str):
        return {
            "ok": True,
            "provider": "demo",
            "failure_class": "chain_terminal_gap",
            "proposal": {
                "provider_id": "demo",
                "target_layer": "provider",
                "strategy": "terminal-media-extractor-with-playback-validation",
                "confidence": 0.96,
                "abstain": False,
                "mutations": [{
                    "scope": "provider_data",
                    "operation": "set",
                    "path": "notes",
                    "value": value,
                }],
                "tests": [],
            },
        }

    def test_single_candidate_is_publishable(self):
        out = mod.sanitize(
            [self.row("candidate-a")],
            niakvio_root=ROOT,
            niakvio_sha="a" * 40,
            brain_llm_sha="b" * 40,
        )
        self.assertEqual(out["providerCount"], 1)
        self.assertEqual(len(out["rows"]), 1)

    def test_exact_failed_candidate_is_filtered_by_force_memory(self):
        first = mod.sanitize(
            [self.row("candidate-a")],
            niakvio_root=ROOT,
            niakvio_sha="a" * 40,
            brain_llm_sha="b" * 40,
        )
        self.assertEqual(len(first["rows"]), 1)
        row = first["rows"][0]
        mod.load_force_memory = lambda _root: {
            (
                row["providerId"],
                row["mutationFingerprint"],
                row["mutationContextFingerprint"],
            )
        }
        second = mod.sanitize(
            [self.row("candidate-a")],
            niakvio_root=ROOT,
            niakvio_sha="a" * 40,
            brain_llm_sha="b" * 40,
        )
        self.assertEqual(second["providerCount"], 0)
        self.assertEqual(second["rows"], [])

    def test_provider_bloc_failed_fingerprint_survives_neutral_context_drift(self):
        blocked = {
            ("demo", "a" * 64, "b" * 64),
            ("other", "c" * 64, "d" * 64),
        }
        self.assertTrue(mod.force_candidate_blocked(
            blocked,
            provider="demo",
            mutation_fp="a" * 64,
            context_fp="e" * 64,
            scopes={"provider_bloc"},
        ))
        self.assertFalse(mod.force_candidate_blocked(
            blocked,
            provider="demo",
            mutation_fp="a" * 64,
            context_fp="e" * 64,
            scopes={"provider_patch"},
        ))
        self.assertTrue(mod.force_candidate_blocked(
            blocked,
            provider="demo",
            mutation_fp="a" * 64,
            context_fp="b" * 64,
            scopes={"provider_patch"},
        ))

    def test_publisher_and_planner_agree_on_4khdhub_unexecuted_rejections(self):
        # Regression from hosted Brain run 42382482886: the generator produced
        # three concrete class/metadata/identity candidates, but publication
        # incorrectly blacklisted them from stale playback-gate counters even
        # when the ledger explicitly said executionObserved=false.
        mutation = {
            "scope": "provider_bloc", "operation": "replace",
            "find": "function classBlocks(){return 0;}",
            "replace": "function classBlocks(){return 1;}",
        }
        fp = mod.fingerprint([mutation])
        ctx_fp = "b" * 64
        request = RepairRequest(
            provider_id="4khdhub", failure_class="route_proven_gap",
            observations=[],
            allowed_mutations=["provider_bloc"],
        )

        def check(last_outcome, observed, materialized, expected_blocked):
            value = {
                "providerId": "4khdhub", "mutationFingerprint": fp,
                "mutationContextFingerprint": ctx_fp,
                "consecutiveFailures": 1, "failures": 1,
                "successes": 0, "lastOutcome": last_outcome,
                "lastMutationSummary": [{"scope":"provider_bloc","operation":"upsert"}],
            }
            if observed is not None:
                value["executionObserved"] = observed
            if materialized is not None:
                value["materializedMutationObserved"] = materialized
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "automation").mkdir()
                (root / "automation" / "brain-llm-force-memory.json").write_text(
                    json.dumps({"schemaVersion": 1, "entries": [value]}),
                    encoding="utf-8",
                )
                blocked = self.old_memory(root)
            self.assertEqual(
                mod.force_candidate_blocked(
                    blocked, provider="4khdhub", mutation_fp=fp,
                    context_fp="c" * 64, scopes={"provider_bloc"},
                ), expected_blocked, (last_outcome, observed),
            )
            trace_request = RepairRequest(
                provider_id="4khdhub", failure_class="route_proven_gap",
                allowed_mutations=["provider_bloc"],
                observations=[{
                    "source": "brain-force-sandbox-memory", "value": [value],
                }],
            )
            self.assertEqual(
                _force_memory_blocks_mutations(trace_request, [mutation]),
                expected_blocked, (last_outcome, observed),
            )
            projected = _provider_force_negative_memory(
                {"entries": [value]}, "4khdhub",
            )
            self.assertEqual(
                projected[0]["executionObserved"],
                last_outcome == "rejected" and observed is True,
                (last_outcome, observed),
            )
            self.assertEqual(
                projected[0]["materializedMutationObserved"],
                materialized is True, (last_outcome, materialized),
            )

        for outcome, observed, materialized, blocked in (
            ("rejected", False, True, False),
            ("rejected", True, True, True),
            ("rejected", True, False, False),
            ("rejected", True, None, False),
            ("rejected", None, True, False),
            ("not_generated", True, True, False),
            ("profile_unavailable", True, True, False),
            ("accepted", True, True, False),
        ):
            with self.subTest(outcome=outcome, executionObserved=observed,
                              materializedMutationObserved=materialized):
                check(outcome, observed, materialized, blocked)

    def test_unexecuted_rejection_does_not_remove_sandbox_candidate(self):
        mutation = self.row("candidate-a")["proposal"]["mutations"][0]
        fp = mod.fingerprint([mutation])
        def fake_load(_root):
            return self.old_memory(_root)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "automation").mkdir()
            memory = root / "automation" / "brain-llm-force-memory.json"
            memory.write_text(json.dumps({
                "entries": [{
                    "providerId": "demo", "mutationFingerprint": fp,
                    "mutationContextFingerprint": "b"*64,
                    "executionObserved": False, "lastOutcome": "rejected",
                    "consecutiveFailures": 1, "failures": 1,
                }],
            }), encoding="utf-8")
            mod.load_force_memory = fake_load
            # Provider_data needs only a local override context; the two
            # mutator guards and minimum confidence still apply.
            actual = mod.sanitize(
                [self.row("candidate-a")], niakvio_root=root,
                niakvio_sha="a"*40, brain_llm_sha="b"*40,
            )
            self.assertEqual(actual["providerCount"], 1, actual)
            self.assertEqual(len(actual["rows"]), 1, actual)

    def test_multiple_concrete_candidates_publish_as_ordered_portfolio(self):
        first = self.row("candidate-a")
        first["hypothesis_index"] = 1
        second = self.row("candidate-b")
        second["hypothesis_index"] = 2
        out = mod.sanitize(
            [first, second],
            niakvio_root=ROOT,
            niakvio_sha="a" * 40,
            brain_llm_sha="b" * 40,
        )
        self.assertEqual(out["providerCount"], 1)
        self.assertEqual(len(out["rows"]), 2)
        self.assertEqual([row["candidateOrdinal"] for row in out["rows"]], [1, 2])
        self.assertNotEqual(
            out["rows"][0]["mutationFingerprint"],
            out["rows"][1]["mutationFingerprint"],
        )


if __name__ == "__main__":
    unittest.main()
