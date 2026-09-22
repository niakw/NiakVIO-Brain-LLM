import unittest

from niakvio_brain_llm.mutation_guard import validate_mutation

class MutationGuardTests(unittest.TestCase):
    def test_provider_data_set_allowed(self):
        validate_mutation("demo", {
            "scope": "provider_data",
            "operation": "set",
            "path": "candidate_api_recipe.searchRoute",
            "value": "/search/{query}",
        })

    def test_file_like_provider_data_path_rejected(self):
        with self.assertRaises(ValueError):
            validate_mutation("demo", {
                "scope": "provider_data",
                "operation": "set",
                "path": "engine_v2/providers/demo/mjs",
                "value": {"ua": "x"},
            })

    def test_unknown_provider_data_root_rejected(self):
        with self.assertRaises(ValueError):
            validate_mutation("demo", {
                "scope": "provider_data",
                "operation": "set",
                "path": "randomThing.foo",
                "value": True,
            })

    def test_cross_provider_js_patch_rejected(self):
        with self.assertRaises(ValueError):
            validate_mutation("demo", {
                "scope": "provider_js",
                "operation": "unified_diff",
                "path": "engine_v2/providers/other.mjs",
                "diff": "--- a\n+++ b",
            })

    def test_proto_path_rejected(self):
        with self.assertRaises(ValueError):
            validate_mutation("demo", {
                "scope": "provider_data",
                "operation": "set",
                "path": "__proto__.polluted",
                "value": True,
            })

if __name__ == "__main__":
    unittest.main()
