import unittest
import json
from pathlib import Path

from niakvio_brain_llm.contracts import RepairProposal, RepairRequest
from niakvio_brain_llm.learning import sanitized_experience
from niakvio_brain_llm.session import VerificationOutcome
from niakvio_brain_llm.learning_policy import classify_learning_record
from niakvio_brain_llm.retrieval import ExperienceStore

class LearningTests(unittest.TestCase):
    def test_hls_partial_native_experience_remains_retrievable_not_accepted(self):
        root = Path(__file__).resolve().parents[1]
        record = json.loads((root / "data/experience.jsonl").read_text(encoding="utf-8").strip())
        schema = json.loads((root / "schemas/experience.schema.json").read_text(encoding="utf-8"))
        self.assertTrue(set(schema["required"]).issubset(record))
        self.assertIn(record["result"], schema["properties"]["result"]["enum"])
        self.assertEqual(record["result"], "inconclusive")
        self.assertFalse(record["proof_authority"])
        self.assertFalse(record["publication_authority"])
        self.assertEqual(record["verified_lanes"], [])
        self.assertEqual(record["mutation_scopes"], [])
        self.assertFalse(record["experiment"]["candidateGeneratedByBrain"])
        self.assertFalse(record["experiment"]["decodedMediaVerified"])
        self.assertEqual(record["experiment"]["candidateReturnedStreams"], 1)
        self.assertEqual(record["experiment"]["baselineReturnedStreams"], 0)
        policy = classify_learning_record(record)
        self.assertEqual(policy["rag_bucket"], "transient")
        self.assertFalse(policy["sft_candidate"])
        retrieval = ExperienceStore.from_jsonl(root / "data/experience.jsonl").search({
            "provider_id": "purstream",
            "failure_class": "media_validation_gap",
            "signals": ["aac_advertised_mpegts_observed"],
        }, limit=1)
        self.assertEqual(retrieval[0]["experience_id"], record["experience_id"])
        self.assertNotIn("http://", json.dumps(record))
        self.assertNotIn("https://", json.dumps(record))

    def test_learning_record_omits_raw_context_and_marks_verifier(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="terminal_extractor",
            provider_context={"raw_secret": "must-not-persist"},
        )
        proposal = RepairProposal(
            provider_id="demo",
            diagnosis="extractor changed",
            strategy="repair_terminal",
            confidence=0.8,
            target_layer="provider",
            mutations=[{"scope": "provider_js", "code": "raw patch omitted"}],
        )
        row = sanitized_experience(
            request,
            proposal,
            VerificationOutcome(result="validated", verified_lanes=["movie"]),
        )
        encoded = str(row)
        self.assertNotIn("must-not-persist", encoded)
        self.assertNotIn("raw patch omitted", encoded)
        self.assertEqual(row["result"], "validated")
        self.assertEqual(row["verification_authority"], "niakvio")

if __name__ == "__main__":
    unittest.main()
