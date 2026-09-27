from pathlib import Path
import unittest

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
        self.assertIn("_force_source_windows(source, request.failure_class)", prompting)
        self.assertIn("_force_source_windows(runtime_source, request.failure_class)", prompting)
        self.assertIn("source_windows", prompting)

    def test_timeout_retry_uses_compact_planner(self):
        script = (ROOT / "scripts" / "plan_batch_from_checkout.py").read_text(encoding="utf-8")
        planner = (ROOT / "src" / "niakvio_brain_llm" / "planner.py").read_text(encoding="utf-8")
        self.assertIn('if args.mode == "repair" and not args.advisor_only:', script)
        self.assertIn("_force_scope_order", script)
        self.assertIn("scoped_request.allowed_mutations = [scope]", script)
        self.assertIn("FIELD_BRAIN_FORCE_SCOPE_SELECTED", script)
        self.assertIn(".run(retry_request, compact_force=True)", script)
        self.assertIn("retry_timeout = max(", script)
        self.assertIn("min(int(args.timeout_seconds) + 90, 240)", script)
        self.assertNotIn("timeout_seconds=150", script)
        self.assertIn("build_force_prompt_payload(", planner)
        self.assertIn('"required": ["edit", "abstain_reason"]', planner)
        self.assertIn('"required": ["scope"]', planner)
        self.assertNotIn('"required": ["scope", "path"]', planner)
        self.assertIn('_compact_edit_to_mutation(', planner)
        self.assertIn("COMPACT_FORCE_SYSTEM_PROMPT", planner)
        self.assertIn("Emit at most one edit.", planner)
        workflow = (ROOT / ".github" / "workflows" / "niakvio-private-guidance.yml").read_text(encoding="utf-8")
        self.assertIn("--max-tokens 512", workflow)
        self.assertIn("--timeout-seconds 120", workflow)
        self.assertIn("retry_tokens = max(", script)
        self.assertNotIn("1280", script)


if __name__ == "__main__":
    unittest.main()
