import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.advisor_experiments import experiment_fingerprint, next_advisor_experiment
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.niakvio_adapter import _provider_force_negative_memory, _provider_negative_memory, request_from_checkout
from niakvio_brain_llm.prompting import build_force_prompt_payload, compact_request


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "publish_guidance_memory_retention", ROOT / "scripts" / "publish_niakvio_guidance.py"
)
assert SPEC and SPEC.loader
publish = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish)


class AdvisorMemoryRetentionTests(unittest.TestCase):
    def setUp(self):
        self.initial = RepairRequest(provider_id="demo", failure_class="route_proven_gap")
        self.strategy = "search_detail_player_terminal_traversal"
        self.base_fingerprint = experiment_fingerprint(next_advisor_experiment(self.initial, self.strategy))

    def memory_row(self, fingerprint, **changes):
        return {
            "providerId": "demo",
            "profile": "proven_route_terminal_traversal_v1",
            "llmAdvisorExperimentFingerprint": fingerprint,
            "consecutiveFailures": 1,
            "lastOutcome": "rejected",
            "lastReason": "terminal proof missing",
            "executionObserved": True,
            **changes,
        }

    def test_full_registry_prevents_repeating_early_or_late_failed_fingerprint(self):
        for position in (0, 70):
            with self.subTest(position=position), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "automation").mkdir()
                (root / "automation" / "provider-census-status.json").write_text(json.dumps({
                    "providers": [{"provider": "demo", "status": "ROUTE PROVEN"}],
                }))
                rows = [self.memory_row(f"{i + 100:064x}", lastReason=f"reason-{i}") for i in range(80)]
                rows[position] = self.memory_row(self.base_fingerprint, lastReason=f"reason-{position}")
                (root / "automation" / "brain-repair-memory.json").write_text(json.dumps({"entries": rows}))
                request = request_from_checkout(root, "demo")
                history = request.provider_context["advisor_experiment_history"]
                self.assertEqual(len(history), 80)
                experiment = next_advisor_experiment(request, self.strategy)
                self.assertNotEqual(experiment_fingerprint(experiment), self.base_fingerprint)
                observation = next(row for row in request.observations if row["source"] == "brain-repair-memory")
                self.assertEqual(observation["value"][0]["lastReason"], "reason-79")
                compact = compact_request(request, high_confidence=True, mutation_allowed=False)
                self.assertLessEqual(len(compact["provider_context"]["advisor_experiment_history"]), 6)
                self.assertEqual(compact["provider_context"]["advisor_experiment_history"][-1]["lastReason"], "reason-79")

    def test_unexecuted_profile_does_not_block_runtime_or_publication(self):
        for changes in (
            {"executionObserved": False},
            {"executionObserved": False, "lastOutcome": "profile_unavailable"},
        ):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                rows = _provider_negative_memory({"entries": [self.memory_row(self.base_fingerprint, **changes)]}, "demo")
                request = RepairRequest(provider_id="demo", failure_class="route_proven_gap", provider_context={"advisor_experiment_history": rows})
                experiment = next_advisor_experiment(request, self.strategy)
                self.assertEqual(experiment_fingerprint(experiment), self.base_fingerprint)
                root = Path(tmp)
                (root / "automation").mkdir()
                (root / "automation" / "brain-repair-memory.json").write_text(json.dumps({"entries": [self.memory_row(self.base_fingerprint, **changes)]}))
                self.assertEqual(publish.load_blocked_fingerprints(root), {})

    def test_legacy_executed_failure_is_preserved_without_inventing_execution(self):
        row = self.memory_row(self.base_fingerprint)
        del row["executionObserved"]
        rows = _provider_negative_memory({"entries": [row]}, "demo")
        self.assertNotIn("executionObserved", rows[0])
        request = RepairRequest(provider_id="demo", failure_class="route_proven_gap", provider_context={"advisor_experiment_history": rows})
        self.assertNotEqual(experiment_fingerprint(next_advisor_experiment(request, self.strategy)), self.base_fingerprint)

    def test_unavailable_legacy_profile_is_not_executed_evidence(self):
        row = self.memory_row(self.base_fingerprint, lastOutcome="profile_unavailable")
        del row["executionObserved"]
        rows = _provider_negative_memory({"entries": [row]}, "demo")
        request = RepairRequest(provider_id="demo", failure_class="route_proven_gap", provider_context={"advisor_experiment_history": rows})
        self.assertEqual(experiment_fingerprint(next_advisor_experiment(request, self.strategy)), self.base_fingerprint)

    def test_batch_reservation_still_prevents_duplicate_candidate(self):
        row = self.memory_row(self.base_fingerprint, lastOutcome="candidate_reserved")
        del row["executionObserved"]
        request = RepairRequest(provider_id="demo", failure_class="route_proven_gap", provider_context={"advisor_experiment_history": [row]})
        self.assertNotEqual(experiment_fingerprint(next_advisor_experiment(request, self.strategy)), self.base_fingerprint)

    def test_force_registry_retains_all_exclusions_but_prompt_keeps_recent_three(self):
        from niakvio_brain_llm.planner import _force_memory_blocks_mutation, _force_stable_fingerprint
        mutation = {
            "scope": "provider_bloc", "operation": "upsert", "family": "resolve_player",
            "find": "function resolve(){return firstPlayer();}",
            "replace": "function resolve(){return secondPlayer();}",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir()
            (root / "automation" / "provider-census-status.json").write_text(json.dumps({
                "providers": [{"provider": "demo", "status": "ROUTE PROVEN"}],
            }))
            (root / "automation" / "brain-llm-force-memory.json").write_text(json.dumps({
                "entries": [
                    {
                        "providerId": "demo",
                        "mutationFingerprint": _force_stable_fingerprint([mutation]) if index == 0 else f"{index:064x}",
                        "mutationContextFingerprint": f"{index + 100:064x}",
                        "consecutiveFailures": 1,
                        "lastOutcome": "rejected",
                        "lastReason": f"force-reason-{index}",
                    }
                    for index in range(40)
                ],
            }))
            request = request_from_checkout(root, "demo")
            history = request.provider_context["advisor_experiment_history"]
            self.assertEqual(len(history), 40)
            observation = next(row for row in request.observations if row["source"] == "brain-force-sandbox-memory")
            self.assertEqual(len(observation["value"]), 40)
            self.assertEqual(observation["value"][-1]["lastReason"], "force-reason-0")
            self.assertTrue(_force_memory_blocks_mutation(request, mutation))
            prompt = build_force_prompt_payload(request)
            self.assertEqual(
                [row["lastReason"] for row in prompt["prior_force_sandbox_failures"]],
                ["force-reason-39", "force-reason-38", "force-reason-37"],
            )

    def test_force_ingestion_preserves_explicit_nonexecution(self):
        for changes in (
            {"executionObserved": False, "lastOutcome": "rejected"},
            {"lastOutcome": "profile_unavailable"},
        ):
            with self.subTest(changes=changes):
                rows = _provider_force_negative_memory({"entries": [{
                    "providerId": "demo", "consecutiveFailures": 1,
                    "mutationFingerprint": "a" * 64,
                    "mutationContextFingerprint": "b" * 64,
                    **changes,
                }]}, "demo")
                self.assertIs(rows[0]["executionObserved"], False)


if __name__ == "__main__":
    unittest.main()
