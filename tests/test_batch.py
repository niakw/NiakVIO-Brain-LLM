import unittest

from niakvio_brain_llm.batch import batch_summary, select_batch_targets

ROWS = [
    {
        "provider": "repairable",
        "status": "CHAIN REACHED",
        "brainCheckRequired": True,
        "repairEligible": True,
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
    def test_repair_queue_only_contains_mutation_eligible(self):
        rows = select_batch_targets(ROWS, mode="repair")
        self.assertEqual([row["provider"] for row in rows], ["repairable"])

    def test_diagnostic_queue_is_non_repair_brain_work(self):
        rows = select_batch_targets(ROWS, mode="diagnostic")
        self.assertEqual([row["provider"] for row in rows], ["harness"])

    def test_brain_queue_contains_both(self):
        rows = select_batch_targets(ROWS, mode="brain")
        self.assertEqual(
            [row["provider"] for row in rows],
            ["repairable", "harness"],
        )

    def test_summary_counts_statuses(self):
        summary = batch_summary(ROWS[:2])
        self.assertEqual(summary["targets"], 2)
        self.assertEqual(summary["statuses"]["CHAIN REACHED"], 1)

if __name__ == "__main__":
    unittest.main()
