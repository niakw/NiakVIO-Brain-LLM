import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import (
    _force_structural_focus_keywords,
    build_force_prompt_payload,
)


class TerminalFocusPrecedenceTests(unittest.TestCase):
    def request(self, failure="chain_terminal_gap"):
        source = (
            'function s(v){return String(v==null?"":v).trim();}\n'
            + '/*' + 'padding ' * 160 + '*/\n'
            + 'function hexBytes(v){var out=new Uint8Array(v.length/2);'
            'for(var i=0;i<out.length;i++)out[i]=parseInt(v.slice(i*2,i*2+2),16);return out;}\n'
            + '/*' + 'padding ' * 160 + '*/\n'
            + 'function decodeSource(row){return row.sourceUrl||row.url;}\n'
            + 'async function resolveRows(rows){var out=[];for(var row of rows){'
            'var url=decodeSource(row);var media=await fetch(url);out.push(media);}return out;}\n'
        )
        return RepairRequest(
            provider_id="demo", failure_class=failure,
            allowed_mutations=["provider_bloc"],
            provider_context={
                "preferredRuntimeMutationSource": source,
                "runtime_template_prior": {"reuseBeforeNovelBloc": True},
                "runtime_variant_coverage": {
                    "riskKind": "variant-coverage-truncation",
                    "dimensions": ["quality"],
                },
            },
        )

    def test_heuristic_variant_risk_cannot_hide_terminal_extractor(self):
        request = self.request()
        units = build_force_prompt_payload(request)["new_bloc_target"]["editable_units"]
        joined = "\n".join(row["source"] for row in units)
        self.assertIn("function resolveRows(", joined)
        self.assertNotIn("function hexBytes(", joined)
        self.assertNotIn("out.length", _force_structural_focus_keywords(request))
        self.assertLessEqual(len(units), 2)

    def test_zero_stream_fanout_keeps_terminal_failure_causality(self):
        request = self.request()
        request.observations = [{
            "source": "census-sharded-current",
            "value": {"fanout": {"anime": {
                "announcedVariantCandidates": 4,
                "streamsReturned": 0,
                "state": "explored-not-resolved",
            }}},
        }]
        self.assertNotIn("out.length", _force_structural_focus_keywords(request))

    def test_verified_variant_gap_retains_enumeration_focus(self):
        self.assertIn("out.length", _force_structural_focus_keywords(self.request("variant_coverage_gap")))


if __name__ == "__main__":
    unittest.main()
