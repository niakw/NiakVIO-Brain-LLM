import unittest

from niakvio_brain_llm.retrieval import ExperienceStore

class RetrievalTests(unittest.TestCase):
    def test_similar_failure_ranks_first(self):
        store = ExperienceStore([
            {"provider_id": "a", "failure_class": "terminal_extractor", "strategy": "repair_terminal_extractor"},
            {"provider_id": "b", "failure_class": "waf_challenge", "strategy": "abstain"},
        ])
        rows = store.search({"failure_class": "terminal_extractor"}, limit=1)
        self.assertEqual(rows[0]["provider_id"], "a")

if __name__ == "__main__":
    unittest.main()
