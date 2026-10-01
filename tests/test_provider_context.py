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
                'MANAGED_FIX_ID = "PROVIDER.DEMO.RUNTIME.V1"\n'
                "def apply(value):\n    return value\n"
            )
            (root / "provider-overrides.json").write_text(json.dumps({
                "schema_version": 7,
                "provider_patches": {
                    "demo": {
                        "strategy": "search",
                        "capability": "html_scraper",
                        "learned_routes": ["/?s={query}"],
                        "candidate_learned_routes": ["/detail/{slug}", "https://provider.example/player?id={id}"],
                        "search_request_plan": [{
                            "base": "https://provider.example",
                            "route": "/?s={query}",
                            "requestSpec": {
                                "method": "GET",
                                "headers": {
                                    "Accept": "text/html",
                                    "Authorization": "secret",
                                },
                            },
                            "sourceRole": "catalog-search",
                            "semanticTypes": ["movie", "tv"],
                        }],
                        "route_proof": {
                            "provenRouteCount": 1,
                            "runtimePlanRouteCount": 2,
                            "canonicalExecutionPreference": [{
                                "owner": "route",
                                "route": "/?s={query}",
                                "lanes": ["movie", "tv"],
                            }],
                        },
                        "live_route_gate": {
                            "completion_state": "declared-types-qualified",
                            "provider_request_count": 7,
                            "live_validated_route_count": 2,
                            "runtime_derived_route_count": 3,
                        },
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
            route_contract = context["route_contract"]
            self.assertEqual(route_contract["capability"], "html_scraper")
            self.assertEqual(route_contract["learnedRoutes"], ["/?s={query}"])
            self.assertIn("/detail/{slug}", route_contract["candidateRoutes"])
            self.assertIn("/player?id={id}", route_contract["candidateRoutes"])
            self.assertEqual(route_contract["plans"][0]["method"], "GET")
            self.assertEqual(route_contract["plans"][0]["headerNames"], ["Accept"])
            self.assertEqual(route_contract["canonicalPreference"][0]["owner"], "route")
            self.assertEqual(route_contract["liveEvidence"]["validatedRoutes"], 2)
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
            self.assertNotIn("providerBlockSources", published_context)
            self.assertEqual(
                context["preferredRuntimeMutationBlockId"],
                "PROVIDER.DEMO.RUNTIME.V1",
            )
            self.assertIn(
                "publishedRuntime",
                context["preferredRuntimeMutationSource"],
            )
            self.assertEqual(
                context["runtime_template_prior"]["mode"],
                "reuse_current_provider_runtime_skeleton",
            )
            self.assertTrue(context["runtime_template_prior"]["reuseBeforeNovelBloc"])
            self.assertNotIn(
                "publishedConfig",
                context["preferredRuntimeMutationSource"],
            )

    def test_runtime_variant_coverage_flags_premature_global_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts" / "provider_patches").mkdir(parents=True)
            (root / "scripts" / "provider_patches" / "demo_runtime_v1.py").write_text(
                'MANAGED_FIX_ID = "PROVIDER.DEMO.RUNTIME.V1"\n'
                'WRAPPER = r"""function quality(f){return /(2160|1080|720|480)p/.test(f)} '
                'async function resolve(links){var out=[];for(var i=0;i<links.length;i++){'
                'var rows=await source(links[i]);for(var j=0;j<rows.length;j++)out.push(rows[j]);'
                'if(out.length>=4)break}return out}"""\n',
                encoding="utf-8",
            )
            (root / "provider-overrides.json").write_text(json.dumps({
                "provider_patches": {
                    "demo": {
                        "provider_lego_scripts": ["scripts/provider_patches/demo_runtime_v1.py"]
                    }
                }
            }), encoding="utf-8")
            (root / "provider-hubs.json").write_text("{}", encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"scrapers": []}), encoding="utf-8")
            context = build_provider_context(root, "demo")
            risk = context["runtime_variant_coverage"]
            self.assertEqual(risk["riskKind"], "variant-coverage-truncation")
            self.assertEqual(risk["risk"], "high")
            self.assertIn("global_output_quota_break", risk["mechanisms"])
            self.assertIn("quality", risk["dimensions"])
            self.assertIn("2160p", risk["qualityHints"])
            self.assertFalse(risk["proofAuthority"])

    def test_stremio_route_shape_prefers_shared_json_renderer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "provider-overrides.json").write_text(json.dumps({
                "provider_patches": {
                    "demo": {
                        "learned_routes": [
                            "/stream/movie/{imdbId}.json",
                            "/stream/series/{imdbId}:{season}:{episode}.json",
                        ],
                    }
                }
            }), encoding="utf-8")
            (root / "provider-hubs.json").write_text("{}", encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"scrapers": []}), encoding="utf-8")
            (root / "automation").mkdir()
            (root / "automation" / "provider-v3-static-knowledge.json").write_text(
                json.dumps({"providers": {"demo": {"model": {"sourceRuntimeFamily": "unknown"}}}}),
                encoding="utf-8",
            )
            context = build_provider_context(root, "demo")
            prior = context["runtime_template_prior"]
            self.assertEqual(prior["mode"], "reuse_recognized_family_renderer")
            self.assertEqual(
                prior["template"],
                "scripts/provider_patches/stremio_json_runtime_common.py",
            )
            self.assertTrue(prior["reuseBeforeNovelBloc"])

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
