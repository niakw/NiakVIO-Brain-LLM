import hashlib
import json
import unittest

from niakvio_brain_llm.backend import StaticBackend
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import BrainPlanner


def fingerprint(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("ascii")).hexdigest()


class PlannerNegativeMemoryTests(unittest.TestCase):
    def plan(self, mutations, *, failed=None, source_digest="a" * 64, execution_observed=True, last_outcome="rejected"):
        path = "scripts/provider_patches/demo_runtime.py"
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            allowed_mutations=["provider_patch", "provider_bloc"],
            provider_context={
                "runtimeMutationSource": "function resolve(){return firstPlayer();}",
                "registered_patch_scripts": [path],
                "registered_patch_sha256": {path: source_digest},
            },
            observations=[{
                "source": "brain-force-sandbox-memory",
                "value": [{
                    "mutationFingerprint": fingerprint(failed or mutations),
                    "mutationContextFingerprint": fingerprint([
                        {"scope": "provider_patch", "path": path, "sha256": "a" * 64},
                    ]),
                    "consecutiveFailures": 1,
                    "lastReason": "required_category_playable_proof:movie",
                    "lastOutcome": last_outcome,
                    "executionObserved": execution_observed,
                }],
            }],
        )
        backend = StaticBackend(json.dumps({
            "provider_id": "demo",
            "diagnosis": "bounded provider repair",
            "strategy": "search_detail_player_terminal_traversal",
            "confidence": 0.96,
            "target_layer": "provider",
            "mutations": mutations,
            "abstain": False,
        }))
        return BrainPlanner(backend).plan(request)

    @staticmethod
    def bloc(replacement="secondPlayer"):
        return {
            "scope": "provider_bloc", "operation": "upsert", "family": "resolve_player",
            "find": "function resolve(){return firstPlayer();}",
            "replace": "function resolve(){return " + replacement + "();}",
        }

    def test_model_cannot_reissue_exact_executed_negative_bloc(self):
        with self.assertRaisesRegex(ValueError, "executed negative memory"):
            self.plan([self.bloc()])

    def test_model_cannot_reissue_exact_negative_patch_on_same_bytes(self):
        mutation = {
            "scope": "provider_patch", "operation": "unified_diff",
            "path": "scripts/provider_patches/demo_runtime.py",
            "diff": "--- a/scripts/provider_patches/demo_runtime.py\n+++ b/scripts/provider_patches/demo_runtime.py\n@@ -1 +1 @@\n-first_player\n+second_player\n",
        }
        with self.assertRaisesRegex(ValueError, "executed negative memory"):
            self.plan([mutation])

    def test_changed_patch_source_permits_current_byte_revalidation(self):
        mutation = {
            "scope": "provider_patch", "operation": "unified_diff",
            "path": "scripts/provider_patches/demo_runtime.py",
            "diff": "--- a/scripts/provider_patches/demo_runtime.py\n+++ b/scripts/provider_patches/demo_runtime.py\n@@ -1 +1 @@\n-first_player\n+second_player\n",
        }
        self.assertEqual(self.plan([mutation], source_digest="b" * 64).mutations, [mutation])

    def test_novel_model_edit_is_still_eligible(self):
        mutation = self.bloc("thirdPlayer")
        self.assertEqual(self.plan([mutation], failed=[self.bloc()]).mutations, [mutation])

    def test_exact_rejected_bundle_is_blocked(self):
        mutations = [self.bloc(), {
            "scope": "provider_bloc", "operation": "upsert", "family": "search_aliases",
            "find": "function search(){return primaryTitle();}",
            "replace": "function search(){return alternateTitle();}",
        }]
        with self.assertRaisesRegex(ValueError, "executed negative memory"):
            self.plan(mutations)

    def test_additional_causal_edit_is_a_distinct_hypothesis(self):
        mutations = [self.bloc(), {
            "scope": "provider_bloc", "operation": "upsert", "family": "search_aliases",
            "find": "function search(){return primaryTitle();}",
            "replace": "function search(){return alternateTitle();}",
        }]
        self.assertEqual(self.plan(mutations, failed=[self.bloc()]).mutations, mutations)

    def test_unexecuted_candidate_is_not_negative_execution_memory(self):
        mutations = [self.bloc()]
        self.assertEqual(self.plan(mutations, execution_observed=False).mutations, mutations)
        self.assertEqual(self.plan(
            mutations, execution_observed=None, last_outcome="profile_unavailable",
        ).mutations, mutations)


if __name__ == "__main__":
    unittest.main()
