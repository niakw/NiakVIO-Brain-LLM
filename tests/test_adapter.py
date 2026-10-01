import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.niakvio_adapter import request_from_checkout

class AdapterTests(unittest.TestCase):
    def test_builds_request_without_writing_source_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir()
            census = {
                "providers": [
                    {
                        "provider": "demo",
                        "status": "CHAIN REACHED",
                        "dominantIssue": "terminal_extractor",
                        "declaredLanes": ["movie"],
                        "repairEligible": True,
                        "brainCheckRequired": True,
                        "evidenceDepth": ["movie=chain_reached"],
                    },
                    {"provider": "healthy", "status": "FULL OK"},
                ]
            }
            (root / "automation" / "provider-census-status.json").write_text(json.dumps(census))
            (root / "automation" / "brain-repair-experience.json").write_text("{}")
            (root / "automation" / "brain-repair-memory.json").write_text("{}")
            (root / "automation" / "brain-llm-force-memory.json").write_text(json.dumps({
                "entries": [
                    {
                        "providerId": "demo",
                        "mutationFingerprint": f"{index:064x}",
                        "mutationContextFingerprint": f"{index + 100:064x}",
                        "consecutiveFailures": 1,
                        "failures": 1,
                        "successes": 0,
                        "lastOutcome": "rejected",
                        "lastReason": f"sandbox-{index}",
                        "lastMutationSummary": [{
                            "scope": "provider_bloc",
                            "operation": "upsert",
                            "family": f"family_{index}",
                        }],
                    }
                    for index in range(1, 7)
                ]
            }))
            (root / "scripts" / "provider_patches").mkdir(parents=True)
            (root / "scripts" / "provider_patches" / "healthy_runtime_v1.py").write_text(
                "WRAPPER = r'''async function resolve(){const r=await fetch('/x');return r;}'''\n"
            )
            (root / "provider-overrides.json").write_text(json.dumps({
                "provider_patches": {
                    "healthy": {"patch_scripts": ["scripts/provider_patches/healthy_runtime_v1.py"]},
                    "demo": {},
                }
            }))
            (root / "provider-hubs.json").write_text("{}")
            (root / "manifest.json").write_text(json.dumps({"scrapers": []}))
            req = request_from_checkout(root, "demo")
            self.assertEqual(req.failure_class, "chain_terminal_gap")
            self.assertEqual(req.supported_types, ["movie"])
            self.assertTrue(req.provider_context["read_only"])
            self.assertTrue(req.census_prior["brainCheckRequired"])
            self.assertIn("validated_reference_patterns", req.provider_context)
            self.assertTrue(req.provider_context["validated_reference_patterns"][0]["novelty_allowed"])
            force_observation = next(
                row for row in req.observations
                if row.get("source") == "brain-force-sandbox-memory"
            )
            self.assertEqual(
                [row["lastReason"] for row in force_observation["value"]],
                ["sandbox-6", "sandbox-5", "sandbox-4", "sandbox-3", "sandbox-2", "sandbox-1"],
            )
            self.assertEqual(
                force_observation["value"][0]["mutationFingerprint"],
                f"{6:064x}",
            )

if __name__ == "__main__":
    unittest.main()
