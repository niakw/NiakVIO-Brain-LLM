import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.provider_context import (
    FAMILY_REFERENCE_TOKENS,
    _technical_features,
    audit_current_dynamic_variant_coverage,
)


class DynamicVariantSelectionTests(unittest.TestCase):
    def test_variant_family_peer_vocabulary_covers_player_server_quality(self):
        features = _technical_features(
            "player server mirror source variant quality resolution language audio stream"
        )
        expected = {
            "player", "server", "mirror", "source", "variant",
            "quality", "resolution", "language", "audio", "stream",
        }
        self.assertTrue(expected <= features)
        self.assertTrue(expected <= FAMILY_REFERENCE_TOKENS["variant_coverage_gap"])

    def test_current_sharded_fanout_debt_becomes_repair_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-sharded-latest.json").write_text(
                json.dumps({
                    "schema_version": 6,
                    "rows": [
                        {
                            "provider_id": "coflix",
                            "semantic_type": "movie",
                            "raw": 8,
                            "streams_returned": 8,
                            "announced_player_candidates": 2,
                            "announced_variant_candidates": 19,
                            "announced_player_hosts": ["one.test", "two.test"],
                            "announced_quality_heights": [480, 720, 1080],
                            "explored_player_requests": 2,
                            "explored_player_hosts": ["one.test", "two.test"],
                            "variant_fanout_state": "returned-subset",
                        },
                        {
                            "provider_id": "complete",
                            "semantic_type": "movie",
                            "raw": 19,
                            "streams_returned": 19,
                            "announced_player_candidates": 2,
                            "announced_variant_candidates": 19,
                            "announced_player_hosts": ["a.test", "b.test"],
                            "explored_player_requests": 2,
                            "variant_fanout_state": "fanout-observed",
                        },
                        {
                            "provider_id": "single",
                            "semantic_type": "movie",
                            "raw": 1,
                            "streams_returned": 1,
                            "announced_player_candidates": 1,
                            "announced_variant_candidates": 1,
                            "variant_fanout_state": "not-observed",
                        },
                    ],
                }),
                encoding="utf-8",
            )

            audit = audit_current_dynamic_variant_coverage(root)
            self.assertEqual(audit["highRiskProviders"], ["coflix"])
            self.assertEqual(audit["providerCount"], 1)
            self.assertFalse(audit["proofAuthority"])
            self.assertTrue(audit["repairTargetAuthority"])
            row = audit["providers"][0]
            self.assertEqual(row["provider"], "coflix")
            self.assertEqual(row["maxAnnouncedVariantCandidates"], 19)
            self.assertEqual(row["maxReturnedStreams"], 8)
            lane = row["lanes"][0]
            self.assertEqual(lane["announcedPlayerCandidates"], 2)
            self.assertEqual(lane["announcedVariantCandidates"], 19)
            self.assertEqual(lane["announcedPlayerHosts"], ["one.test", "two.test"])
            self.assertEqual(lane["exploredPlayerRequests"], 2)
            self.assertEqual(lane["state"], "returned-subset")


if __name__ == "__main__":
    unittest.main()
