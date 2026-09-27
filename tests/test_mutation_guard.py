import unittest

from niakvio_brain_llm.mutation_guard import validate_mutation

class MutationGuardTests(unittest.TestCase):
    def test_generated_bloc_rejects_contract_placeholder_family(self):
        mutation = {
            "scope": "provider_bloc",
            "operation": "upsert",
            "family": "snake_case_family",
            "find": "return oldResolver();",
            "replace": "return resolveTerminalMedia();",
        }
        with self.assertRaisesRegex(ValueError, "contract placeholder"):
            validate_mutation("demo", mutation)

    def test_provider_data_set_allowed(self):
        validate_mutation("demo", {
            "scope": "provider_data",
            "operation": "set",
            "path": "candidate_api_recipe.base",
            "value": "https://api.real-provider.co",
        })

    def test_placeholder_api_url_rejected(self):
        with self.assertRaises(ValueError):
            validate_mutation("demo", {
                "scope": "provider_data",
                "operation": "set",
                "path": "candidate_api_recipe.base",
                "value": "https://api.example",
            })

    def test_provider_bloc_rejects_synthetic_network_endpoint(self):
        with self.assertRaisesRegex(ValueError, "synthetic or non-provider network endpoint"):
            validate_mutation("demo", {
                "scope": "provider_bloc",
                "operation": "upsert",
                "family": "terminal_response_fallback",
                "find": "const responseUrl = response.url || row.url;",
                "replace": 'const responseUrl = response.url || row.url || "https://invalid.local/";',
            })

    def test_provider_patch_rejects_synthetic_network_endpoint(self):
        with self.assertRaisesRegex(ValueError, "synthetic or non-provider network endpoint"):
            validate_mutation(
                "demo",
                {
                    "scope": "provider_patch",
                    "operation": "unified_diff",
                    "path": "scripts/provider_patches/demo_runtime_v1.py",
                    "diff": (
                        "--- a/scripts/provider_patches/demo_runtime_v1.py\n"
                        "+++ b/scripts/provider_patches/demo_runtime_v1.py\n"
                        "@@ -1 +1 @@\n"
                        "-return response.url\n"
                        "+return response.url || 'https://fallback.test/'\n"
                    ),
                },
                allowed_patch_paths={"scripts/provider_patches/demo_runtime_v1.py"},
            )

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
                "diff": "--- a\n+++ b\n@@\n-old\n+new",
            })

    def test_registered_provider_patch_allowed(self):
        validate_mutation(
            "demo",
            {
                "scope": "provider_patch",
                "operation": "unified_diff",
                "path": "scripts/provider_patches/demo_runtime_v1.py",
                "diff": "--- a/scripts/provider_patches/demo_runtime_v1.py\n+++ b/scripts/provider_patches/demo_runtime_v1.py\n@@ -1 +1 @@\n-old\n+new",
            },
            allowed_patch_paths={"scripts/provider_patches/demo_runtime_v1.py"},
        )

    def test_unregistered_provider_patch_rejected(self):
        with self.assertRaises(ValueError):
            validate_mutation(
                "demo",
                {
                    "scope": "provider_patch",
                    "operation": "unified_diff",
                    "path": "scripts/provider_patches/other_runtime_v1.py",
                    "diff": "--- a/scripts/provider_patches/other_runtime_v1.py\n+++ b/scripts/provider_patches/other_runtime_v1.py\n@@ -1 +1 @@\n-old\n+new",
                },
                allowed_patch_paths={"scripts/provider_patches/demo_runtime_v1.py"},
            )

    def test_placeholder_diff_rejected(self):
        with self.assertRaises(ValueError):
            validate_mutation("demo", {
                "scope": "provider_js",
                "operation": "unified_diff",
                "path": "engine_v2/providers/demo.mjs",
                "diff": "diff_to_replace_extractor",
            })

    def test_clipped_provider_patch_rejected(self):
        with self.assertRaises(ValueError):
            validate_mutation(
                "demo",
                {
                    "scope": "provider_patch",
                    "operation": "unified_diff",
                    "path": "scripts/provider_patches/demo_runtime_v1.py",
                    "diff": (
                        "--- scripts/provider_patches/demo_runtime_v1.py\n"
                        "+++ scripts/provider_patches/demo_runtime_v1.py\n"
                        "@@ -1 +1 @@\n"
                        "-old\n"
                        "+new /* clipped */\n"
                    ),
                },
                allowed_patch_paths={"scripts/provider_patches/demo_runtime_v1.py"},
            )

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
