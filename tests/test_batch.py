import unittest

from niakvio_brain_llm.batch import batch_summary, select_batch_targets

ROWS = [
    {
        "provider": "route",
        "status": "ROUTE PROVEN",
        "brainCheckRequired": True,
        "repairEligible": True,
        "routeProof": ["route"],
    },
    {
        "provider": "chain",
        "status": "CHAIN REACHED",
        "brainCheckRequired": True,
        "repairEligible": True,
        "evidenceDepth": ["movie=chain_reached"],
    },
    {
        "provider": "candidate",
        "status": "CANDIDATE OK",
        "brainCheckRequired": True,
        "repairEligible": True,
        "candidateProof": ["candidate"],
    },
    {
        "provider": "harness",
        "status": "HARNESS MISMATCH",
        "brainCheckRequired": True,
        "repairEligible": False,
    },
    {
        "provider": "healthy",
        "status": "FULL OK",
        "brainCheckRequired": False,
        "repairEligible": False,
    },
]

class BatchTests(unittest.TestCase):
    def test_repair_queue_prioritizes_evidence_depth(self):
        rows = select_batch_targets(ROWS, mode="repair")
        self.assertEqual(
            [row["provider"] for row in rows],
            ["candidate", "chain", "route"],
        )

    def test_diagnostic_queue_is_non_repair_brain_work(self):
        rows = select_batch_targets(ROWS, mode="diagnostic")
        self.assertEqual([row["provider"] for row in rows], ["harness"])

    def test_brain_queue_contains_repair_and_diagnostic(self):
        rows = select_batch_targets(ROWS, mode="brain")
        self.assertEqual(
            {row["provider"] for row in rows},
            {"candidate", "chain", "route", "harness"},
        )

    def test_summary_counts_statuses(self):
        summary = batch_summary(ROWS[:2])
        self.assertEqual(summary["targets"], 2)
        self.assertEqual(summary["statuses"]["CHAIN REACHED"], 1)

if __name__ == "__main__":
    unittest.main()
