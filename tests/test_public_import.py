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

if __name__ == "__main__":
    unittest.main()
