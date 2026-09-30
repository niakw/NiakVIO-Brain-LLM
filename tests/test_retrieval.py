import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.repair_family import repair_family_descriptor
from niakvio_brain_llm.retrieval import ExperienceStore

class RetrievalTests(unittest.TestCase):
    def test_similar_failure_ranks_first(self):
        store = ExperienceStore([
            {"provider_id": "a", "failure_class": "terminal_extractor", "strategy": "repair_terminal_extractor"},
            {"provider_id": "b", "failure_class": "waf_challenge", "strategy": "abstain"},
        ])
        rows = store.search({"failure_class": "terminal_extractor"}, limit=1)
        self.assertEqual(rows[0]["provider_id"], "a")

    def test_validated_same_repair_family_outranks_generic_same_failure(self):
        query = {
            "provider_id": "new-provider",
            "failure_class": "route_proven_gap",
            "status": "ROUTE PROVEN",
            "supported_types": ["movie", "tv"],
            "allowed_mutations": ["provider_patch", "provider_bloc"],
            "observations": [{
                "source": "census-sharded-current",
                "value": {
                    "structureHints": [
                        "movie:classes=movie-card,movie-card-format;"
                        "classFacts=[movie-card;count=12;selfHref=1;nestedAnchors=24;"
                        "tags=a,div,span;signals=movie,series,year]"
                    ]
                },
            }],
        }
        family = repair_family_descriptor(query)
        store = ExperienceStore([
            {
                "provider_id": "generic",
                "failure_class": "route_proven_gap",
                "strategy": "generic-route-repair",
                "result": "failed",
            },
            {
                "provider_id": "peer",
                "failure_class": "route_proven_gap",
                "strategy": "validated-family-mechanism",
                "result": "validated",
                "repair_family": family,
            },
        ])
        rows = store.search(query, limit=2)
        self.assertEqual(rows[0]["provider_id"], "peer")
        self.assertGreater(rows[0]["_structural_score"], rows[1]["_structural_score"])

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
