import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.niakvio_adapter import classify_census_failure, request_from_checkout

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

    def test_client_transport_gap_is_not_provider_failure(self):
        row = {
            "status": "CLIENT TRANSPORT GAP",
            "dominantIssue": "provider_network_exception",
        }
        self.assertEqual(classify_census_failure(row), "transport_environment_gap")

    def test_current_targeted_and_refined_evidence_reaches_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "run-1",
                    "providers": [{
                        "provider": "demo",
                        "status": "ROUTE PROVEN",
                        "dominantIssue": "provider_network_exception",
                        "declaredLanes": ["anime"],
                        "routeProof": ["1 live route"],
                    }],
                }),
                encoding="utf-8",
            )
            (root / "automation" / "brain-repair-experience.json").write_text("{}", encoding="utf-8")
            (root / "automation" / "brain-repair-memory.json").write_text("{}", encoding="utf-8")
            (root / "automation" / "provider-targeted-regression-recovery-latest.json").write_text(
                json.dumps({
                    "providers": {
                        "demo": {
                            "debugStages": {"anime": "provider_network_exception"},
                            "statuses": {"anime": "no_streams"},
                            "verifiedLanes": [],
                            "playableLanes": [],
                            "contradictions": 0,
                            "sampleTitles": {"anime": ["Example"]},
                            "network": {
                                "anime": [{
                                    "method": "GET",
                                    "host": "example.test",
                                    "path": "/search/123",
                                    "status": 403,
                                    "headers": {"Authorization": "must-not-leak"},
                                }],
                            },
                        }
                    }
                }),
                encoding="utf-8",
            )
            (root / "automation" / "provider-repair-batch-refined-latest.json").write_text(
                json.dumps({
                    "sourceRunId": "run-1",
                    "groups": [{
                        "groupId": "route-to-terminal|mixed#r1",
                        "parentGroupId": "route-to-terminal|mixed",
                        "repairScope": "route-to-terminal",
                        "capabilityStrategy": "mixed_embed_resolver",
                        "providers": ["demo"],
                        "dominantIssues": ["network_exception"],
                        "debugStages": ["provider_network_exception"],
                        "networkShape": ["anime:GET:example.test:403:/search/{id}"],
                        "splitReason": "observed-signature-divergence",
                    }],
                }),
                encoding="utf-8",
            )

            request = request_from_checkout(root, "demo")
            by_source = {row["source"]: row["value"] for row in request.observations}
            current = by_source["targeted-regression-current"]
            self.assertEqual(current["debugStages"]["anime"], "provider_network_exception")
            self.assertEqual(current["network"]["anime"][0]["host"], "example.test")
            self.assertNotIn("headers", current["network"]["anime"][0])
            refined = by_source["refined-repair-batch-current"][0]
            self.assertEqual(refined["splitReason"], "observed-signature-divergence")
            self.assertEqual(refined["networkShape"], ["anime:GET:example.test:403:/search/{id}"])

    def test_stale_refined_evidence_is_not_injected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({"runId": "new", "providers": [{"provider": "demo", "status": "NO PROOF"}]}),
                encoding="utf-8",
            )
            for name in ("brain-repair-experience.json", "brain-repair-memory.json", "provider-targeted-regression-recovery-latest.json"):
                (root / "automation" / name).write_text("{}", encoding="utf-8")
            (root / "automation" / "provider-repair-batch-refined-latest.json").write_text(
                json.dumps({"sourceRunId": "old", "groups": [{"providers": ["demo"], "networkShape": ["stale"]}]}),
                encoding="utf-8",
            )
            request = request_from_checkout(root, "demo")
            self.assertNotIn(
                "refined-repair-batch-current",
                {row["source"] for row in request.observations},
            )

    def test_candidate_proof_uses_replay_gap(self):
        row = {
            "status": "CANDIDATE OK",
            "candidateProof": ["known candidate"],
            "dominantIssue": "provider_network_zero_result",
        }
        self.assertEqual(classify_census_failure(row), "candidate_replay_gap")

if __name__ == "__main__":
    unittest.main()
