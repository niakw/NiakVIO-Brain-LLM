import hashlib
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import (
    RejectedForceUnitError,
    _compact_wire_schema_for,
    _force_unit_for_edit,
    tagged_force_deletion,
)
from niakvio_brain_llm.prompting import build_force_prompt_payload, selectable_force_units


class ForceRejectedUnitDiversification(unittest.TestCase):
    def test_deleted_exact_source_is_excluded_even_when_unit_ids_reorder(self):
        source = (
            "function searchTitle(query){return fetchTitle(query);}\n"
            "function resolvePlayer(url){return fetchPlayer(url);}\n"
            "function extractSources(html){return parseSources(html);}\n"
        )
        request = RepairRequest(
            provider_id="synthetic", status="CHAIN REACHED",
            failure_class="chain_terminal_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": source,
                "runtimeMutationFilename": "providers/synthetic.js",
            },
        )
        policy = {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]}
        base = build_force_prompt_payload(request, {}, policy)
        offered = base["new_bloc_target"]["editable_units"]
        self.assertGreaterEqual(len(offered), 2)
        first = offered[0]
        unit_id = first["id"]
        expected_hash = hashlib.sha256(first["source"].encode("utf-8")).hexdigest()
        rejected = tagged_force_deletion(
            request,
            {"scope": "provider_bloc", "unit_id": unit_id},
            ValueError("compact Force traversal repair may not be a pure deletion of existing logic"),
        )
        self.assertIsInstance(rejected, RejectedForceUnitError)
        self.assertEqual(rejected.rejected_unit_sha256, expected_hash)
        request.observations = [{
            "stage": "force_validation_feedback", "reason": "causally_empty_deletion",
            "rejected_unit_sha256": rejected.rejected_unit_sha256,
        }]
        after = build_force_prompt_payload(request, {}, policy)
        remaining = after["new_bloc_target"]["editable_units"]
        self.assertTrue(remaining)
        self.assertTrue(all(
            hashlib.sha256(u["source"].encode("utf-8")).hexdigest() != expected_hash
            for u in remaining
        ))
        wire = _compact_wire_schema_for(request, policy)
        variants = [v for v in wire["properties"]["edit"]["anyOf"]
                    if v.get("properties", {}).get("scope", {}).get("enum") == ["provider_bloc"]]
        self.assertEqual(len(variants), 1)
        self.assertEqual([u["id"] for u in remaining],
                         variants[0]["properties"]["unit_id"]["enum"])
        allowed, _ = _force_unit_for_edit(request, source, remaining[0]["id"])
        self.assertNotEqual(hashlib.sha256(allowed["source"].encode("utf-8")).hexdigest(),
                            expected_hash)

    def test_noop_retries_rotate_exact_source_without_losing_other_units(self):
        source = (
            "function searchTitle(q){return fetchTitle(q);}\n"
            "function resolvePlayer(u){return fetchPlayer(u);}\n"
            "function extractSources(h){return parseSources(h);}\n"
        )
        request = RepairRequest(
            provider_id="synthetic", status="CHAIN REACHED",
            failure_class="chain_terminal_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={"runtimeMutationSource": source,
                              "runtimeMutationFilename": "providers/synthetic.js"},
        )
        policy = {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]}
        offered = build_force_prompt_payload(request, {}, policy)["new_bloc_target"]["editable_units"]
        self.assertGreaterEqual(len(offered), 3)
        excluded = offered[:2]
        request.observations = []
        for row in excluded:
            exc = tagged_force_deletion(request,
                {"scope": "provider_bloc", "unit_id": row["id"]},
                ValueError("compact Force edit is a no-op"))
            self.assertIsInstance(exc, RejectedForceUnitError)
            request.observations.append({
                "stage": "force_validation_feedback",
                "reason": "no_op",
                "rejected_unit_sha256": exc.rejected_unit_sha256,
            })
        after = build_force_prompt_payload(request, {}, policy)["new_bloc_target"]["editable_units"]
        denied = {hashlib.sha256(row["source"].encode("utf-8")).hexdigest()
                  for row in excluded}
        self.assertTrue(after)
        self.assertTrue(all(hashlib.sha256(row["source"].encode("utf-8")).hexdigest()
                            not in denied for row in after))
        wire = _compact_wire_schema_for(request, policy)
        variants = [v for v in wire["properties"]["edit"]["anyOf"]
                    if v.get("properties", {}).get("scope", {}).get("enum") == ["provider_bloc"]]
        self.assertEqual([u["id"] for u in after],
                         variants[0]["properties"]["unit_id"]["enum"])

    def test_non_deletion_rejection_does_not_block_source_units(self):
        request = RepairRequest(provider_id="synthetic", failure_class="chain_terminal_gap", allowed_mutations=["provider_bloc"])
        exc = ValueError("compact Force JavaScript syntax validation failed")
        self.assertIs(tagged_force_deletion(
            request, {"scope": "provider_bloc", "unit_id": "w1u1"}, exc), exc)


if __name__ == "__main__":
    unittest.main()
