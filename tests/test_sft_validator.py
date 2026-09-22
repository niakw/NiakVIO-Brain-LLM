import json
import unittest

from training.validate_sft_dataset import validate_row

class SftValidatorTests(unittest.TestCase):
    def test_accepts_verified_training_row(self):
        row = {
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "{}"},
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "provider_id": "demo",
                        "strategy": "repair",
                        "target_layer": "provider",
                        "abstain": False,
                    }),
                },
            ],
            "metadata": {
                "source": "niakvio-verified-learning",
                "weight": 1.0,
            },
        }
        validate_row(row)

    def test_rejects_abstention_as_positive_training_truth(self):
        row = {
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "{}"},
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "provider_id": "demo",
                        "strategy": "probe",
                        "target_layer": "provider",
                        "abstain": True,
                    }),
                },
            ],
            "metadata": {
                "source": "niakvio-verified-learning",
            },
        }
        with self.assertRaises(ValueError):
            validate_row(row)

    def test_rejects_unverified_source(self):
        row = {
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "{}"},
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "provider_id": "demo",
                        "strategy": "repair",
                        "target_layer": "provider",
                        "abstain": False,
                    }),
                },
            ],
            "metadata": {"source": "historical-chat"},
        }
        with self.assertRaises(ValueError):
            validate_row(row)

if __name__ == "__main__":
    unittest.main()
