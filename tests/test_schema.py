import unittest

from niakvio_brain_llm.schema import REPAIR_PROPOSAL_SCHEMA, proposal_schema_for

class SchemaTests(unittest.TestCase):
    def test_mutation_variants_are_scope_specific(self):
        variants = REPAIR_PROPOSAL_SCHEMA["properties"]["mutations"]["items"]["oneOf"]
        scopes = {variant["properties"]["scope"]["const"] for variant in variants}
        self.assertEqual(scopes, {"provider_data", "provider_js"})
        self.assertFalse(REPAIR_PROPOSAL_SCHEMA["additionalProperties"])

    def test_provider_prior_constrains_layer_and_identity(self):
        schema = proposal_schema_for("movix", {
            "target_layer": "provider",
            "confidence": 0.94,
        })
        self.assertEqual(schema["properties"]["provider_id"]["const"], "movix")
        self.assertEqual(schema["properties"]["target_layer"]["enum"], ["provider"])
        js_variant = schema["properties"]["mutations"]["items"]["oneOf"][1]
        self.assertEqual(
            js_variant["properties"]["path"]["const"],
            "engine_v2/providers/movix.mjs",
        )

    def test_harness_prior_forbids_mutation(self):
        schema = proposal_schema_for("demo", {
            "target_layer": "harness",
            "confidence": 0.99,
        })
        self.assertEqual(schema["properties"]["target_layer"]["enum"], ["harness"])
        self.assertEqual(schema["properties"]["mutations"]["maxItems"], 0)
        self.assertTrue(schema["properties"]["abstain"]["const"])

if __name__ == "__main__":
    unittest.main()
