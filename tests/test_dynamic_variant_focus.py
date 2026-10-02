import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import _force_structural_focus_keywords, _force_source_windows


class DynamicVariantFocusTests(unittest.TestCase):
    def test_dynamic_multi_player_gap_focuses_force_on_enumeration(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="variant_coverage_gap",
            status="FULL OK",
            observations=[{
                "source": "census-sharded-current",
                "value": {
                    "fanout": {
                        "movie": {
                            "announcedVariantCandidates": 19,
                            "streamsReturned": 8,
                            "state": "returned-subset",
                            "announcedQualityHeights": [480, 720, 1080, 2160],
                        }
                    }
                },
            }],
            provider_context={},
        )
        focus = _force_structural_focus_keywords(request)
        for token in ("out.length", "player", "server", "mirror", "source", "quality", "2160"):
            self.assertIn(token, focus)

        source = (
            "x" * 1200
            + "async function resolve(players){var out=[];"
            + "for(var i=0;i<players.length&&out.length<8;i++){"
            + "var rows=await source(players[i]);"
            + "for(var j=0;j<rows.length&&out.length<8;j++)out.push(rows[j]);"
            + "}return out;}"
            + "y" * 3200
        )
        windows = _force_source_windows(
            source,
            request.failure_class,
            focus_keywords=focus,
            max_chars=1200,
            max_windows=3,
        )
        self.assertTrue(windows)
        joined = "\n".join(str(row.get("source") or "") for row in windows)
        self.assertIn("out.length<8", joined)


if __name__ == "__main__":
    unittest.main()
