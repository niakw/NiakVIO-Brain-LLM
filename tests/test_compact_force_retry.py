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

    def test_timeout_retry_uses_compact_planner(self):
        script = (ROOT / "scripts" / "plan_batch_from_checkout.py").read_text(encoding="utf-8")
        planner = (ROOT / "src" / "niakvio_brain_llm" / "planner.py").read_text(encoding="utf-8")
        self.assertIn(".run(retry_request, compact_force=True)", script)
        self.assertIn("compact_force_schema_for(", planner)
        self.assertIn("COMPACT_FORCE_SYSTEM_PROMPT", planner)
        self.assertIn("Emit at most one mutation.", planner)


if __name__ == "__main__":
    unittest.main()
