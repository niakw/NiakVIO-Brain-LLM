from __future__ import annotations

import importlib.util
from pathlib import Path
import hashlib
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import RejectedForceUnitError
from niakvio_brain_llm.prompting import (
    _force_window_kwargs_for_request, build_force_prompt_payload,
    selectable_force_units,
)
from niakvio_brain_llm.planner import _compact_wire_schema_for

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "plan_batch_from_checkout.py"
SPEC = importlib.util.spec_from_file_location("force_portfolio_memory", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class ForcePortfolioRejectedUnitMemoryTests(unittest.TestCase):
    def test_rotated_exact_unit_hashes_survive_portfolio_without_source_bytes(self):
        first = "a" * 64
        second = "b" * 64
        observations = [
            {
                "stage": "force_validation_feedback",
                "reason": "no_op",
                "rejected_unit_sha256": first,
                "rotate_unit": True,
                "private_source": "MUST_NOT_SURVIVE",
            },
            {
                "stage": "force_validation_feedback",
                "reason": "causally_empty_deletion",
                "rejected_unit_sha256": second,
                "rotate_unit": True,
            },
            {
                "stage": "force_validation_feedback",
                "reason": "no_op",
                "rejected_unit_sha256": first,
                "rotate_unit": True,
            },
            {
                "stage": "force_validation_feedback",
                "reason": "syntax_error",
                "rejected_unit_sha256": "c" * 64,
                "rotate_unit": True,
            },
            {
                "stage": "force_validation_feedback",
                "reason": "no_op",
                "rejected_unit_sha256": "d" * 64,
                "rotate_unit": False,
            },
        ]
        hashes = mod.force_rejected_unit_hashes(observations)
        self.assertEqual(hashes, [first, second])
        rows = mod.force_portfolio_rejected_feedback(hashes)
        self.assertEqual([row["rejected_unit_sha256"] for row in rows], hashes)
        self.assertTrue(all(row["rotate_unit"] is True for row in rows))
        self.assertTrue(all(row["reason"] == "no_op" for row in rows))
        encoded = repr(rows)
        self.assertNotIn("MUST_NOT_SURVIVE", encoded)
        self.assertNotIn("private_source", encoded)

    def test_portfolio_rejected_units_are_fallback_not_lifetime_ban(self):
        first = {"id": "w1u1", "source": "const player = firstPlayer();"}
        second = {"id": "w1u2", "source": "const media = secondSource();"}
        third = {"id": "w1u3", "source": "return terminalMedia;"}
        first_hash = hashlib.sha256(first["source"].encode("utf-8")).hexdigest()
        second_hash = hashlib.sha256(second["source"].encode("utf-8")).hexdigest()

        request = RepairRequest(
            provider_id="sekai",
            failure_class="route_proven_gap",
            observations=mod.force_portfolio_rejected_feedback([first_hash, second_hash]),
        )
        # A fresh causal unit outranks both same-run rejected units.
        self.assertEqual(selectable_force_units(request, [first, second, third]), [third])
        # Once all fresh units are exhausted, a later hypothesis may revisit
        # the exact source unit with a different edit/mechanism.
        self.assertEqual(selectable_force_units(request, [first, second]), [first, second])

        # Immediate validation feedback is still a hard rotation and never
        # reopens the rejected unit inside the same correction chain.
        request.observations = [{
            "stage": "force_validation_feedback",
            "reason": "no_op",
            "rejected_unit_sha256": first_hash,
            "rotate_unit": True,
        }]
        self.assertEqual(selectable_force_units(request, [first]), [])

    def test_malformed_hashes_never_become_portfolio_memory(self):
        self.assertEqual(mod.force_portfolio_rejected_feedback([
            "", "x" * 64, "a" * 63, "a" * 65
        ]), [])
        self.assertEqual(mod.force_rejected_unit_hashes([
            {
                "stage": "force_validation_feedback",
                "reason": "no_op",
                "rejected_unit_sha256": "not-a-sha",
                "rotate_unit": True,
            }
        ]), [])


    def test_failed_correction_chain_carries_only_exact_unit_hashes(self):
        first = "a" * 64
        second = "b" * 64
        error = RejectedForceUnitError(
            "private provider URL and model output must not be persisted", second
        )
        error.rejected_unit_sha256s = [first, "not-a-sha", first]
        carried = mod.force_rejected_error_hashes(error)
        self.assertEqual(carried, [first, second])
        self.assertEqual(mod.force_rejected_error_hashes(None), [])

        # Even when there was no successful proposal row, this sanitized
        # error is enough to rank rejected units behind fresh units next time.
        rows = mod.force_portfolio_rejected_feedback(carried)
        self.assertEqual([row["rejected_unit_sha256"] for row in rows],
                         [first, second])
        self.assertNotIn("private provider URL", repr(rows))
        self.assertNotIn("model output", repr(rows))

    def test_later_portfolio_hypothesis_retains_prior_hashes(self):
        first = "a" * 64
        second = "b" * 64
        already = mod.force_portfolio_rejected_feedback([first])
        combined = mod.force_portfolio_rejected_feedback([
            *mod.force_rejected_unit_hashes(already), second,
        ])
        self.assertEqual(
            [row["rejected_unit_sha256"] for row in combined],
            [first, second],
        )
        fresh = {"id": "w1u3", "source": "return newTerminalRoute;"}
        previously_rejected = [
            {"id": "w1u1", "source": "return candidateOne;"},
            {"id": "w1u2", "source": "return candidateTwo;"},
        ]
        original_hashes = [
            hashlib.sha256(row["source"].encode("utf-8")).hexdigest()
            for row in previously_rejected
        ]
        request = RepairRequest(
            provider_id="synthetic", failure_class="route_proven_gap",
            observations=mod.force_portfolio_rejected_feedback(original_hashes),
        )
        self.assertEqual(
            selectable_force_units(request, [*previously_rejected, fresh]),
            [fresh],
        )


    def test_route_graph_expands_only_after_two_distinct_exact_failures(self):
        source = (
            "async function resolve(q){return await search(q);}\n"
            "async function search(q){return await player(q);}\n"
            "async function player(q){return await extract(q);}\n"
            "async function extract(q){return parseMedia(q);}\n"
            "function parseMedia(q){return q || []; }\n"
            "function normalize(q){return q;}\n"
        )
        request = RepairRequest(
            provider_id="synthetic", status="REGRESSION PROVIDER",
            failure_class="route_proven_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "preferredRuntimeMutationSource": source,
                "runtimeMutationSource": source,
                "runtimeMutationFilename": "providers/synthetic.js",
                "runtime_template_prior": {"reuseBeforeNovelBloc": True},
            },
        )
        policy = {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]}
        baseline = build_force_prompt_payload(request, {}, policy)
        first_units = baseline["new_bloc_target"]["editable_units"]
        self.assertEqual(len(first_units), 2)
        self.assertEqual(_force_window_kwargs_for_request(request)["max_units"], 2)
        hashes = [
            hashlib.sha256(unit["source"].encode("utf-8")).hexdigest()
            for unit in first_units
        ]
        # One rejected current function must not widen the normal CPU prompt.
        request.observations = mod.force_portfolio_rejected_feedback(hashes[:1])
        self.assertEqual(_force_window_kwargs_for_request(request)["max_units"], 2)
        # Exhausting both exact units permits a bounded two-window/four-unit
        # causal fallback. The two old units remain lower priority.
        request.observations = mod.force_portfolio_rejected_feedback(hashes)
        expanded = build_force_prompt_payload(request, {}, policy)
        self.assertEqual(_force_window_kwargs_for_request(request)["max_units"], 4)
        new_units = expanded["new_bloc_target"]["editable_units"]
        self.assertGreater(len(new_units), 0)
        self.assertTrue(all(
            hashlib.sha256(unit["source"].encode("utf-8")).hexdigest() not in hashes
            for unit in new_units
        ), "fresh causal functions must be offered before portfolio rejects")
        wire = _compact_wire_schema_for(request, policy)
        variant = next(v for v in wire["properties"]["edit"]["anyOf"]
                       if v.get("properties", {}).get("scope", {}).get("enum")
                       == ["provider_bloc"])
        self.assertEqual([u["id"] for u in new_units],
                         variant["properties"]["unit_id"]["enum"])
        # No valid source-backed replacement is published without conversion,
        # materialization and downstream replay; this is an edit-surface test.


if __name__ == "__main__":
    unittest.main()
