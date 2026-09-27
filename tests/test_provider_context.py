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

    def test_full_ok_reference_patterns_are_sanitized_and_optional(self):
        from niakvio_brain_llm.provider_context import build_validated_reference_patterns

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "providers").mkdir(parents=True)
            (root / "scripts" / "provider_patches").mkdir(parents=True)
            (root / "engine_v2" / "providers").mkdir(parents=True)
            (root / "provider-hubs.json").write_text("{}", encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"scrapers": []}), encoding="utf-8")
            (root / "scripts" / "provider_patches" / "peer_runtime_v1.py").write_text(
                "WRAPPER = r'''\n"
                "async function resolvePlayer(url){\n"
                "  const res = await fetch('https://peer.example/watch/123', {headers:{Referer:'/title/123'}});\n"
                "  const html = await res.text();\n"
                "  const iframe = html.match(/iframe/);\n"
                "  return iframe ? 'https://cdn.peer.example/master.m3u8' : null;\n"
                "}\n"
                "'''\n",
                encoding="utf-8",
            )
            (root / "provider-overrides.json").write_text(json.dumps({
                "provider_patches": {
                    "peer": {"patch_scripts": ["scripts/provider_patches/peer_runtime_v1.py"]},
                    "demo": {},
                }
            }), encoding="utf-8")
            census = {
                "providers": [
                    {"provider": "peer", "status": "FULL OK"},
                    {"provider": "demo", "status": "CHAIN REACHED"},
                ]
            }
            refs = build_validated_reference_patterns(
                root,
                "demo",
                "chain_terminal_gap",
                census,
                target_context={"runtimeMutationSource": "function resolve(){return null;}"},
            )
            self.assertTrue(refs)
            self.assertEqual(refs[0]["status"], "FULL OK")
            self.assertTrue(refs[0]["novelty_allowed"])
            self.assertEqual(refs[0]["copy_policy"], "pattern_reference_only")
            self.assertIn("fetch", refs[0]["technical_features"])
            self.assertNotIn("peer.example", refs[0]["snippet"])
            self.assertNotIn("/watch/123", refs[0]["snippet"])
            self.assertNotIn("/title/123", refs[0]["snippet"])
            self.assertNotIn("cdn.peer.example", refs[0]["snippet"])

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

    def test_minified_fixdata_comment_does_not_erase_runtime_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "providers").mkdir(parents=True)
            (root / "provider-overrides.json").write_text(json.dumps({"provider_patches": {}}))
            (root / "provider-hubs.json").write_text("{}")
            one_line = (
                "/* STARTFIX:PROVIDER.DEMO.RUNTIME.V1 */ "
                "/* FIXDATA:PROVIDER.DEMO.RUNTIME.V1:" + ("C" * 500) + " */ "
                "const runtimeStillHere = true; "
                "/* CLOSEFIX:PROVIDER.DEMO.RUNTIME.V1 */"
            )
            (root / "providers" / "demo--nuvio--one.js").write_text(one_line)
            (root / "manifest.json").write_text(json.dumps({
                "scrapers": [{
                    "id": "demo",
                    "version": "1.0.0",
                    "filename": "providers/demo--nuvio--one.js",
                }],
            }))
            context = build_provider_context(root, "demo")
            source = context["published_bundle"]["providerBlocks"][0]["source"]
            self.assertIn("runtimeStillHere", source)
            self.assertIn("FIXDATA blob omitted", source)
            self.assertNotIn("C" * 100, source)

if __name__ == "__main__":
    unittest.main()
