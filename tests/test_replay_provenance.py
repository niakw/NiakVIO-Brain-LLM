from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from niakvio_brain_llm.replay_inventory import replay_inventory

OLD="a"*40
NOW="b"*40
ROWS=[
    {"provider": "animesama-co", "status": "CANDIDATE OK", "candidateProof": ["run 34309729426"]},
    {"provider": "animevostfr", "status": "CANDIDATE OK", "candidateProof": ["run 34309729426"]},
    {"provider": "coflix", "status": "FULL OK", "candidateProof": ["run 34309729426"]},
]
CENSUS={"providers":ROWS,"repairQueue":["animesama-co","animevostfr"]}

class ReplayProvenanceTests(unittest.TestCase):
    def test_historical_label_without_patch_is_not_a_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            result=replay_inventory(CENSUS,Path(folder),NOW)
        self.assertEqual(result["candidateReplayCount"],2)
        self.assertEqual(result["missingProgramCount"],2)
        self.assertEqual(result["currentProgramCount"],0)
        self.assertEqual({r["status"] for r in result["rows"]},{"missing_exact_replay_program"})
        self.assertFalse(result["publicationAuthority"])
        self.assertNotIn("coflix",str(result))

    def test_archived_mutation_requires_source_sha_and_real_owned_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            path=root/"automation/hosted-repair-evidence/34309729426-mutations.json"
            path.parent.mkdir(parents=True)
            doc={
                "publicationAuthority":False,
                "sandboxMutationAuthority":True,
                "providerMutationContentRetained":True,
                "sourceNiakvioSha":OLD,
                "rows":[{"providerId":"animesama-co","mutationFingerprint":"c"*64,
                         "mutations":[{"scope":"provider_bloc","operation":"upsert",
                                       "family":"catalogue_html","find":"old","replace":"new"}]}],
            }
            path.write_text(json.dumps(doc))
            result=replay_inventory(CENSUS,root,NOW)
            self.assertEqual(result["missingProgramCount"],1)
            self.assertEqual(result["currentProgramCount"],0)
            self.assertEqual(result["rows"][0]["status"],
                             "historical_program_needs_safe_rematerialization")
            doc["sourceNiakvioSha"]=NOW
            path.write_text(json.dumps(doc))
            result=replay_inventory(CENSUS,root,NOW)
            self.assertEqual(result["currentProgramCount"],1)
            self.assertEqual(result["rows"][0]["status"],
                             "source_matched_program_needs_live_replay")
            # A path with a run label but no real provider mutation is not a
            # candidate program and cannot produce a positive proof.
            doc["rows"][0]["mutations"]=[]
            path.write_text(json.dumps(doc))
            self.assertEqual(replay_inventory(CENSUS,root,NOW)["missingProgramCount"],2)

    def test_cannot_transform_candidate_label_into_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            invalid={"providers":ROWS,"repairQueue":"animesama-co"}
            with self.assertRaises(ValueError):
                replay_inventory(invalid,Path(folder),NOW)
            with self.assertRaises(ValueError):
                replay_inventory(CENSUS,Path(folder),"not-current-sha")

if __name__=="__main__":
    unittest.main()
