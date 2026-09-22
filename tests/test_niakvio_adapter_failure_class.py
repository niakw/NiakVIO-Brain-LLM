import unittest

from niakvio_brain_llm.niakvio_adapter import classify_census_failure

class AdapterFailureClassTests(unittest.TestCase):
    def test_chain_reached_beats_generic_zero_issue(self):
        row = {
            "status": "CHAIN REACHED",
            "dominantIssue": "provider_network_zero_result",
            "evidenceDepth": ["anime=chain_reached"],
        }
        self.assertEqual(classify_census_failure(row), "chain_terminal_gap")

    def test_route_proven_beats_generic_zero_issue(self):
        row = {
            "status": "ROUTE PROVEN",
            "dominantIssue": "provider_network_zero_result",
            "routeProof": ["1 live route"],
        }
        self.assertEqual(classify_census_failure(row), "route_proven_gap")

    def test_harness_status_is_not_provider_failure(self):
        row = {
            "status": "HARNESS MISMATCH",
            "dominantIssue": "provider_network_exception",
        }
        self.assertEqual(classify_census_failure(row), "transport_environment_gap")

    def test_candidate_proof_uses_replay_gap(self):
        row = {
            "status": "CANDIDATE OK",
            "candidateProof": ["known candidate"],
            "dominantIssue": "provider_network_zero_result",
        }
        self.assertEqual(classify_census_failure(row), "candidate_replay_gap")

if __name__ == "__main__":
    unittest.main()
