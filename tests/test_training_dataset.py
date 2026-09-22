import unittest

from training.build_sft_dataset import build_example

class TrainingDatasetTests(unittest.TestCase):
    def test_unpromoted_validated_memory_is_not_sft_truth(self):
        self.assertIsNone(build_example({
            "provider_id": "demo",
            "failure_class": "api_discovery_gap",
            "strategy": "discover_api",
            "target_layer": "provider",
            "result": "validated",
        }))

    def test_abstention_never_becomes_sft_truth(self):
        self.assertIsNone(build_example({
            "provider_id": "demo",
            "failure_class": "api_discovery_gap",
            "strategy": "discover_api",
            "target_layer": "provider",
            "result": "abstained",
            "_learning": {"sft_candidate": True, "weight": 1.0},
        }))

    def test_promoted_validated_layer_becomes_sft_example(self):
        example = build_example({
            "provider_id": "demo",
            "failure_class": "api_discovery_gap",
            "strategy": "discover_api",
            "diagnosis": "old API is stale",
            "target_layer": "provider",
            "result": "validated",
            "_learning": {"sft_candidate": True, "weight": 1.2},
        })
        self.assertIsNotNone(example)
        self.assertIn('"target_layer": "provider"', example["messages"][2]["content"])
        self.assertEqual(example["metadata"]["weight"], 1.2)

if __name__ == "__main__":
    unittest.main()
