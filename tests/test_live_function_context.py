import unittest
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import build_force_prompt_payload
from niakvio_brain_llm.source_units import javascript_function_end
from niakvio_brain_llm.live_evidence import network_evidence, verification_feedback

class LiveFunctionContextTests(unittest.TestCase):
    def test_schema_evidence_has_no_response_values_or_credential_fields(self):
        rows = network_evidence([{'host': 'example.test', 'status': 200, 'stage': 'player',
            'response_body': 'PRIVATE', 'response_structure': {'kind': 'json', 'fields': [
                {'path': 'data.sources[].file', 'type': 'string', 'value': 'PRIVATE'},
                {'path': 'data.access_token', 'type': 'string'},
            ]}}])
        self.assertEqual(rows[0]['response_structure']['fields'], [{'path': 'data.sources[].file', 'type': 'string'}])
        self.assertNotIn('PRIVATE', str(rows))
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            allowed_mutations=['provider_bloc'], provider_context={'live_runtime_evidence': {
                'network_evidence': rows, 'previous_verification': verification_feedback({
                    'reason': 'required_category_playable_proof:anime',
                    'baseline': {'streamsPlayable': 0}, 'candidate': {'streamsPlayable': 0},
                })}})
        payload = build_force_prompt_payload(request)
        self.assertEqual(payload['current_network_evidence'], rows)
        self.assertEqual(payload['previous_verification']['candidate']['streamsPlayable'], 0)

    def test_regex_quotes_do_not_hide_complete_parser(self):
        source = '''function parse(html){return /["']([^"']+)["']/.exec(html);}function next(){return 1;}'''
        end = javascript_function_end(source, 0)
        self.assertEqual(source[:end], source.split('function next')[0])
        source = 'function f(url){return /^https?:/.test(url);}'
        self.assertEqual(javascript_function_end(source, 0), len(source))

    def test_live_fallback_branch_precedes_unexecuted_terminal_api(self):
        source = (
            'function decodeSource(v){return String(v);}'
            'function resolveRows(v){return decodeSource(v);}'
            '''function siteCandidates(html){return /["']([^"']+)["']/.exec(html);}'''
            'async function fetchSitePage(url){return fetch(url).then(r=>r.text());}'
            'async function siteFallback(url){return siteCandidates(await fetchSitePage(url));}'
        )
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            allowed_mutations=['provider_bloc'], provider_context={
                'preferredRuntimeMutationSource': source,
                'runtime_template_prior': {'reuseBeforeNovelBloc': True},
                'live_runtime_evidence': {'active_functions': ['siteFallback']},
            })
        units = build_force_prompt_payload(request)['new_bloc_target']['editable_units']
        self.assertTrue(units[0]['source'].startswith('async function siteFallback('))
        self.assertTrue(any('function siteCandidates(' in row['source'] for row in units))

if __name__ == '__main__': unittest.main()
