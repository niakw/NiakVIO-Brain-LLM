import hashlib
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import (
    RejectedForceUnitError,
    _compact_wire_schema_for,
    _force_unit_for_edit,
    tagged_force_deletion,
)
from niakvio_brain_llm.prompting import (
    _force_edit_units,
    _force_window_kwargs_for_request,
    build_force_prompt_payload,
    selectable_force_units,
    repeated_live_binding_rejection,
)


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

    def test_repeated_removed_binding_rotates_only_after_one_correction(self):
        source = (
            "function searchTitle(q){const dec=find(q);return dec;}\n"
            "function resolvePlayer(u){const dec=parse(u);return dec;}\n"
            "function extractSources(h){return parseSources(h);}\n"
        )
        request = RepairRequest(
            provider_id="synthetic", status="CHAIN REACHED",
            failure_class="chain_terminal_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={"runtimeMutationSource":source,
                              "runtimeMutationFilename":"providers/synthetic.js"},
        )
        policy = {"allow_mutations":True,"allowed_scopes":["provider_bloc"]}
        offered = build_force_prompt_payload(request,{},policy)["new_bloc_target"]["editable_units"]
        self.assertGreaterEqual(len(offered),2)
        unit = offered[0]
        rejection = tagged_force_deletion(
            request, {"scope":"provider_bloc","unit_id":unit["id"]},
            ValueError("compact Force replacement removes live binding still referenced nearby: dec"))
        self.assertIsInstance(rejection, RejectedForceUnitError)
        h = rejection.rejected_unit_sha256
        self.assertFalse(repeated_live_binding_rejection([], "removed_live_binding", h))
        request.observations = [{
            "stage":"force_validation_feedback", "reason":"removed_live_binding",
            "rejected_unit_sha256":h,
        }]
        # First error is recoverable in the same helper.
        still_available = build_force_prompt_payload(request,{},policy)["new_bloc_target"]["editable_units"]
        self.assertTrue(any(u["source"] == unit["source"] for u in still_available))
        self.assertTrue(repeated_live_binding_rejection(
            request.observations,"removed_live_binding",h))
        request.observations.insert(0,{
            "stage":"force_validation_feedback", "reason":"removed_live_binding",
            "rejected_unit_sha256":h, "rotate_unit":True,
        })
        after = build_force_prompt_payload(request,{},policy)["new_bloc_target"]["editable_units"]
        self.assertTrue(after)
        self.assertFalse(any(u["source"] == unit["source"] for u in after))
        self.assertFalse(repeated_live_binding_rejection(
            request.observations,"removed_live_binding","0"*64))
        self.assertFalse(repeated_live_binding_rejection(
            request.observations,"syntax_error",h))

    def test_graphql_error_prioritizes_current_lookup_producer_not_validator(self):
        # An HTTP 200 with GraphQL errors/data:null is not a valid content
        # result. Do not offer terminal guards as a repair for a lookup failure.
        from niakvio_brain_llm.prompting import _force_structural_focus_keywords
        source = (
            "function siteFallback(){return 0;}\n"
            "function verifyEpisodeIdentity(){return true;}\n"
            "function resolve(){return null;}\n"
            "function searchOneAt(q){return apiJson(q);}\n"
            "function findShow(q){return searchOneAt(q);}\n"
            "function apiJson(q){return q;}\n"
        )
        live = {
            "active_functions": [
                "siteFallback", "resolve", "searchOneAt", "findShow",
                "verifyEpisodeIdentity", "apiJson",
            ],
            "network_evidence": [{
                "fixture": "Missing S01E01", "stage": "content_lookup",
                "status": 200,
                "functions": ["resolve", "searchOneAt", "verifyEpisodeIdentity"],
                "response_structure": {
                    "kind": "json",
                    "graphql": {
                        "errorCount": 2, "kinds": ["schema_mismatch"],
                        "dataState": "null", "codes": ["GRAPHQL_VALIDATION_FAILED"],
                        "message": "PRIVATE_REJECTED_QUERY"
                    },
                },
            }],
        }
        request = RepairRequest(
            provider_id="example", status="CHAIN REACHED",
            failure_class="chain_terminal_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={"runtimeMutationSource": source,
                "runtimeMutationFilename": "providers/example.js",
                "live_runtime_evidence": live},
        )
        focus = _force_structural_focus_keywords(request)
        self.assertEqual(focus[0], "function:searchOneAt")
        self.assertEqual(focus[1], "function:findShow")
        self.assertNotIn("function:verifyEpisodeIdentity", focus[:3])
        payload = build_force_prompt_payload(
            request, {}, {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]}
        )
        self.assertIn("function:searchOneAt", payload["structural_focus"])
        self.assertNotIn("PRIVATE_REJECTED_QUERY", str(payload))
        units = payload["new_bloc_target"]["editable_units"]
        self.assertTrue(units)
        self.assertTrue(any("searchOneAt" in str(u.get("source")) for u in units))
        schema = _compact_wire_schema_for(request, {"allow_mutations": True,
                                                       "allowed_scopes": ["provider_bloc"]})
        variants = [v for v in schema["properties"]["edit"]["anyOf"]
                    if v.get("properties", {}).get("scope", {}).get("enum") == ["provider_bloc"]]
        self.assertEqual([u["id"] for u in units],
                         variants[0]["properties"]["unit_id"]["enum"])
        # Successful HTML/JSON without classified GraphQL failure must not
        # override the existing generic function ordering.
        live["network_evidence"][0]["response_structure"] = {"kind": "json"}
        request.provider_context["live_runtime_evidence"] = live
        self.assertEqual(_force_structural_focus_keywords(request)[0],
                         "function:siteFallback")

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

    def test_full_block_body_repeat_is_tagged_as_exact_noop_and_rotates(self):
        source = (
            "async function crawl(q){\n"
            + "".join(f"const observed{i}=q;\n" for i in range(130))
            + "if (q && q.player) { const rows = parse(q); return rows; }\n"
            + "if (q && q.embed) { return embeds(q); }\n"
            + "return [];\n}\n"
        )
        self.assertGreater(len(source), 1800)
        request = RepairRequest(
            provider_id="synthetic", status="CHAIN REACHED",
            failure_class="chain_terminal_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": source,
                "runtimeMutationFilename": "providers/synthetic.js",
                "live_runtime_evidence": {"active_functions": ["crawl"]},
            },
        )
        policy = {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]}
        offered = build_force_prompt_payload(request, {}, policy)["new_bloc_target"]["editable_units"]
        block = next(row for row in offered if row.get("kind") == "block_unit")
        tagged = tagged_force_deletion(
            request,
            {"scope": "provider_bloc", "unit_id": block["id"]},
            ValueError("block_unit replacement repeats current body without a repair"),
        )
        self.assertIsInstance(tagged, RejectedForceUnitError)
        denied = tagged.rejected_unit_sha256
        request.observations = [{
            "stage": "force_validation_feedback",
            "reason": "no_op",
            "rejected_unit_sha256": denied,
            "rotate_unit": True,
        }]
        remaining = build_force_prompt_payload(request, {}, policy)["new_bloc_target"]["editable_units"]
        self.assertTrue(remaining)
        self.assertTrue(all(
            hashlib.sha256(row["source"].encode("utf-8")).hexdigest() != denied
            for row in remaining
        ))

    def test_non_deletion_rejection_does_not_block_source_units(self):
        request = RepairRequest(provider_id="synthetic", failure_class="chain_terminal_gap", allowed_mutations=["provider_bloc"])
        exc = ValueError("compact Force JavaScript syntax validation failed")
        self.assertIs(tagged_force_deletion(
            request, {"scope": "provider_bloc", "unit_id": "w1u1"}, exc), exc)


    def test_memory_ranked_noop_tags_exact_prompt_unit_and_rotates(self):
        """A rejected unit must be resolved with the same live+memory focus as FORCE."""
        source = (
            "function genericList(q){return list(q);}\n"
            "function searchSeason(q){return search(q);}\n"
            "function sitemapSlug(q){return crawl(q);}\n"
            "function extractPlayer(q){return resolve(q);}\n"
        )
        request = RepairRequest(
            provider_id="synthetic",
            status="REGRESSION PROVIDER",
            failure_class="route_proven_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": source,
                "runtimeMutationFilename": "providers/synthetic.js",
            },
        )
        # This is the same focus path passed from the prompt into the schema,
        # converter and, crucially, the rejected-unit fingerprinting branch.
        focus = ("function:extractPlayer", "memory:sitemap", "memory:slug")
        units = _force_edit_units(
            source, request.failure_class,
            focus_keywords=focus, **_force_window_kwargs_for_request(request)
        )
        self.assertGreaterEqual(len(units), 2)
        chosen = units[0]
        expected_sha = hashlib.sha256(chosen["source"].encode("utf-8")).hexdigest()
        tagged = tagged_force_deletion(
            request,
            {"scope": "provider_bloc", "unit_id": chosen["id"]},
            ValueError("compact Force edit is a no-op"),
            focus_keywords=focus,
        )
        self.assertIsInstance(tagged, RejectedForceUnitError)
        self.assertEqual(tagged.rejected_unit_sha256, expected_sha)

        request.observations = [{
            "stage": "force_validation_feedback",
            "reason": "no_op",
            "rejected_unit_sha256": tagged.rejected_unit_sha256,
            "rotate_unit": True,
        }]
        remaining = selectable_force_units(request, _force_edit_units(
            source, request.failure_class,
            focus_keywords=focus, **_force_window_kwargs_for_request(request)
        ))
        self.assertTrue(remaining)
        self.assertNotIn(expected_sha, {
            hashlib.sha256(unit["source"].encode("utf-8")).hexdigest()
            for unit in remaining
        })


if __name__ == "__main__":
    unittest.main()
