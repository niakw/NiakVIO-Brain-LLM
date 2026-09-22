import unittest

from niakvio_brain_llm.schema import REPAIR_PROPOSAL_SCHEMA, proposal_schema_for

class SchemaTests(unittest.TestCase):
    def test_causal_layers_and_mutation_scopes_are_closed(self):
        props = REPAIR_PROPOSAL_SCHEMA["properties"]
        self.assertIn("provider", props["target_layer"]["enum"])
        scopes = props["mutations"]["items"]["properties"]["scope"]["enum"]
        self.assertEqual(set(scopes), {"provider_data", "provider_js"})
        self.assertFalse(REPAIR_PROPOSAL_SCHEMA["additionalProperties"])

    def test_provider_prior_constrains_layer_and_identity(self):
        schema = proposal_schema_for("movix", {
            "target_layer": "provider",
            "confidence": 0.94,
        })
        self.assertEqual(schema["properties"]["provider_id"]["const"], "movix")
        self.assertEqual(schema["properties"]["target_layer"]["enum"], ["provider"])

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
