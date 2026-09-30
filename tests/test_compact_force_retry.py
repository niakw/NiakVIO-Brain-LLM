from pathlib import Path
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import _compact_wire_schema_for
from niakvio_brain_llm.planner import _preserve_selected_function_envelope
from niakvio_brain_llm.prompting import build_force_prompt_payload
from niakvio_brain_llm.prompting import _force_window_kwargs_for_request
from niakvio_brain_llm.schema import compact_force_schema_for


ROOT = Path(__file__).resolve().parents[1]


class CompactForceRetryTest(unittest.TestCase):
    def test_compact_schema_keeps_causal_and_mutation_bounds(self):
        schema = compact_force_schema_for(
            "demo",
            {
                "confidence": 0.97,
                "target_layer": "provider",
                "strategy_prior": "terminal-media-extractor-with-playback-validation",
            },
            {
                "allow_mutations": True,
                "allowed_scopes": ["provider_data"],
            },
            {},
        )
        self.assertEqual(
            set(schema["required"]),
            {
                "provider_id",
                "diagnosis",
                "strategy",
                "confidence",
                "target_layer",
                "mutations",
                "abstain",
                "abstain_reason",
            },
        )
        self.assertEqual(schema["properties"]["provider_id"]["const"], "demo")
        self.assertEqual(schema["properties"]["target_layer"]["enum"], ["provider"])
        self.assertEqual(
            schema["properties"]["strategy"]["const"],
            "terminal-media-extractor-with-playback-validation",
        )
        self.assertEqual(schema["properties"]["mutations"]["maxItems"], 1)
        variants = schema["properties"]["mutations"]["items"]["oneOf"]
        self.assertEqual(
            [row["properties"]["scope"]["const"] for row in variants],
            ["provider_data"],
        )
        self.assertNotIn("experiment", schema["properties"])
        self.assertNotIn("evidence", schema["properties"])
        self.assertNotIn("tests", schema["properties"])

    def test_registered_force_source_remains_exact_before_prompt_clipping(self):
        source = (ROOT / "src" / "niakvio_brain_llm" / "provider_context.py").read_text(encoding="utf-8")
        prompting = (ROOT / "src" / "niakvio_brain_llm" / "prompting.py").read_text(encoding="utf-8")
        self.assertIn("sanitize_exact_source(", source)
        self.assertIn("Prompting owns", source)
        self.assertIn("_force_source_windows(source, request.failure_class, focus_keywords=structural_focus_keywords, **context_window_kwargs)", prompting)
        self.assertIn("_force_source_windows(runtime_source, request.failure_class, focus_keywords=structural_focus_keywords, **context_window_kwargs)", prompting)
        self.assertIn("_force_edit_units(source, request.failure_class, focus_keywords=structural_focus_keywords, **force_window_kwargs)", prompting)
        self.assertIn("_force_edit_units(runtime_source, request.failure_class, focus_keywords=structural_focus_keywords, **force_window_kwargs)", prompting)
        self.assertIn("source_windows", prompting)

    def test_force_prompt_prefill_is_aggressively_bounded(self):
        prompting = (ROOT / "src" / "niakvio_brain_llm" / "prompting.py").read_text(encoding="utf-8")
        self.assertIn('{"max_chars": 2000, "max_windows": 2, "max_units": 4}', prompting)
        self.assertIn('{"max_chars": 1600, "max_windows": 2, "max_units": 3}', prompting)
        self.assertIn('{"max_chars": 1000, "max_windows": 2}', prompting)
        self.assertIn('{"max_chars": 650, "max_windows": 1}', prompting)

    def test_compact_force_prompt_carries_executed_sandbox_failure(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            provider_context={
                "runtimeMutationFilename": "providers/demo.js",
                "runtimeMutationSource": "function resolve(){const normalized=_embeddedText(text);return normalized;}",
                "advisor_experiment_history": [{
                    "memoryRole": "force_sandbox_execution",
                    "consecutiveFailures": 1,
                    "failures": 1,
                    "successes": 0,
                    "lastOutcome": "rejected",
                    "lastReason": "required_category_playable_proof:movie",
                    "lastMutationSummary": [{"scope": "provider_bloc", "operation": "upsert", "family": "resolve_urls"}],
                    "executionObserved": True,
                    "mutationFingerprint": "secret-mutation-fingerprint",
                }],
            },
            allowed_mutations=["provider_bloc"],
        )
        payload = build_force_prompt_payload(
            request,
            {"confidence": 0.96, "target_layer": "provider", "strategy_prior": "search_detail_player_terminal_traversal"},
            {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]},
        )
        failures = payload["prior_force_sandbox_failures"]
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["lastReason"], "required_category_playable_proof:movie")
        self.assertTrue(failures[0]["executionObserved"])
        self.assertEqual(failures[0]["rejectedMechanisms"][0]["family"], "resolve_urls")
        self.assertNotIn("mutationFingerprint", failures[0])

    def test_timeout_retry_uses_compact_planner(self):
        script = (ROOT / "scripts" / "plan_batch_from_checkout.py").read_text(encoding="utf-8")
        planner = (ROOT / "src" / "niakvio_brain_llm" / "planner.py").read_text(encoding="utf-8")
        self.assertIn('if args.mode == "repair" and not args.advisor_only:', script)
        self.assertIn("_force_scope_order", script)
        scope_order = script[script.index("def _force_scope_order"):script.index("def _run_force_scope")]
        self.assertIn("structural_gap =", scope_order)
        self.assertIn("runtime_patch_ready =", scope_order)
        self.assertIn("NIAKVIO_PROVIDER_RUNTIME_RESOLVER_V1", scope_order)
        self.assertIn("MANAGED_FIX_ID", scope_order)
        self.assertIn('".RUNTIME."', scope_order)
        self.assertIn("template_first =", scope_order)
        self.assertIn('runtime_template_prior.get("reuseBeforeNovelBloc")', scope_order)
        self.assertLess(
            scope_order.index('if bloc_ready and structural_gap and template_first:'),
            scope_order.index('if runtime_patch_ready and structural_gap and not template_first:'),
        )
        self.assertIn('and not (structural_gap and template_first)', scope_order)
        self.assertIn("scoped_request.allowed_mutations = [scope]", script)
        self.assertIn("FIELD_BRAIN_FORCE_SCOPE_SELECTED", script)
        self.assertIn("_validation_feedback(", script)
        self.assertIn("except ValueError as validation_exc:", script)
        self.assertIn("timeout_seconds=validation_timeout", script)
        self.assertIn("timeout_seconds=transport_timeout", script)
        self.assertIn("validation_timeout = max(", script)
        self.assertIn("primary_timeout = max(", script)
        self.assertIn("transport_timeout = max(", script)
        self.assertIn("timeout_seconds=primary_timeout", script)
        self.assertIn('max_validation_corrections = 3 if scope == "provider_bloc" else 1', script)
        self.assertIn("for correction_index in range(1, max_validation_corrections + 1):", script)
        self.assertIn("helper_collision", script)
        self.assertIn("helper_declaration_removed", script)
        self.assertIn("preserve its exact original", script)
        self.assertIn("targeted-regression-current", script)
        self.assertIn("prior_feedback", script)
        self.assertIn("window-local edit in the same scope or abstain", script)
        self.assertIn('120 if scope == "provider_bloc" else 90', script)
        self.assertIn("min(int(args.timeout_seconds), 180)", script)
        self.assertIn('budget_seconds = min(budget_cap, 600)', script)
        self.assertIn('300 if status_key == "CHAIN REACHED"', script)
        self.assertIn('else 240', script)
        self.assertIn('exact_runtime_template = bool(', script)
        self.assertNotIn("timeout_seconds=150", script)
        self.assertIn("build_force_prompt_payload(", planner)
        self.assertIn('"required": ["edit", "abstain_reason"]', planner)
        self.assertIn("_compact_wire_schema_for(request, mutation_policy)", planner)
        self.assertIn('_compact_edit_to_mutation(', planner)
        self.assertIn("COMPACT_FORCE_SYSTEM_PROMPT", planner)
        self.assertIn("One edit max", planner)
        workflow = (ROOT / ".github" / "workflows" / "niakvio-private-guidance.yml").read_text(encoding="utf-8")
        self.assertIn("--max-tokens 512", workflow)
        self.assertIn("--timeout-seconds 240", workflow)
        self.assertIn("--force-provider-budget-seconds 600", workflow)
        self.assertIn("retry_tokens = max(", script)
        self.assertIn("prefill_prompt=False", script)
        self.assertIn("force_deadline = time.monotonic() + budget_seconds", script)
        self.assertIn("FIELD_BRAIN_FORCE_PROVIDER_BUDGET_EXHAUSTED", script)
        self.assertNotIn("1280", script)


    def test_force_edit_unit_budget_is_tighter_on_validation_retry(self):
        initial = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            observations=[],
        )
        retry = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            observations=[{"stage": "force_validation_feedback", "reason": "no_op"}],
        )
        self.assertEqual(_force_window_kwargs_for_request(initial)["max_units"], 4)
        self.assertEqual(_force_window_kwargs_for_request(retry)["max_units"], 3)
        self.assertLess(
            _force_window_kwargs_for_request(retry)["max_units"],
            _force_window_kwargs_for_request(initial)["max_units"],
        )

    def test_compact_wire_schema_requires_scope_specific_fields(self):
        patch_request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            provider_context={
                "registered_patch_sources": {
                    "scripts/provider_patches/demo_runtime_v1.py": "return old;",
                },
            },
            allowed_mutations=["provider_patch"],
        )
        patch_schema = _compact_wire_schema_for(
            patch_request,
            {"allowed_scopes": ["provider_patch"]},
        )
        patch_variant = patch_schema["properties"]["edit"]["anyOf"][0]
        self.assertEqual(
            set(patch_variant["required"]),
            {"scope", "path", "unit_id", "replace"},
        )
        self.assertEqual(
            patch_variant["properties"]["path"]["enum"],
            ["scripts/provider_patches/demo_runtime_v1.py"],
        )
        self.assertIn("w1u1", patch_variant["properties"]["unit_id"]["enum"])
        self.assertGreaterEqual(len(patch_variant["properties"]["unit_id"]["enum"]), 1)
        self.assertNotIn("find", patch_variant["properties"])
        self.assertNotIn("window_id", patch_variant["properties"])

        bloc_request = RepairRequest(
            provider_id="demo",
            failure_class="chain_terminal_gap",
            provider_context={"runtimeMutationSource": "function resolve(){return oldResolver();}"},
            allowed_mutations=["provider_bloc"],
        )
        bloc_schema = _compact_wire_schema_for(
            bloc_request,
            {"allowed_scopes": ["provider_bloc"]},
        )
        bloc_variant = bloc_schema["properties"]["edit"]["anyOf"][0]
        self.assertEqual(
            set(bloc_variant["required"]),
            {"scope", "family", "unit_id", "replace"},
        )
        self.assertEqual(
            bloc_variant["properties"]["scope"]["enum"],
            ["provider_bloc"],
        )
        self.assertEqual(bloc_variant["properties"]["family"]["pattern"], "^[a-z][a-z0-9_]{2,48}$")
        self.assertEqual(bloc_variant["properties"]["family"]["minLength"], 3)
        self.assertNotIn("path", bloc_variant["properties"])
        self.assertIn("w1u1", bloc_variant["properties"]["unit_id"]["enum"])
        self.assertGreaterEqual(len(bloc_variant["properties"]["unit_id"]["enum"]), 1)
        self.assertNotIn("find", bloc_variant["properties"])
        self.assertNotIn("window_id", bloc_variant["properties"])



    def test_complete_wrong_function_wrapper_keeps_selected_identity(self):
        find = "async function resolveCandidate(url, ref){return await crawl(url, ref);}"
        wrapped = "async function extractUrls(url, ref){const rows=await crawl(url, ref);return rows.filter(Boolean);}"
        rebuilt = _preserve_selected_function_envelope(find, wrapped, normalize_explicit_wrapper=True)
        self.assertTrue(rebuilt.startswith("async function resolveCandidate(url, ref){"))
        self.assertNotIn("function extractUrls", rebuilt)
        self.assertIn("const rows=await crawl(url, ref);", rebuilt)
        self.assertIn("return rows.filter(Boolean);", rebuilt)

    def test_multiple_function_wrapper_is_not_silently_normalized(self):
        find = "function resolve(url){return crawl(url);}"
        wrapped = "function a(url){return crawl(url);} function b(url){return url;}"
        rebuilt = _preserve_selected_function_envelope(find, wrapped)
        self.assertEqual(rebuilt, wrapped)


if __name__ == "__main__":
    unittest.main()
