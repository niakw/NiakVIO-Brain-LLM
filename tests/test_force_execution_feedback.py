import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.niakvio_adapter import _provider_force_negative_memory
from niakvio_brain_llm.live_evidence import non_improving_functions, verification_feedback
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
            "executionObserved": True, "materializedMutationObserved": True,
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


    def test_decoded_repair_failure_rotates_only_without_real_fanout_progress(self):
        source = 'function classBlocks(html,cls){return String(html||"").slice(0,1);}'
        metric = {
            "streamsReturned": 0, "streamsPlayable": 0,
            "identityContradictions": 0, "fixtureCoverage": [],
            "variantCoverage": {
                "announcedPlayerCandidates": 16, "announcedVariantCandidates": 16,
                "exploredPlayerRequests": 1, "maxPlayableHeight": 0,
            },
        }
        previous = {
            "reason": "decoded_repair_no_new_fixture_control",
            "executionObserved": True, "materializedMutationObserved": True,
            "baseline": metric, "candidate": metric,
        }
        context = {
            "previous_verification": previous,
            "previous_executed_edits": [{"find": source}],
        }
        self.assertEqual(non_improving_functions(source, context), ["classBlocks"])
        feedback = verification_feedback(previous)
        self.assertEqual(feedback["baseline"]["variantCoverage"]["exploredPlayerRequests"], 1)
        self.assertEqual(feedback["candidate"]["variantCoverage"]["announcedPlayerCandidates"], 16)

        # A deeper crawl is evidence of progress, even if decoder proof remains zero.
        changed = {**metric, "variantCoverage": {**metric["variantCoverage"], "exploredPlayerRequests": 3}}
        progressed = {**context, "previous_verification": {**previous, "candidate": changed}}
        self.assertEqual(non_improving_functions(source, progressed), [])
        # Missing executable/materialized bytes must never blacklist a source.
        unexecuted = {**context, "previous_verification": {**previous, "executionObserved": False}}
        self.assertEqual(non_improving_functions(source, unexecuted), [])
        self.assertEqual(non_improving_functions(source, {
            **context, "previous_verification": {**previous, "reason": "decoded_repair_fixture_contract"},
        }), [])


if __name__ == "__main__":
    unittest.main()
