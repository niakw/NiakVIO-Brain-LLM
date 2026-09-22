import unittest

from training.build_sft_dataset import build_example

class TrainingDatasetTests(unittest.TestCase):
    def test_unlabelled_historical_memory_is_not_sft_truth(self):
        self.assertIsNone(build_example({
            "provider_id": "demo",
            "failure_class": "api_discovery_gap",
            "strategy": "discover_api",
            "result": "validated",
        }))

    def test_validated_layer_becomes_sft_example(self):
        example = build_example({
            "provider_id": "demo",
            "failure_class": "api_discovery_gap",
            "strategy": "discover_api",
            "diagnosis": "old API is stale",
            "target_layer": "provider",
            "result": "validated",
        })
        self.assertIsNotNone(example)
        self.assertIn('"target_layer": "provider"', example["messages"][2]["content"])

if __name__ == "__main__":
    unittest.main()
