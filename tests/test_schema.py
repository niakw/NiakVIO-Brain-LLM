import unittest

from niakvio_brain_llm.schema import REPAIR_PROPOSAL_SCHEMA

class SchemaTests(unittest.TestCase):
    def test_causal_layers_and_mutation_scopes_are_closed(self):
        props = REPAIR_PROPOSAL_SCHEMA["properties"]
        self.assertIn("provider", props["target_layer"]["enum"])
        scopes = props["mutations"]["items"]["properties"]["scope"]["enum"]
        self.assertEqual(set(scopes), {"provider_data", "provider_js"})
        self.assertFalse(REPAIR_PROPOSAL_SCHEMA["additionalProperties"])

if __name__ == "__main__":
    unittest.main()
