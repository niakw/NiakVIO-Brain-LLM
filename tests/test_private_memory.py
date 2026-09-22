import unittest

from niakvio_brain_llm.private_memory import sanitize_private_record

class PrivateMemoryTests(unittest.TestCase):
    def test_accepts_structured_niakvio_experience(self):
        row = sanitize_private_record({
            "project": "NiakVIO",
            "experience_id": "chat-case-1",
            "failure_class": "api_discovery_gap",
            "strategy": "discover_api_from_current_page_and_bundles",
            "providers": ["movix"],
            "lesson": "discover current provider-owned API",
        })
        self.assertEqual(row["project"], "NiakVIO")
        self.assertFalse(row["proof_authority"])

    def test_rejects_other_project(self):
        with self.assertRaises(ValueError):
            sanitize_private_record({
                "project": "OtherProject",
                "failure_class": "x",
                "strategy": "y",
            })

    def test_rejects_raw_conversation(self):
        with self.assertRaises(ValueError):
            sanitize_private_record({
                "project": "NiakVIO",
                "failure_class": "x",
                "strategy": "y",
                "messages": [{"role": "user", "content": "raw"}],
            })

if __name__ == "__main__":
    unittest.main()
