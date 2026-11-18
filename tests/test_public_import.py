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

    def test_imports_structured_provider_reverse_prior_without_network_literals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir()
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
