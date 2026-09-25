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
            (root / "providers").mkdir(parents=True)
            published = (
                "/* BEGIN NIAKVIO_PROVIDER */\n"
                "/* STARTFIX:PROVIDER.DEMO.CONFIG.V1 */\n"
                "/* FIXDATA:PROVIDER.DEMO.CONFIG.V1:" + ("B" * 500) + " */\n"
                "const publishedConfig = 1;\n"
                "/* CLOSEFIX:PROVIDER.DEMO.CONFIG.V1 */\n"
                "/* STARTFIX:PROVIDER.DEMO.RUNTIME.V1 */\n"
                "const publishedRuntime = 'current';\n"
                "/* CLOSEFIX:PROVIDER.DEMO.RUNTIME.V1 */\n"
                "/* END NIAKVIO_PROVIDER */\n"
            )
            (root / "providers" / "demo--nuvio--abc.js").write_text(published)
            (root / "manifest.json").write_text(json.dumps({
                "scrapers": [{
                    "id": "demo",
                    "version": "1.2.3",
                    "filename": "providers/demo--nuvio--abc.js",
                    "supportedTypes": ["movie", "tv"],
                    "formats": ["m3u8"],
                }],
            }))
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
            published_context = context["published_bundle"]
            self.assertEqual(published_context["filename"], "providers/demo--nuvio--abc.js")
            self.assertEqual(published_context["version"], "1.2.3")
            self.assertEqual(len(published_context["providerBlocks"]), 2)
            self.assertIn("publishedRuntime", published_context["providerBlocks"][1]["source"])
            self.assertNotIn("B" * 100, published_context["providerBlocks"][0]["source"])

    def test_hyphenated_provider_reads_published_bloc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "providers").mkdir(parents=True)
            (root / "provider-overrides.json").write_text(json.dumps({"provider_patches": {}}))
            (root / "provider-hubs.json").write_text("{}")
            (root / "providers" / "anime-ultime--nuvio--abc.js").write_text(
                "/* STARTFIX:PROVIDER.ANIME-ULTIME.RUNTIME.V1 */\n"
                "const route = '/current';\n"
                "/* CLOSEFIX:PROVIDER.ANIME-ULTIME.RUNTIME.V1 */\n"
            )
            (root / "manifest.json").write_text(json.dumps({
                "scrapers": [{
                    "id": "anime-ultime",
                    "version": "1.0.1",
                    "filename": "providers/anime-ultime--nuvio--abc.js",
                }],
            }))
            context = build_provider_context(root, "anime-ultime")
            blocks = context["published_bundle"]["providerBlocks"]
            self.assertEqual(len(blocks), 1)
            self.assertEqual(blocks[0]["id"], "PROVIDER.ANIME-ULTIME.RUNTIME.V1")
            self.assertIn("/current", blocks[0]["source"])

if __name__ == "__main__":
    unittest.main()
