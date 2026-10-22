import unittest
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import build_force_prompt_payload
from niakvio_brain_llm.source_units import javascript_function_end

class LiveFunctionContextTests(unittest.TestCase):
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
