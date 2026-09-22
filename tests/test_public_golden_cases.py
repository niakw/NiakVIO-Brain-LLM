import json
import tempfile
import unittest
from pathlib import Path

from benchmark.build_public_golden_cases import build_case, load_cases

class PublicGoldenCaseTests(unittest.TestCase):
    def test_known_route_gap_becomes_provider_case(self):
        case = build_case({
            "id": "route",
            "providers": ["demo"],
            "failureClass": "route_proven_gap",
            "solutionClass": "search_detail_player_terminal_traversal",
            "transferableSignals": ["route responds"],
        })
        self.assertIsNotNone(case)
        self.assertEqual(case["expected_target_layer"], "provider")
        self.assertEqual(case["request"]["status"], "ROUTE PROVEN")

    def test_ambiguous_failure_is_excluded(self):
        self.assertIsNone(build_case({
            "id": "ambiguous",
            "providers": ["global"],
            "failureClass": "unknown_case",
            "solutionClass": "something",
        }))

if __name__ == "__main__":
    unittest.main()
