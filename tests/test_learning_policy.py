import unittest

from niakvio_brain_llm.learning_policy import classify_learning_record

class LearningPolicyTests(unittest.TestCase):
    def test_validated_provider_result_can_become_sft_candidate(self):
        policy = classify_learning_record({
            "result": "validated",
            "target_layer": "provider",
            "verified_lanes": ["movie"],
        })
        self.assertEqual(policy["rag_bucket"], "positive")
        self.assertTrue(policy["sft_candidate"])

    def test_failed_result_is_negative_memory_only(self):
        policy = classify_learning_record({
            "result": "failed",
            "target_layer": "provider",
        })
        self.assertEqual(policy["rag_bucket"], "negative")
        self.assertFalse(policy["sft_candidate"])

    def test_inconclusive_result_is_not_training_truth(self):
        policy = classify_learning_record({
            "result": "inconclusive",
            "target_layer": "provider",
        })
        self.assertEqual(policy["rag_bucket"], "transient")
        self.assertFalse(policy["sft_candidate"])

if __name__ == "__main__":
    unittest.main()
