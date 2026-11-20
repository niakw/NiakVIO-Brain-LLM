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
        records = [
            json.loads(line)
            for line in (root / "data/experience.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        record = next(
            row for row in records
            if row.get("experience_id") == "official-tv-purstream-core-v20-ts-aac-partial-20261120"
        )
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

    def test_hls_track_topology_collapse_remains_core_negative_prior(self):
        root = Path(__file__).resolve().parents[1]
        records = [
            json.loads(line)
            for line in (root / "data/experience.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        record = next(
            row for row in records
            if row.get("experience_id") == "official-tv-purstream-core-v20-track-topology-collapse-20261120"
        )
        schema = json.loads((root / "schemas/experience.schema.json").read_text(encoding="utf-8"))
        self.assertTrue(set(schema["required"]).issubset(record))
        self.assertEqual(record["result"], "inconclusive")
        self.assertEqual(record["target_layer"], "core_client_boundary")
        self.assertFalse(record["proof_authority"])
        self.assertFalse(record["publication_authority"])
        self.assertFalse(record["experiment"]["candidateGeneratedByBrain"])
        self.assertTrue(record["experiment"]["decodedVideoVerified"])
        self.assertFalse(record["experiment"]["decodedMediaVerified"])
        self.assertEqual(record["experiment"]["transportAudioTrackCount"], 2)
        self.assertEqual(record["experiment"]["playerAudioTrackCount"], 0)
        self.assertEqual(record["experiment"]["transportSubtitleTrackCount"], 1)
        policy = classify_learning_record(record)
        self.assertEqual(policy["rag_bucket"], "transient")
        self.assertFalse(policy["sft_candidate"])
        self.assertEqual(
            record["superseded_by"],
            "official-tv-purstream-v35-compose-track-observer-gap-20261120",
        )
        store = ExperienceStore.from_jsonl(root / "data/experience.jsonl")
        self.assertNotIn(record["experience_id"], {
            row.get("experience_id") for row in store.rows
        })
        retrieval = store.search({
            "provider_id": "purstream",
            "failure_class": "media_validation_gap",
            "signals": ["player_audio_tracks_0_observer_ambiguous"],
        }, limit=1)
        self.assertEqual(
            retrieval[0]["experience_id"],
            "official-tv-purstream-v35-compose-track-observer-gap-20261120",
        )
        self.assertEqual(retrieval[0]["target_layer"], "harness_observation")
        self.assertFalse(retrieval[0]["proof_authority"])
        encoded = json.dumps(record)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

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
