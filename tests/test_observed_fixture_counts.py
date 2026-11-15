"""Network-free regression coverage for absent versus observed counters."""
import unittest

from niakvio_brain_llm.live_evidence import (
    _observed_empty_fixtures, fixture_evidence, observed_failure_class,
)


def receipt(label="Demo", returned=0, playable=0):
    return {"fixture": label, "streamsReturned": returned, "streamsPlayable": playable}


class ObservedFixtureCountsTests(unittest.TestCase):
    def test_batch_keeps_only_explicit_empty_receipt(self):
        rows = [receipt("Film"), receipt("Episode", 2, 1), receipt("Animation", 1, 0)]
        self.assertEqual([row["fixture"] for row in _observed_empty_fixtures(rows)], ["Film"])

    def test_invalid_receipts_fail_closed(self):
        for raw in ({"fixture": "Demo"}, {"fixture": "Demo", "streamsReturned": 0},
                    receipt(returned="0"), receipt(returned=False), receipt(returned=-1),
                    receipt(returned=0, playable=1), receipt(returned=100001),
                    receipt(label=""), receipt(label="Demo\n"), None):
            with self.subTest(raw=raw):
                self.assertEqual(_observed_empty_fixtures([raw]), [])
                self.assertEqual(_observed_empty_fixtures([receipt("Other"), raw]), [])

    def test_duplicate_and_overlong_groups_are_ambiguous(self):
        self.assertEqual(_observed_empty_fixtures([receipt(), receipt()]), [])
        self.assertEqual(_observed_empty_fixtures([receipt(str(i)) for i in range(9)]), [])

    def test_display_projection_preserves_missingness(self):
        raw = {"fixture": "Demo", "category": ["malformed"]}
        clean = fixture_evidence([raw])
        self.assertEqual(clean[0]["streamsReturned"], 0)
        self.assertEqual(clean[0]["category"], "")
        self.assertIs(clean[0]["streamCountsObserved"], False)
        self.assertEqual(fixture_evidence(clean), clean)
        self.assertEqual(_observed_empty_fixtures(clean), [])

    def test_incomplete_evidence_cannot_refine_failure(self):
        for rows in ([{"fixture": "Demo"}], fixture_evidence([{"fixture": "Demo"}])):
            live = {"fixture_evidence": rows, "network_evidence": [
                {"fixture": "Demo", "stage": "content_lookup", "status": 200}]}
            self.assertEqual(observed_failure_class("variant_coverage_gap", live),
                             "variant_coverage_gap")


if __name__ == "__main__":
    unittest.main()
