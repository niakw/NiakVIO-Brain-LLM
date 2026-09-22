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
            (root / "provider-overrides.json").write_text(json.dumps({
                "demo": {"strategy": "search"},
                "other": {"strategy": "ignore"},
            }))
            (root / "provider-hubs.json").write_text("{}")
            context = build_provider_context(root, "demo")
            self.assertIn("const a = 1", context["authored_module"])
            self.assertNotIn("A" * 100, context["authored_module"])
            self.assertIn("search", context["override"])
            self.assertNotIn("ignore", context["override"])

if __name__ == "__main__":
    unittest.main()
