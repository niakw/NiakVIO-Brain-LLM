import unittest
import copy
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import build_force_prompt_payload
from niakvio_brain_llm.source_units import javascript_function_end
from niakvio_brain_llm.live_evidence import network_evidence, verification_feedback, non_improving_functions, observed_failure_class, executed_runtime_source, fixture_evidence, short_media_source_focus

class LiveFunctionContextTests(unittest.TestCase):
    def short_source_example(self):
        source = ('function pickPlayers(html){return html.match(/iframe/g)||[];}'
                  'async function openPlayer(url){return fetch(url).then(r=>r.text());}'
                  'function episodeRoute(q){return q.episode;}'
                  'function unusedPlayer(){return "not on the executed chain";}'
                  'function decoder(value){return value;}'
                  'async function terminalCrawl(url){var out=[];' +
                  ''.join(f'out.push(decoder({i}));' for i in range(140)) + 'return out;}'
                  'async function resolve(q){var episode=episodeRoute(q),players=pickPlayers(q.html);'
                  'return terminalCrawl(await openPlayer(players[0]));}'
                  '/* STARTFIX:CORE.TEST */function corePlayer(){return 1;}')
        live = {'active_functions': ['terminalCrawl', 'resolve', 'openPlayer'],
                'fixture_evidence': [{'fixture': 'Missing', 'streamsReturned': 0, 'expectedDurationSeconds': 1440}],
                'network_evidence': [
                    {'fixture': 'Missing', 'stage': 'media', 'status': 206,
                     'media_observation': {'signature': 'mp4', 'durationSeconds': 5, 'bytesSampled': 32768,
                                           'readState': 'data', 'cancelState': 'complete'}},
                    {'fixture': 'Missing', 'stage': 'player', 'status': 200,
                     'functions': ['fetchPage', 'terminalCrawl', 'resolve'],
                     'response_structure': {'kind': 'html', 'tags': [{'tag': 'video'}, {'tag': 'source'}]}},
                ]}
        return source, live

    def test_short_terminal_source_offers_executed_upstream_selectors(self):
        source, live = self.short_source_example()
        focus = short_media_source_focus(source, live)
        self.assertEqual(focus['selector_functions'], ['pickPlayers', 'openPlayer', 'episodeRoute'])
        self.assertEqual(focus['terminal_functions'], ['terminalCrawl'])
        self.assertEqual(focus['fixtures'][0]['sampledDurationSeconds'], 5)
        self.assertNotIn('unusedPlayer', str(focus))
        self.assertNotIn('corePlayer', str(focus))
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            allowed_mutations=['provider_bloc'], provider_context={
                'preferredRuntimeMutationSource': source.split('/* STARTFIX:CORE.')[0],
                'runtime_template_prior': {'reuseBeforeNovelBloc': True}, 'live_runtime_evidence': live})
        payload = build_force_prompt_payload(request)
        units = payload['new_bloc_target']['editable_units']
        self.assertLessEqual(len(units), 4)
        self.assertEqual(len({row['source'] for row in units}), len(units))
        for name in focus['selector_functions']:
            self.assertTrue(any('function ' + name + '(' in row['source'] for row in units), name)
        self.assertFalse(any('out.push(decoder(' in row['source'] for row in units))
        self.assertEqual(payload['source_selection_focus'], focus)

    def test_short_source_focus_requires_complete_same_fixture_evidence(self):
        source, live = self.short_source_example()
        for key, value in [('durationSeconds', None), ('durationSeconds', 1440),
                           ('readState', 'error'), ('cancelState', 'requested'),
                           ('signature', 'html'), ('bytesSampled', 4)]:
            invalid = copy.deepcopy(live)
            invalid['network_evidence'][0]['media_observation'][key] = value
            self.assertEqual(short_media_source_focus(source, invalid), {}, (key, value))
        for key, value in [('fixture', 'Other'), ('status', 503)]:
            invalid = copy.deepcopy(live)
            invalid['network_evidence'][0][key] = value
            self.assertEqual(short_media_source_focus(source, invalid), {})
        for key, value in [('expectedDurationSeconds', None), ('expectedDurationSeconds', 30), ('streamsReturned', 1)]:
            invalid = copy.deepcopy(live)
            invalid['fixture_evidence'][0][key] = value
            self.assertEqual(short_media_source_focus(source, invalid), {})
        invalid = copy.deepcopy(live)
        invalid['network_evidence'][1]['functions'] = ['corePlayer']
        self.assertEqual(short_media_source_focus(source, invalid), {})

    def test_short_source_rotation_follows_the_remaining_selector_parser(self):
        source, live = self.short_source_example()
        source = source.replace(
            'function episodeRoute(q){return q.episode;}',
            'function episodeRoute(q){return episodeRows(q.html).find(episodeScore);}'
            'function episodeRows(html){return html.match(/<option[^>]*>/g)||[];}'
            'function episodeScore(row){return /episode/.test(row);}',
        )
        source = source.replace('return html.match(/iframe/g)||[];',
                                'return (html.match(/iframe/g)||[]).map(abs);')
        source = source.replace('return fetch(url).then(r=>r.text());', 'return text(abs(url));')
        source = source.replace('/* STARTFIX:CORE.TEST */',
            'function abs(v){return String(v);}'
            'async function text(url){return fetch(url).then(r=>r.text());}'
            '/* STARTFIX:CORE.TEST */')
        live['previous_executed_edits'] = [
            {'find': 'return (html.match(/iframe/g)||[]).map(abs);', 'replace': 'return [];'},
            {'find': 'return text(abs(url));', 'replace': 'return "";'},
        ]
        live['previous_verification'] = {
            'executionObserved': True, 'materializedMutationObserved': True,
            'reason': 'insufficient_playable_stream_proof',
            'baseline': {'streamsPlayable': 0, 'streamsReturned': 0},
            'candidate': {'streamsPlayable': 0, 'streamsReturned': 0},
        }
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            allowed_mutations=['provider_bloc'], provider_context={
                'preferredRuntimeMutationSource': source.split('/* STARTFIX:CORE.')[0],
                'runtime_template_prior': {'reuseBeforeNovelBloc': True},
                'live_runtime_evidence': live,
            })
        units = build_force_prompt_payload(request)['new_bloc_target']['editable_units']
        self.assertLessEqual(len(units), 4)
        self.assertEqual(len({row['source'] for row in units}), len(units))
        for name in ('episodeRoute', 'episodeRows', 'episodeScore'):
            self.assertTrue(any('function ' + name + '(' in row['source'] for row in units), name)
        for name in ('pickPlayers', 'openPlayer', 'terminalCrawl', 'unusedPlayer', 'decoder', 'corePlayer'):
            self.assertFalse(any('function ' + name + '(' in row['source'] for row in units), name)

    def test_upstream_markup_selector_does_not_require_a_provider_specific_name(self):
        source, live = self.short_source_example()
        source = source.replace('pickPlayers', 'routeA').replace('html.match(/iframe/g)', 'html.match(/<option/g)')
        self.assertIn('routeA', short_media_source_focus(source, live)['selector_functions'])

    def test_terminal_media_evidence_is_bounded_and_contains_no_payload(self):
        live = [{'fixture': 'Missing', 'stage': 'media', 'media_observation': {
            'signature': 'mp4', 'durationSeconds': 35, 'bytesSampled': 999999,
            'readState': 'data', 'cancelState': 'complete', 'body': 'PRIVATE', 'url': 'PRIVATE',
        }}]
        rows = network_evidence(live)
        media = rows[0]['media_observation']
        self.assertEqual(media['durationSeconds'], 35)
        self.assertEqual(media['bytesSampled'], 65536)
        self.assertNotIn('PRIVATE', str(rows))
        self.assertEqual(network_evidence(rows), rows)
        live[0]['media_observation'].update(signature='PRIVATE', readState='PRIVATE', durationSeconds='PRIVATE')
        self.assertNotIn('PRIVATE', str(network_evidence(live)))
        fixtures = fixture_evidence([{'fixture': 'Missing', 'expectedDurationSeconds': 1440, 'body': 'PRIVATE'}])
        self.assertEqual(fixtures[0]['expectedDurationSeconds'], 1440)
        self.assertNotIn('PRIVATE', str(fixtures))

    def test_executed_long_provider_helper_is_visible_without_exposing_core(self):
        native = 'async function resolve(){return terminalCrawl();}'
        helper = 'async function terminalCrawl(){var out=[];' + ''.join(f'out.push({i});' for i in range(170)) + 'return out;}'
        full = helper + native + '/* STARTFIX:CORE.TEST */function coreSecret(){return 1;}'
        context = {'preferredRuntimeMutationSource': native, 'runtimeMutationSource': full,
                   'runtime_template_prior': {'reuseBeforeNovelBloc': True}}
        live = {'active_functions': ['terminalCrawl']}
        context['preferredRuntimeMutationSource'] = executed_runtime_source(context, live)
        context['live_runtime_evidence'] = live
        self.assertNotIn('coreSecret', context['preferredRuntimeMutationSource'])
        q = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
                          allowed_mutations=['provider_bloc'], provider_context=context)
        payload = build_force_prompt_payload(q)
        self.assertEqual(payload['executed_helper_context'][0]['source'], helper)
        first = payload['new_bloc_target']['editable_units'][0]
        self.assertLessEqual(len(payload['new_bloc_target']['editable_units']), 4)
        self.assertNotEqual(first['kind'], 'function_unit')
        self.assertIn(first['source'], helper)
        self.assertEqual(executed_runtime_source({'preferredRuntimeMutationSource': native,
            'runtimeMutationSource': full}, {'active_functions': ['coreSecret']}), native)

    def test_current_missing_title_supersedes_stale_variant_risk(self):
        live = {'fixture_evidence': [
            {'fixture': 'Working', 'streamsPlayable': 1, 'streamsReturned': 1},
            {'fixture': 'Missing', 'streamsPlayable': 0, 'streamsReturned': 0}],
            'network_evidence': [{'fixture': 'Missing', 'stage': 'content_lookup'}]}
        self.assertEqual(observed_failure_class('variant_coverage_gap', live), 'route_proven_gap')
        live['network_evidence'][0]['stage'] = 'player'
        self.assertEqual(observed_failure_class('variant_coverage_gap', live), 'chain_terminal_gap')
        self.assertEqual(observed_failure_class('provider_network_blocked', live), 'provider_network_blocked')
        live['fixture_evidence'][1]['streamsReturned'] = 2
        self.assertEqual(observed_failure_class('variant_coverage_gap', live), 'variant_coverage_gap')

    def test_replay_label_requires_complete_short_media_proof_before_refinement(self):
        _, live = self.short_source_example()
        self.assertEqual(observed_failure_class('candidate_replay_gap', live), 'chain_terminal_gap')
        for key, value in [('durationSeconds', None), ('durationSeconds', 1440),
                           ('bytesSampled', 4), ('readState', 'error'), ('cancelState', 'requested')]:
            invalid = copy.deepcopy(live)
            invalid['network_evidence'][0]['media_observation'][key] = value
            self.assertEqual(observed_failure_class('candidate_replay_gap', invalid), 'candidate_replay_gap')
        invalid = copy.deepcopy(live)
        invalid['network_evidence'][0]['fixture'] = 'Other'
        self.assertEqual(observed_failure_class('candidate_replay_gap', invalid), 'candidate_replay_gap')
        invalid = copy.deepcopy(live)
        invalid['fixture_evidence'][0]['streamsReturned'] = 1
        self.assertEqual(observed_failure_class('candidate_replay_gap', invalid), 'candidate_replay_gap')
        self.assertEqual(observed_failure_class('candidate_replay_gap', {}), 'candidate_replay_gap')
        self.assertEqual(observed_failure_class('provider_network_blocked', live), 'provider_network_blocked')

    def test_current_short_media_refines_replay_without_bypassing_policy_evidence(self):
        from niakvio_brain_llm.priors import build_causal_prior
        from niakvio_brain_llm.policy import build_mutation_policy
        _, live = self.short_source_example()
        request = RepairRequest(provider_id='demo', failure_class='candidate_replay_gap', status='CANDIDATE OK',
            allowed_mutations=['provider_bloc'], provider_context={'runtimeMutationSource': 'function resolve(){return [];}'},
            observations=[{'source': 'census_current', 'value': {
                'testedThisRun': True, 'candidateProof': ['same-provider candidate'],
            }}])
        self.assertFalse(build_mutation_policy(request, build_causal_prior(request, []))['allow_mutations'])
        request.failure_class = observed_failure_class(request.failure_class, live)
        prior = build_causal_prior(request, [])
        self.assertEqual(prior['strategy_prior'], 'terminal_media_extractor_with_playback_validation')
        self.assertTrue(build_mutation_policy(request, prior)['allow_mutations'])
        request.observations[0]['value']['testedThisRun'] = False
        self.assertFalse(build_mutation_policy(request, prior)['allow_mutations'])

    def test_measured_no_gain_rotates_away_from_dispatcher_but_keeps_its_callees(self):
        source = ('function playerRows(html){return html.match(/iframe/g)||[];}'
                  'async function externalPlayer(url){return fetch(url).then(r=>r.text());}'
                  'async function resolve(html){var rows=playerRows(html);return externalPlayer(rows[0]);}')
        live = {'active_functions': ['resolve'], 'previous_executed_edits': [
            {'find': 'var rows=playerRows(html);return externalPlayer(rows[0]);', 'replace': 'return [];'}],
            'previous_verification': {'executionObserved': True, 'materializedMutationObserved': True,
                'reason': 'insufficient_playable_stream_proof',
                'baseline': {'streamsPlayable': 1, 'streamsReturned': 1},
                'candidate': {'streamsPlayable': 1, 'streamsReturned': 1}}}
        self.assertEqual(non_improving_functions(source, live), ['resolve'])
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            allowed_mutations=['provider_bloc'], provider_context={
                'preferredRuntimeMutationSource': source,
                'runtime_template_prior': {'reuseBeforeNovelBloc': True}, 'live_runtime_evidence': live})
        units = build_force_prompt_payload(request)['new_bloc_target']['editable_units']
        self.assertTrue(units)
        self.assertTrue(any('function playerRows(' in row['source'] for row in units))
        self.assertFalse(any(row['source'].startswith('async function resolve(') for row in units))
        live['previous_verification']['materializedMutationObserved'] = False
        self.assertEqual(non_improving_functions(source, live), [])
        live['previous_verification']['materializedMutationObserved'] = True
        live['previous_verification']['candidate']['streamsPlayable'] = 2
        self.assertEqual(non_improving_functions(source, live), [])

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

    def test_player_markup_survives_prompt_projection_without_response_values(self):
        markup = {'rows': [{'tag': 'div', 'value_kinds': {'data-src': 'absolute_url',
                  'data-token': 'PRIVATE', 'src': 'https://private.test/PRIVATE'},
                  'count': 999999, 'distinct_values': 999999, 'raw_value': 'PRIVATE'}] * 20,
                  'sampled_chars': 999999, 'truncated': True, 'raw_body': 'PRIVATE'}
        evidence = network_evidence([{'fixture': 'Missing', 'stage': 'episode', 'status': 200,
            'response_structure': {'kind': 'html', 'player_markup': markup}}])
        projected = evidence[0]['response_structure']['player_markup']
        self.assertEqual(len(projected['rows']), 8)
        self.assertEqual(projected['rows'][0], {'tag': 'div', 'value_kinds': {'data-src': 'absolute_url'},
                                               'count': 128, 'distinct_values': 128})
        self.assertEqual(projected['sampled_chars'], 131072)
        self.assertTrue(projected['truncated'])
        self.assertNotIn('PRIVATE', str(evidence))
        self.assertNotIn('private.test', str(evidence))
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            provider_context={'live_runtime_evidence': {'network_evidence': evidence}})
        payload = build_force_prompt_payload(request)
        self.assertEqual(payload['current_network_evidence'], evidence)
        self.assertEqual(network_evidence(evidence), evidence)

    def test_repeated_player_replies_do_not_evict_the_episode_markup(self):
        events = [{'fixture': 'Missing', 'stage': 'media', 'status': 206}] * 2
        events += [{'fixture': 'Missing', 'stage': 'player', 'status': 200,
                    'response_structure': {'kind': 'html', 'player_markup': {
                        'rows': [{'tag': 'source', 'value_kinds': {'src': 'absolute_url'},
                                  'count': 1, 'distinct_values': 1}], 'sampled_chars': 20000 + index}}}
                   for index in range(8)]
        events.append({'fixture': 'Missing', 'stage': 'episode', 'status': 200,
                       'response_structure': {'kind': 'html', 'player_markup': {
                           'rows': [{'tag': 'option', 'value_kinds': {'value': 'absolute_url'},
                                     'count': 54, 'distinct_values': 54}]}}})
        evidence = network_evidence(events)
        self.assertEqual(len(evidence), 8)
        self.assertEqual([row['stage'] for row in evidence[:3]], ['media', 'player', 'episode'])
        self.assertEqual(evidence[2]['response_structure']['player_markup']['rows'][0]['count'], 54)
        self.assertEqual(network_evidence(evidence), evidence)

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
