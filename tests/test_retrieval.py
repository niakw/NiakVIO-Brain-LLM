import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.retrieval import ExperienceStore

class RetrievalTests(unittest.TestCase):
    def test_similar_failure_ranks_first(self):
        store = ExperienceStore([
            {"provider_id": "a", "failure_class": "terminal_extractor", "strategy": "repair_terminal_extractor"},
            {"provider_id": "b", "failure_class": "waf_challenge", "strategy": "abstain"},
        ])
        rows = store.search({"failure_class": "terminal_extractor"}, limit=1)
        self.assertEqual(rows[0]["provider_id"], "a")

    def test_public_and_private_jsonl_merge_deduplicates_experience_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "public.jsonl"
            private = root / "private.jsonl"
            public.write_text(
                json.dumps({
                    "experience_id": "same",
                    "failure_class": "api_discovery_gap",
                    "strategy": "public",
                }) + "\n",
                encoding="utf-8",
            )
            private.write_text(
                "\n".join([
                    json.dumps({
                        "experience_id": "same",
                        "failure_class": "api_discovery_gap",
                        "strategy": "duplicate",
                    }),
                    json.dumps({
                        "experience_id": "private-2",
                        "failure_class": "chain_terminal_gap",
                        "strategy": "terminal",
                    }),
                ]) + "\n",
                encoding="utf-8",
            )
            store = ExperienceStore.from_jsonl_many([public, private])
            self.assertEqual(len(store.rows), 2)
            self.assertEqual(store.rows[0]["strategy"], "public")

if __name__ == "__main__":
    unittest.main()
