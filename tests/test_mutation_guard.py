import unittest

from niakvio_brain_llm.mutation_guard import validate_mutation

class MutationGuardTests(unittest.TestCase):
    def test_provider_data_set_allowed(self):
        validate_mutation("demo", {
            "scope": "provider_data",
            "operation": "set",
            "path": "apiRecipe.searchRoute",
            "value": "/search/{query}",
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
