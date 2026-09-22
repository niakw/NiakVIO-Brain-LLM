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
                "providers": [{
                    "provider": "demo",
                    "status": "CHAIN REACHED",
                    "dominantIssue": "terminal_extractor",
                    "declaredLanes": ["movie"],
                    "repairEligible": True,
                    "brainCheckRequired": True,
                    "evidenceDepth": ["movie=chain_reached"],
                }]
            }
            (root / "automation" / "provider-census-status.json").write_text(json.dumps(census))
            (root / "automation" / "brain-repair-experience.json").write_text("{}")
            (root / "automation" / "brain-repair-memory.json").write_text("{}")
            req = request_from_checkout(root, "demo")
            self.assertEqual(req.failure_class, "chain_terminal_gap")
            self.assertEqual(req.supported_types, ["movie"])
            self.assertTrue(req.provider_context["read_only"])
            self.assertTrue(req.census_prior["brainCheckRequired"])

if __name__ == "__main__":
    unittest.main()
