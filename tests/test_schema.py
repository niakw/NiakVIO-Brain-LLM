import unittest

from niakvio_brain_llm.schema import EXPERIMENT_SPEC_SCHEMA, REPAIR_PROPOSAL_SCHEMA, proposal_schema_for

class SchemaTests(unittest.TestCase):
    def test_mutation_variants_are_scope_specific(self):
        variants = REPAIR_PROPOSAL_SCHEMA["properties"]["mutations"]["items"]["oneOf"]
        scopes = {variant["properties"]["scope"]["const"] for variant in variants}
        self.assertEqual(scopes, {"provider_data", "provider_patch", "provider_js"})
        self.assertFalse(REPAIR_PROPOSAL_SCHEMA["additionalProperties"])

    def test_experiment_spec_is_abstract_and_bounded(self):
        self.assertFalse(EXPERIMENT_SPEC_SCHEMA["additionalProperties"])
        props=EXPERIMENT_SPEC_SCHEMA["properties"]
        self.assertEqual(props["max_depth"]["maximum"],6)
        self.assertEqual(props["max_pages"]["maximum"],36)
        self.assertEqual(props["role_order"]["maxItems"],7)
        self.assertIn("experiment",REPAIR_PROPOSAL_SCHEMA["properties"])

    def test_high_confidence_provider_prior_requires_full_experiment(self):
        schema = proposal_schema_for(
            "demo",
            causal_prior={
                "confidence": 0.96,
                "target_layer": "provider",
                "strategy_prior": "search-detail-player-terminal-traversal",
            },
        )
        self.assertIn("experiment", schema["required"])
        required = set(schema["properties"]["experiment"]["required"])
        self.assertEqual(required, set(EXPERIMENT_SPEC_SCHEMA["properties"]))

    def test_provider_prior_constrains_layer_strategy_identity_and_scope(self):
        schema = proposal_schema_for(
            "movix",
            {
                "target_layer": "provider",
                "confidence": 0.96,
                "strategy_prior": "discover_api_from_current_page_and_bundles",
            },
            {
                "allow_mutations": True,
                "allowed_scopes": ["provider_data"],
                "force_abstain": False,
            },
        )
        self.assertEqual(schema["properties"]["provider_id"]["const"], "movix")
        self.assertEqual(schema["properties"]["target_layer"]["enum"], ["provider"])
        self.assertEqual(
            schema["properties"]["strategy"]["const"],
            "discover_api_from_current_page_and_bundles",
        )
        variants = schema["properties"]["mutations"]["items"]["oneOf"]
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0]["properties"]["scope"]["const"], "provider_data")

    def test_registered_provider_patch_paths_are_constrained(self):
        schema = proposal_schema_for(
            "demo",
            {"target_layer": "provider", "confidence": 0.96, "strategy_prior": "search-detail-player-terminal-traversal"},
            {"allow_mutations": True, "allowed_scopes": ["provider_patch"], "force_abstain": False},
            {"registered_patch_scripts": ["scripts/provider_patches/demo_runtime_v1.py"]},
        )
        variants = schema["properties"]["mutations"]["items"]["oneOf"]
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0]["properties"]["scope"]["const"], "provider_patch")
        self.assertEqual(
            variants[0]["properties"]["path"]["enum"],
            ["scripts/provider_patches/demo_runtime_v1.py"],
        )

    def test_harness_policy_forbids_mutation_and_forces_abstain(self):
        schema = proposal_schema_for(
            "demo",
            {
                "target_layer": "harness",
                "confidence": 0.99,
                "strategy_prior": "compare_browser_native_residential_profiles_without_provider_mutation",
            },
            {
                "allow_mutations": False,
                "allowed_scopes": [],
                "force_abstain": True,
            },
        )
        self.assertEqual(schema["properties"]["target_layer"]["enum"], ["harness"])
        self.assertEqual(schema["properties"]["mutations"]["maxItems"], 0)
        self.assertTrue(schema["properties"]["abstain"]["const"])
        self.assertEqual(schema["properties"]["tests"]["minItems"], 1)

if __name__ == "__main__":
    unittest.main()
