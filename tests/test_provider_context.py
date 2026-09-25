import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.provider_context import build_provider_context

class ProviderContextTests(unittest.TestCase):
    def test_omits_fixdata_blob_and_selects_provider_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "engine_v2" / "providers").mkdir(parents=True)
            (root / "engine_v2" / "providers" / "demo.mjs").write_text(
                "const a = 1;\n/* FIXDATA:DEMO:" + ("A" * 500) + " */\nconst b = 2;\n"
            )
            (root / "scripts" / "provider_patches").mkdir(parents=True)
            (root / "scripts" / "provider_patches" / "demo_runtime_v1.py").write_text(
                "def apply(value):\n    return value\n"
            )
            (root / "provider-overrides.json").write_text(json.dumps({
                "schema_version": 7,
                "provider_patches": {
                    "demo": {
                        "strategy": "search",
                        "provider_lego_scripts": ["scripts/provider_patches/demo_runtime_v1.py"],
                    },
                    "other": {"strategy": "ignore"},
                },
            }))
            (root / "provider-hubs.json").write_text("{}")
            context = build_provider_context(root, "demo")
            self.assertIn("const a = 1", context["authored_module"])
            self.assertNotIn("A" * 100, context["authored_module"])
            self.assertIn("search", context["override"])
            self.assertNotIn("ignore", context["override"])
            self.assertEqual(
                context["registered_patch_scripts"],
                ["scripts/provider_patches/demo_runtime_v1.py"],
            )
            self.assertIn(
                "def apply(value)",
                context["registered_patch_sources"]["scripts/provider_patches/demo_runtime_v1.py"],
            )

if __name__ == "__main__":
    unittest.main()
