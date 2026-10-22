import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.niakvio_adapter import _provider_force_negative_memory
from niakvio_brain_llm.prompting import build_force_prompt_payload


class ForceExecutionFeedbackTests(unittest.TestCase):
    def test_failed_execution_keeps_measured_progress_for_the_next_model_call(self):
        coverage = {
            "streamsReturned": 0, "streamsPlayable": 0,
            "announcedPlayerCandidates": 47, "announcedVariantCandidates": 141,
            "exploredPlayerRequests": 8, "rawHeader": "must-not-retain",
        }
        rows = _provider_force_negative_memory({"entries": [{
            "providerId": "demo", "mutationFingerprint": "a" * 64,
            "mutationContextFingerprint": "b" * 64,
            "consecutiveFailures": 1, "lastOutcome": "rejected",
            "lastReason": "required_category_playable_proof:anime",
            "lastBaselineCoverage": coverage, "lastCandidateCoverage": coverage,
            "lastCoverageDelta": {"streamsPlayable": 0, "exploredPlayerRequests": 0},
        }]}, "demo")
        request = RepairRequest(
            provider_id="demo", failure_class="chain_terminal_gap",
            provider_context={"advisor_experiment_history": rows},
        )
        failure = build_force_prompt_payload(request)["prior_force_sandbox_failures"][0]
        self.assertEqual(failure["lastBaselineCoverage"]["announcedVariantCandidates"], 141)
        self.assertEqual(failure["lastCandidateCoverage"]["streamsPlayable"], 0)
        self.assertEqual(failure["lastCoverageDelta"]["exploredPlayerRequests"], 0)
        self.assertNotIn("must-not-retain", str(rows))

    def test_terminal_template_exposes_the_extractor_and_its_request_callees(self):
        source = (
            'function s(v){return String(v||"");}'
            'function decodeSource(row){return s(row.sourceUrl);}'
            'async function clockLinks(path){return fetch(path).then(r=>r.json());}'
            'function isDirect(url){return /m3u8/.test(url);}'
            'async function directPlayable(url){return fetch(url).then(r=>r.url);}'
            'async function resolveRows(rows){var out=[];for(var row of rows){'
            'var url=decodeSource(row);var links=await clockLinks(url);'
            'if(isDirect(links[0]))out.push(await directPlayable(links[0]));}return out;}'
        )
        request = RepairRequest(
            provider_id="demo", failure_class="chain_terminal_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "preferredRuntimeMutationSource": source,
                "runtime_template_prior": {"reuseBeforeNovelBloc": True},
            },
        )
        units = build_force_prompt_payload(request)["new_bloc_target"]["editable_units"]
        joined = "\n".join(row["source"] for row in units)
        for name in ("resolveRows", "clockLinks", "directPlayable"):
            self.assertIn("function " + name + "(", joined)
        self.assertNotIn('function s(', joined)
        self.assertLessEqual(len(units), 4)


if __name__ == "__main__":
    unittest.main()
