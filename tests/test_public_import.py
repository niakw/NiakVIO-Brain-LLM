import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_public_niakvio import collect

class PublicImportTests(unittest.TestCase):
    def test_deduplicates_same_historical_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir()
            case = {
                "id": "hist-a",
                "providers": ["demo"],
                "failureClass": "api_discovery_gap",
                "solutionClass": "discover_api",
                "symptomFamilies": ["obsolete_route"],
                "transferableSignals": ["frontend alive"],
                "lesson": "discover current API",
            }
            payload = {"historicalCases": [case]}
            (root / "automation" / "brain-repair-experience.json").write_text(json.dumps(payload))
            (root / "automation" / "brain-historical-experience-seed.json").write_text(
                json.dumps({"cases": [case]})
            )
            rows = collect(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["strategy"], "discover_api")
            self.assertFalse(rows[0]["proof_authority"])

    def test_rejected_native_bridge_candidate_imports_as_negative_prior_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir()
            entry = {
                "schemaVersion": 1,
                "role": "brain-native-bridge-negative-experiments",
                "experiments": [{
                    "id": "tv-demo-negative",
                    "provider": "french-manga",
                    "runId": "44620517326",
                    "sourceNiakvioSha": "a" * 40,
                    "officialClientSha": "b" * 40,
                    "candidateJsSha256": "c" * 64,
                    "failureClass": "synchronous_native_fetch_no_parallelism",
                    "mechanism": "providerbase_v27_js_promise_hedge",
                    "result": "rejected_executed_no_improvement",
                    "proofAuthority": False,
                    "publicationAuthority": False,
                    "providerMutationAuthority": False,
                    "evidence": {
                        "candidateByteMatched": True,
                        "publishedManifestShaPinnedHttps": True,
                        "runtimeIsOfficialNuvioTV": True,
                        "officialBridgeBlockingCallExecute": True,
                        "nativeRequestSequentialObserved": True,
                        "firstSourceHttpStatus": 522,
                        "returnedStreamCount": 0,
                        "playerReached": False,
                        "decodedMediaVerified": False,
                        "signedUrl": "https://private.invalid/?token=SECRET",
                    },
                }],
            }
            file = root / "automation/native-bridge-negative-experiments.json"
            file.write_text(json.dumps(entry))
            rows = collect(root)
            self.assertEqual(len(rows), 1)
            observed = rows[0]
            self.assertEqual(observed["source"], "official-tv-executed-negative")
            self.assertEqual(observed["result"], "rejected_executed_no_improvement")
            self.assertEqual(observed["failure_class"], "synchronous_native_fetch_no_parallelism")
            self.assertTrue(observed["prior_only"])
            self.assertFalse(observed["proof_authority"])
            self.assertIn("official_tv_call_execute_synchronous", observed["signals"])
            serialized = json.dumps(observed)
            self.assertNotIn("private.invalid", serialized)
            self.assertNotIn("SECRET", serialized)
            for key, value in (
                ("proofAuthority", True),
                ("publicationAuthority", True),
                ("providerMutationAuthority", True),
            ):
                bad = json.loads(json.dumps(entry))
                bad["experiments"][0][key] = value
                file.write_text(json.dumps(bad))
                self.assertEqual(collect(root), [], key)
            bad = json.loads(json.dumps(entry))
            bad["experiments"][0]["evidence"]["candidateByteMatched"] = False
            file.write_text(json.dumps(bad))
            self.assertEqual(collect(root), [])
            bad = json.loads(json.dumps(entry))
            bad["experiments"][0]["evidence"]["playerReached"] = True
            file.write_text(json.dumps(bad))
            self.assertEqual(collect(root), [])

    def test_imports_structured_provider_reverse_prior_without_network_literals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir()
            lego_dir = root / "scripts" / "provider_patches"
            lego_dir.mkdir(parents=True)
            (lego_dir / "sekai_runtime_v1.py").write_text(
                """SECRET='https://secret.example.org/private/player?id=123'\n"""
                """JS=r'''function scripts(html){return html.match(/<script/)}\n"""
                """function resolve(tmdbId,season,episode){var x=atob('YWJj');"""
                """var y=JSON.parse('{}'); return _crawlDirectMedia(['/movie.mp4']);}\n"""
                """// sitemap.xml slug Referer User-Agent iframe #EXTM3U .m3u8\n'''\n"""
            )
            payload = {
                "role": "repair-prior-only",
                "sourceSha": "a" * 40,
                "historicalCases": [],
                "providers": {
                    "sekai": {
                        "strategy": "html_scraper",
                        "providerLegoScripts": ["sekai_runtime_v1.py"],
                        "routeFamilies": ["detail", "player", "api"],
                        "recipeRoles": ["detail", "player"],
                        "recipeMethods": ["GET"],
                        "recipeResponses": ["html-or-text"],
                        "mediaTypes": ["anime"],
                        "hasApiRecipe": False,
                        "hasProviderValuePlan": False,
                        "hasSearchRequestPlan": False,
                        "officialHost": "secret.example.org",
                        "routeTemplates": ["/private/player?id=123"],
                        "requestRecipes": [{
                            "origin": "https://secret.example.org",
                            "route": "/episodesData.js",
                            "body": {"token": "MUST_NOT_SURVIVE"},
                        }],
                    }
                },
            }
            (root / "automation" / "brain-repair-experience.json").write_text(
                json.dumps(payload)
            )
            rows = collect(root)
            priors = [row for row in rows if row.get("source") == "provider-structured-knowledge"]
            self.assertEqual(len(priors), 1)
            row = priors[0]
            self.assertEqual(row["providers"], ["sekai"])
            self.assertEqual(row["provider_recipe"]["lego_families"], ["sekai_runtime_v1"])
            self.assertEqual(row["provider_recipe"]["route_families"], ["detail", "player", "api"])
            self.assertEqual(
                row["provider_recipe"]["mechanisms"],
                [
                    "base64_decode",
                    "direct_media_files",
                    "embed_player_traversal",
                    "hls_playlist_validation",
                    "inline_script_parse",
                    "json_response_parse",
                    "request_header_replay",
                    "season_episode_identity",
                    "sitemap_slug_discovery",
                    "terminal_media_crawl",
                    "tmdb_identity",
                ],
            )
            self.assertFalse(row["proof_authority"])
            self.assertTrue(row["prior_only"])
            encoded = json.dumps(row)
            self.assertNotIn("secret.example.org", encoded)
            self.assertNotIn("episodesData", encoded)
            self.assertNotIn("MUST_NOT_SURVIVE", encoded)
            self.assertNotIn("routeTemplates", encoded)
            self.assertNotIn("requestRecipes", encoded)

if __name__ == "__main__":
    unittest.main()
