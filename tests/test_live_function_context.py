import unittest
import copy
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import build_force_prompt_payload
from niakvio_brain_llm.source_units import javascript_function_end
from niakvio_brain_llm.live_evidence import network_evidence, verification_feedback, non_improving_functions, observed_failure_class, executed_runtime_source, fixture_evidence, short_media_source_focus, player_markup, response_structure

class LiveFunctionContextTests(unittest.TestCase):
    def test_opaque_address_correlation_reaches_both_prompt_channels_by_scope(self):
        scope, other_scope = 's0123456789abcdef', 'sfedcba9876543210'
        # r3/r4 stand for addresses differing only by query. The Brain receives
        # the producer's distinct labels, never either query or address.
        episode = {'fixture': 'Missing', 'stage': 'episode', 'status': 200,
            'address_scope': scope, 'request_ref': 'r1', 'response_ref': 'r2',
            'address_refs_truncated': False, 'address_trace_truncated': False,
            'response_structure': {'kind': 'html', 'player_markup': {'rows': [
                {'tag': 'div', 'value_kinds': {'data-src': 'absolute_url'},
                 'address_refs': {'data-src': ['r3', 'r4', 'r5']},
                 'address_refs_truncated': False, 'count': 3, 'distinct_values': 3}]}}}
        events = [episode] + [{'fixture': 'Missing', 'stage': 'player', 'status': 200,
            'address_scope': scope, 'request_ref': ref, 'response_ref': response,
            'referer_ref': 'r2', 'address_refs_truncated': False, 'address_trace_truncated': False}
            for ref, response in [('r3', 'r3'), ('r4', 'r4'), ('r5', 'r6')]]
        events.append({'fixture': 'Missing', 'stage': 'player', 'status': 200,
            'address_scope': other_scope, 'request_ref': 'r3', 'response_ref': 'r8',
            'address_trace_truncated': False})
        live = {'network_evidence': events, 'previous_verification': {
            'executionObserved': True, 'materializedMutationObserved': True,
            'candidate_network': events}}
        payload = build_force_prompt_payload(RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            provider_context={'live_runtime_evidence': live}))
        projected = network_evidence(events)
        self.assertEqual(payload['current_network_evidence'], projected)
        self.assertEqual(payload['previous_verification']['candidate_network'], projected)
        markup = projected[0]['response_structure']['player_markup']['rows'][0]
        refs = markup['address_refs']['data-src']
        self.assertEqual(refs, ['r3', 'r4', 'r5'])
        requests = {(row['address_scope'], row['request_ref']): row for row in projected}
        correlated = [requests[(projected[0]['address_scope'], ref)] for ref in refs]
        self.assertEqual([row['response_ref'] for row in correlated], ['r3', 'r4', 'r6'])
        self.assertEqual(requests[(other_scope, 'r3')]['response_ref'], 'r8')
        self.assertEqual(network_evidence(projected), projected)
        feedback = verification_feedback(live['previous_verification'])
        self.assertEqual(verification_feedback(feedback), feedback)
        self.assertNotIn('unused', str(projected))
        self.assertNotIn('playable', str(projected))

    def test_address_scope_is_required_for_all_optional_correlation_fields(self):
        row = {'fixture': 'Missing', 'stage': 'episode', 'request_ref': 'r1', 'response_ref': 'r2',
            'referer_ref': 'r3', 'address_refs_truncated': False, 'address_trace_truncated': False,
            'response_structure': {'kind': 'html', 'player_markup': {'rows': [
                {'tag': 'div', 'value_kinds': {'data-src': 'absolute_url'},
                 'address_refs': {'data-src': ['r1']}, 'address_refs_truncated': False}]}}}
        for scope in (None, '', 's0123456789abcde', 's0123456789abcdef0', 's0123456789abcdeF',
                      's0123456789abcdef\n', 'S0123456789abcdef', ['s0123456789abcdef'],
                      {'scope': 's0123456789abcdef'}, True, 1):
            with self.subTest(scope=scope):
                row['address_scope'] = scope
                clean = network_evidence([row])[0]
                self.assertFalse(any(key.startswith('address_') or key.endswith('_ref') for key in clean))
                markup = clean['response_structure']['player_markup']
                self.assertNotIn('address_refs', markup['rows'][0])
                self.assertNotIn('address_refs_truncated', markup['rows'][0])
                self.assertFalse(markup['truncated'])
        row.pop('address_scope')
        self.assertNotIn('address_scope', network_evidence([row])[0])
        self.assertNotIn('address_refs', player_markup(row['response_structure']['player_markup'])['rows'][0])
        self.assertNotIn('address_refs', response_structure(row['response_structure'])['player_markup']['rows'][0])

    def test_address_fields_are_independent_strict_bounded_and_optional(self):
        base = {'fixture': 'Missing', 'stage': 'player', 'address_scope': 's0123456789abcdef'}
        clean = network_evidence([base])[0]
        self.assertEqual({key: value for key, value in clean.items() if key.startswith('address_')},
                         {'address_scope': base['address_scope']})
        for number in range(1, 513):
            row = network_evidence([{**base, 'request_ref': 'r' + str(number)}])[0]
            self.assertEqual(row['request_ref'], 'r' + str(number))
            self.assertNotIn('address_refs_truncated', row)
        for invalid in ('r0', 'r00', 'r01', 'r513', 'r999', 'r-1', 'r+1', 'r1\n', 'R1',
                        'https://private.test/PRIVATE?token=PRIVATE', ['r1'], {'ref': 'r1'}, True, 1):
            with self.subTest(invalid=invalid):
                clean = network_evidence([{**base, 'request_ref': invalid, 'response_ref': 'r512',
                    'referer_ref': 'r1', 'address_refs_truncated': False, 'address_trace_truncated': False}])[0]
                self.assertNotIn('request_ref', clean)
                self.assertEqual(clean['response_ref'], 'r512')
                self.assertEqual(clean['referer_ref'], 'r1')
                self.assertTrue(clean['address_refs_truncated'])
                self.assertFalse(clean['address_trace_truncated'])
                self.assertNotIn('PRIVATE', str(clean))
                self.assertEqual(network_evidence([clean]), [clean])
        for empty in (None, ''):
            clean = network_evidence([{**base, 'request_ref': empty}])[0]
            self.assertNotIn('request_ref', clean)
            self.assertNotIn('address_refs_truncated', clean)
        for key in ('address_refs_truncated', 'address_trace_truncated'):
            for flag in (True, False, None, 0, 1, '', 'false', [], {}, ['PRIVATE']):
                with self.subTest(key=key, flag=flag):
                    clean = network_evidence([{**base, key: flag}])[0]
                    self.assertIs(clean[key], flag if type(flag) is bool else True)
                    self.assertEqual(network_evidence([clean]), [clean])

    def test_markup_address_refs_drop_forged_values_and_report_every_loss(self):
        row = {'tag': 'div', 'value_kinds': {'data-src': 'absolute_url', 'src': 'relative_url'},
            'address_refs': {'data-src': ['r1', 'r1', 'r512', 'r513', 'PRIVATE', ['r2']],
                'src': ['r' + str(number) for number in range(1, 19)],
                'href': ['r7'], 'data-token-PRIVATE': ['r8']},
            'address_refs_truncated': False, 'count': 3, 'distinct_values': 3,
            'raw_url': 'https://private.test/PRIVATE?token=PRIVATE'}
        event = {'address_scope': 's0123456789abcdef', 'response_structure': {'kind': 'html',
            'player_markup': {'rows': [row], 'truncated': False}}}
        clean = network_evidence([event])
        markup = clean[0]['response_structure']['player_markup']
        projected = markup['rows'][0]
        self.assertEqual(projected['address_refs'], {'data-src': ['r1', 'r512'],
                         'src': ['r' + str(number) for number in range(1, 17)]})
        self.assertTrue(projected['address_refs_truncated'])
        self.assertTrue(markup['truncated'])
        self.assertNotIn('PRIVATE', str(clean))
        self.assertNotIn('private.test', str(clean))
        self.assertEqual(network_evidence(clean), clean)
        for refs in (None, 'PRIVATE', [], {'data-src': 'r1'}, {'data-src': ['r0']}, {'unknown': []}):
            with self.subTest(refs=refs):
                event['response_structure']['player_markup']['rows'][0] = {
                    'tag': 'div', 'value_kinds': {'data-src': 'absolute_url'}, 'address_refs': refs}
                clean = network_evidence([event])
                markup = clean[0]['response_structure']['player_markup']
                self.assertTrue(markup['rows'][0]['address_refs_truncated'])
                self.assertTrue(markup['truncated'])
                self.assertEqual(network_evidence(clean), clean)
        for flag in (True, None, 0, 1, 'false', [], {}):
            event['response_structure']['player_markup']['rows'][0] = {
                'tag': 'div', 'value_kinds': {'src': 'absolute_url'}, 'address_refs_truncated': flag}
            markup = network_evidence([event])[0]['response_structure']['player_markup']
            self.assertTrue(markup['rows'][0]['address_refs_truncated'])
            self.assertTrue(markup['truncated'])
        event['response_structure']['player_markup']['rows'][0] = {
            'tag': 'div', 'value_kinds': {'src': 'absolute_url'}, 'address_refs': {'src': ['r1', 'r1', 'r2']}}
        markup = network_evidence([event])[0]['response_structure']['player_markup']
        self.assertEqual(markup['rows'][0]['address_refs'], {'src': ['r1', 'r2']})
        self.assertNotIn('address_refs_truncated', markup['rows'][0])
        self.assertFalse(markup['truncated'])
        event['response_structure']['player_markup']['rows'][0].pop('address_refs')
        markup = network_evidence([event])[0]['response_structure']['player_markup']
        self.assertNotIn('address_refs', markup['rows'][0])
        self.assertNotIn('address_refs_truncated', markup['rows'][0])

    def test_discarded_markup_rows_signal_lost_scoped_address_refs(self):
        good = {'tag': 'div', 'value_kinds': {'src': 'absolute_url'}}
        lost = {'tag': 'div', 'value_kinds': {'src': 'absolute_url'}, 'address_refs': {'src': ['r1']}}
        for rows in ([{**lost, 'tag': 'script'}], [{**lost, 'value_kinds': {}}], [good] * 8 + [lost]):
            with self.subTest(rows=rows):
                event = {'address_scope': 's0123456789abcdef', 'response_structure': {'kind': 'html',
                    'player_markup': {'rows': rows}}}
                clean = network_evidence([event])
                self.assertTrue(clean[0]['response_structure']['player_markup']['truncated'])
                self.assertEqual(network_evidence(clean), clean)

    def test_network_selection_marks_only_scopes_with_omitted_observations(self):
        scope, other_scope = 's0123456789abcdef', 'sfedcba9876543210'
        base = {'fixture': 'Missing', 'stage': 'player', 'status': 200,
                'address_scope': scope, 'address_trace_truncated': False}
        events = [{**base, 'request_ref': 'r' + str(index)} for index in range(1, 11)]
        events.insert(2, {**base, 'address_scope': other_scope, 'request_ref': 'r1', 'stage': 'episode'})
        events.append({**base, 'request_ref': 'r11', 'response_structure': {'kind': 'json',
            'fields': [{'path': 'data.sources', 'type': 'array'}]}})
        original = copy.deepcopy(events)
        projected = network_evidence(events)
        self.assertEqual(events, original)
        self.assertEqual(len(projected), 8)
        self.assertEqual([row['stage'] for row in projected[:2]], ['player', 'episode'])
        self.assertEqual(projected[2]['response_structure']['kind'], 'json')
        self.assertTrue(all(row['address_trace_truncated'] is True
                            for row in projected if row['address_scope'] == scope))
        self.assertFalse(next(row for row in projected if row['address_scope'] == other_scope)['address_trace_truncated'])
        self.assertEqual(network_evidence(projected), projected)
        # Equal observations can be omitted too: equality does not establish
        # that every occurrence survived the eight-event bound.
        equal = network_evidence([base] * 9)
        self.assertEqual(len(equal), 8)
        self.assertTrue(all(row['address_trace_truncated'] for row in equal))
        self.assertEqual(network_evidence(equal), equal)
        # The initial twelve-event sample can also lose a scope's observation.
        events = [{**base, 'address_scope': other_scope}] + [None] * 11 + [{**base, 'address_scope': other_scope}]
        sampled = network_evidence(events)
        self.assertTrue(sampled[0]['address_trace_truncated'])
        self.assertEqual(network_evidence(sampled), sampled)

    def test_address_diagnostics_do_not_change_source_focus_or_failure_class(self):
        source, live = self.short_source_example()
        focus = short_media_source_focus(source, live)
        failure = observed_failure_class('candidate_replay_gap', live)
        enriched = copy.deepcopy(live)
        for index, row in enumerate(enriched['network_evidence'], 1):
            row.update(address_scope='s0123456789abcdef', request_ref='r' + str(index),
                       response_ref='r' + str(index), address_refs_truncated=False,
                       address_trace_truncated=False)
        self.assertEqual(short_media_source_focus(source, enriched), focus)
        self.assertEqual(observed_failure_class('candidate_replay_gap', enriched), failure)

    def test_address_ref_loss_does_not_displace_structurally_distinct_events(self):
        events = [{'fixture': 'Missing', 'stage': 'player', 'status': status,
            'response_structure': {'kind': 'html', 'player_markup': {'rows': [
                {'tag': 'div', 'value_kinds': {'src': 'absolute_url'}}], 'truncated': False}}}
            for status in [200, 200, 201, 202, 203, 204, 205, 206, 207]]
        baseline = network_evidence(events)
        events[1]['response_structure']['player_markup']['rows'][0]['address_refs'] = {'src': ['r513']}
        for index, row in enumerate(events, 1):
            row.update(address_scope='s0123456789abcdef', request_ref='r' + str(index),
                       address_refs_truncated=False, address_trace_truncated=False)
        projected = network_evidence(events)
        self.assertEqual([row['status'] for row in projected], [row['status'] for row in baseline])
        self.assertEqual([row['status'] for row in projected], [200, 201, 202, 203, 204, 205, 206, 207])
        self.assertTrue(all(row['address_trace_truncated'] for row in projected))
        self.assertEqual(network_evidence(projected), projected)

    def test_reader_agent_control_reaches_both_prompt_channels_without_private_values(self):
        signal = {'content_kind': 'html', 'url_relation': 'same_url', 'body_state': 'not_sampled',
                  'sampled_bytes': 0, 'page_signal': 'unknown'}
        control = {'attempted': True, 'profile_source': 'prior_successful_html', 'changed_header': 'user-agent',
                   'status': 200, 'outcome': 'response', 'http_observation': signal}
        private = 'PRIVATE_URL_HEADER_AGENT_BODY'
        raw = {'fixture': 'Missing', 'stage': 'player', 'host': 'reader.test', 'status': 403,
               'reader_user_agent_probe': {**control, 'profile_source': private, 'changed_header': private,
                   'url': 'https://private.test/' + private, 'headers': {'User-Agent': private, 'Cookie': private},
                   'body': private, 'http_observation': {**signal, 'raw_body': private, 'url': private}}}
        live = {'network_evidence': [raw], 'previous_verification': {
            'executionObserved': True, 'materializedMutationObserved': True, 'candidate_network': [raw],
        }}
        payload = build_force_prompt_payload(RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            allowed_mutations=['provider_bloc'], provider_context={'live_runtime_evidence': live}))
        self.assertEqual(payload['current_network_evidence'][0]['reader_user_agent_probe'], control)
        self.assertEqual(payload['previous_verification']['candidate_network'][0]['reader_user_agent_probe'], control)
        self.assertNotIn(private, str(payload))
        projected = network_evidence([raw])
        self.assertEqual(network_evidence(projected), projected)
        feedback = verification_feedback(live['previous_verification'])
        self.assertEqual(verification_feedback(feedback), feedback)
        # Exact booleans, bounded status, and dependent outcomes are independently
        # checked by the Brain instead of trusting the producer's projection.
        for attempted, outcome, status, expected_attempt, expected_outcome, expected_status in [
            (True, 'response', 206, True, 'response', 206),
            (True, 'response', True, True, 'response', None),
            (True, 'response', 200.0, True, 'response', None),
            (True, 'response', 99, True, 'response', None),
            (True, 'response', 600, True, 'response', None),
            (True, 'timeout', 200, True, 'timeout', None),
            (True, 'error', 403, True, 'error', None),
            (True, [private], 403, True, 'error', None),
            (True, 'budget_exhausted', 200, True, 'error', None),
            (False, 'missing_profile', 200, False, 'missing_profile', None),
            (False, 'budget_exhausted', 200, False, 'budget_exhausted', None),
            (False, 'response', 200, False, 'missing_profile', None),
            (1, 'response', 200, False, 'missing_profile', None),
            ('true', 'response', 200, False, 'missing_profile', None),
        ]:
            with self.subTest(attempted=attempted, outcome=outcome, status=status):
                raw['reader_user_agent_probe'] = {**control, 'attempted': attempted, 'outcome': outcome, 'status': status,
                    'raw': private, 'http_observation': {'content_kind': [private], 'url_relation': private,
                        'body_state': private, 'page_signal': private, 'sampled_bytes': 999999, 'raw': private}}
                clean = network_evidence([raw])[0]['reader_user_agent_probe']
                self.assertEqual((clean['attempted'], clean['outcome'], clean['status']),
                                 (expected_attempt, expected_outcome, expected_status))
                self.assertEqual(clean['http_observation']['sampled_bytes'], 8192)
                self.assertNotIn(private, str(clean))
                self.assertEqual(network_evidence(network_evidence([raw])), network_evidence([raw]))
        for absent in (None, {}, [], 'PRIVATE', 0):
            raw['reader_user_agent_probe'] = absent
            self.assertNotIn('reader_user_agent_probe', network_evidence([raw])[0])
        raw.pop('reader_user_agent_probe')
        self.assertNotIn('reader_user_agent_probe', network_evidence([raw])[0])

    def test_observed_media_diagnostic_bridge_is_scoped_bounded_and_not_playback_proof(self):
        scope, private = 's0123456789abcdef', 'PRIVATE_URL_COOKIE_HEADER_BODY'
        media = {'signature': 'mp4', 'durationSeconds': 1440, 'bytesSampled': 80,
                 'readState': 'complete', 'cancelState': 'complete'}
        http = {'content_kind': 'media', 'url_relation': 'same_origin',
                'body_state': 'sampled', 'page_signal': 'none', 'sampled_bytes': 80}
        control = {'attempted': True, 'source_ref': 'r8', 'template_ref': 'r5',
                   'status': 206, 'outcome': 'response',
                   'media_observation': media, 'http_observation': http}
        raw = {'fixture': 'Missing', 'stage': 'media', 'address_scope': scope,
               'request_ref': 'r5', 'response_ref': 'r6',
               'observed_media_probe': {**control, 'url': 'https://private.test/' + private,
                   'headers': {'Cookie': private, 'Authorization': private},
                   'body': private, 'media_observation': {**media, 'raw': private},
                   'http_observation': {**http, 'url': private, 'body': private}}}
        live = {'network_evidence': [raw], 'previous_verification': {
            'executionObserved': True, 'materializedMutationObserved': True,
            'candidate_network': [raw]}}
        payload = build_force_prompt_payload(RepairRequest(provider_id='demo',
            failure_class='chain_terminal_gap', provider_context={'live_runtime_evidence': live}))
        current = payload['current_network_evidence'][0]['observed_media_probe']
        previous = payload['previous_verification']['candidate_network'][0]['observed_media_probe']
        self.assertEqual(current, control)
        self.assertEqual(previous, control)
        self.assertNotIn(private, str(payload))
        self.assertNotIn('playable', str(current))
        self.assertEqual(network_evidence(network_evidence([raw])), network_evidence([raw]))

        for attempted, outcome, status, expected in [
            (True, 'response', 200, (True, 'response', 200)),
            (True, 'response', True, (True, 'response', None)),
            (True, 'response', 600, (True, 'response', None)),
            (True, 'timeout', 206, (True, 'timeout', None)),
            (True, 'error', 206, (True, 'error', None)),
            (True, [private], 206, (True, 'error', None)),
            (False, 'budget_exhausted', 206, (False, 'budget_exhausted', None)),
        ]:
            with self.subTest(attempted=attempted, outcome=outcome, status=status):
                raw['observed_media_probe'] = {**control, 'attempted': attempted,
                    'outcome': outcome, 'status': status, 'body': private,
                    'media_observation': {'signature': [private], 'readState': [private],
                        'cancelState': [private], 'bytesSampled': 999999, 'durationSeconds': 9999999},
                    'http_observation': {'content_kind': [private], 'sampled_bytes': 999999,
                        'raw': private}}
                clean = network_evidence([raw])[0]['observed_media_probe']
                self.assertEqual((clean['attempted'], clean['outcome'], clean['status']), expected)
                self.assertEqual(clean['media_observation']['bytesSampled'], 32768)
                self.assertEqual(clean['http_observation']['sampled_bytes'], 8192)
                self.assertEqual(clean['media_observation']['signature'], 'unknown')
                self.assertNotIn(private, str(clean))
                self.assertEqual(network_evidence(network_evidence([raw])), network_evidence([raw]))

        for bad in ({**control, 'source_ref': 'r513'}, {**control, 'template_ref': 'r0'},
                    {**control, 'source_ref': 'https://private.test/' + private},
                    {**control, 'attempted': 1}, {**control, 'attempted': False, 'outcome': 'response'},
                    {}, None, [private], private):
            with self.subTest(bad=bad):
                raw['observed_media_probe'] = bad
                self.assertNotIn('observed_media_probe', network_evidence([raw])[0])
        raw['observed_media_probe'] = control
        raw.pop('address_scope')
        self.assertNotIn('observed_media_probe', network_evidence([raw])[0])
        raw['address_scope'] = 's0123456789abcdeF'
        self.assertNotIn('observed_media_probe', network_evidence([raw])[0])

        # A diagnostic is not a new structural alternative: it must not crowd
        # out earlier player/episode observations in the eight-event prompt cap.
        repeated = [{'fixture': 'Missing', 'stage': 'media', 'status': 206,
                     'address_scope': scope, 'request_ref': 'r' + str(i)}
                    for i in range(1, 13)]
        baseline = network_evidence(repeated)
        repeated[-1]['observed_media_probe'] = control
        selected = network_evidence(repeated)
        self.assertEqual([x.get('request_ref') for x in selected],
                         [x.get('request_ref') for x in baseline])
        self.assertFalse(any('observed_media_probe' in x for x in selected))

    def test_http_failure_observation_reaches_prompt_as_fixed_categories(self):
        signal = {'content_kind': 'html', 'url_relation': 'same_url', 'body_state': 'complete',
                  'sampled_bytes': 512, 'page_signal': 'challenge_markup'}
        raw = {'fixture': 'Missing', 'stage': 'player', 'host': 'reader.test', 'status': 403,
               'http_observation': {**signal, 'raw_body': 'PRIVATE', 'cookie': 'PRIVATE'}}
        live = {'network_evidence': [raw], 'previous_verification': {
            'executionObserved': True, 'materializedMutationObserved': True,
            'candidate_network': [raw],
        }}
        payload = build_force_prompt_payload(RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            allowed_mutations=['provider_bloc'], provider_context={'live_runtime_evidence': live}))
        # Both the current preflight and an executed candidate retain the clue.
        self.assertEqual(payload['current_network_evidence'][0]['http_observation'], signal)
        self.assertEqual(payload['previous_verification']['candidate_network'][0]['http_observation'], signal)
        self.assertNotIn('PRIVATE', str(payload))
        projected = network_evidence([raw])
        self.assertEqual(network_evidence(projected), projected)
        for value in ({key: ['PRIVATE'] for key in signal}, {**signal, 'sampled_bytes': 999999},
                      {key: 'https://private.test/PRIVATE' for key in signal}):
            raw['http_observation'] = value
            clean = network_evidence([raw])[0]['http_observation']
            self.assertLessEqual(clean['sampled_bytes'], 8192)
            self.assertNotIn('PRIVATE', str(clean))

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

    def admission_example(self):
        source, live = self.short_source_example()
        source = source.replace('var out=[];', 'var routes=[url].filter(permitRoute);var out=[];', 1)
        source = source.replace('/* STARTFIX:CORE.TEST */',
            'function permitRoute(url){return !/\\{status:/.test(url)&&validateMedia(url)&&routeLike(url)&&routeScore(url)>0;}'
            'function validateMedia(url){return new URL(url).pathname.includes(".mp4");}'
            'function routeLike(url){return new URL(url).pathname.includes("/embed/");}'
            'function routeScore(url){return new URL(url).searchParams.size;}'
            '/* STARTFIX:CORE.TEST */')
        live['previous_executed_edits'] = [{'find': 'return html.match(/iframe/g)||[];'}]
        live['previous_verification'] = {'executionObserved': True, 'materializedMutationObserved': True,
            'reason': 'insufficient_playable_stream_proof',
            'baseline': {'streamsPlayable': 0, 'streamsReturned': 0},
            'candidate': {'streamsPlayable': 0, 'streamsReturned': 0}}
        live['network_evidence'].append({'fixture': 'Missing', 'stage': 'player', 'status': 200,
            'response_structure': {'kind': 'html', 'player_markup': {'rows': [
                {'tag': 'iframe', 'value_kinds': {'src': 'absolute_url'}, 'count': 1, 'distinct_values': 1,
                 'value_shapes': {'src': {'kind': 'page_extension', 'origin': 'cross_origin'}}}]}}})
        return source, live

    def test_declared_foreign_reader_after_no_gain_exposes_seed_admission(self):
        source, live = self.admission_example()
        focus = short_media_source_focus(source, live)
        names = ['permitRoute', 'routeLike', 'routeScore']
        self.assertEqual(focus['seed_admission_functions'], names)
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            allowed_mutations=['provider_bloc'], provider_context={
                'preferredRuntimeMutationSource': source.split('/* STARTFIX:CORE.')[0],
                'runtime_template_prior': {'reuseBeforeNovelBloc': True}, 'live_runtime_evidence': live})
        payload = build_force_prompt_payload(request)
        units = payload['new_bloc_target']['editable_units']
        self.assertEqual(len(units), 3)
        for name in names:
            self.assertTrue(any('function '+name+'(' in row['source'] for row in units), name)
        for name in ('validateMedia', 'terminalCrawl', 'pickPlayers', 'corePlayer'):
            self.assertFalse(any('function '+name+'(' in row['source'] for row in units), name)
        self.assertEqual(payload['source_selection_focus']['reason'], 'declared_reader_seed_admission')

    def test_seed_admission_focus_requires_proved_no_gain_and_foreign_reader(self):
        source, live = self.admission_example()
        variants = []
        invalid = copy.deepcopy(live)
        invalid['previous_verification']['executionObserved'] = False
        variants.append(invalid)
        for key, value in [('kind', 'image_extension'), ('origin', 'same_origin')]:
            invalid = copy.deepcopy(live)
            invalid['network_evidence'][-1]['response_structure']['player_markup']['rows'][0]['value_shapes']['src'][key] = value
            variants.append(invalid)
        invalid = copy.deepcopy(live)
        invalid['network_evidence'][-1]['fixture'] = 'Other'
        variants.append(invalid)
        for invalid in variants:
            self.assertNotIn('seed_admission_functions', short_media_source_focus(source, invalid))
        self.assertNotIn('seed_admission_functions', short_media_source_focus(
            source.replace('permitRoute', 'validateRoute'), live))

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

    def test_address_shapes_reach_the_prompt_without_urls_or_unknown_values(self):
        markup = {'rows': [{'tag': 'div', 'value_kinds': {'data-src': 'absolute_url'},
            'value_shapes': {'data-src': {'kind': 'image_extension', 'origin': 'cross_origin', 'url': 'PRIVATE'},
                             'src': {'kind': 'PRIVATE', 'origin': 'PRIVATE'}},
            'count': 3, 'distinct_values': 3},
            {'tag': 'option', 'value_kinds': {'value': 'absolute_url'},
             'value_shapes': {'value': {'kind': 'page_extension', 'origin': 'same_origin'}},
             'count': 54, 'distinct_values': 54},
            {'tag': 'iframe', 'value_kinds': {'src': 'absolute_url'},
             'value_shapes': {'src': {'kind': 'https://private.test/PRIVATE', 'origin': 'cross_origin'}},
             'count': 1, 'distinct_values': 1}]}
        evidence = network_evidence([{'fixture': 'Missing', 'stage': 'episode', 'status': 200,
            'response_structure': {'kind': 'html', 'player_markup': markup}}])
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            provider_context={'live_runtime_evidence': {'network_evidence': evidence}})
        projected = build_force_prompt_payload(request)['current_network_evidence'][0]['response_structure']['player_markup']
        self.assertEqual(projected['rows'][0]['value_shapes'],
                         {'data-src': {'kind': 'image_extension', 'origin': 'cross_origin'}})
        self.assertEqual(projected['rows'][1]['value_shapes'],
                         {'value': {'kind': 'page_extension', 'origin': 'same_origin'}})
        self.assertNotIn('value_shapes', projected['rows'][2])
        self.assertNotIn('PRIVATE', str(projected))
        self.assertNotIn('private.test', str(projected))
        self.assertEqual(network_evidence(evidence), evidence)

    def test_regex_quotes_do_not_hide_complete_parser(self):
        source = '''function parse(html){return /["']([^"']+)["']/.exec(html);}function next(){return 1;}'''
        end = javascript_function_end(source, 0)
        self.assertEqual(source[:end], source.split('function next')[0])
        source = 'function f(url){return /^https?:/.test(url);}'
        self.assertEqual(javascript_function_end(source, 0), len(source))

    def test_complete_editable_function_keeps_literal_brace_regex(self):
        source = r'function eligible(url){return !/\{status:/.test(url);}'
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            allowed_mutations=['provider_bloc'], provider_context={
                'preferredRuntimeMutationSource': source,
                'runtime_template_prior': {'reuseBeforeNovelBloc': True},
                'live_runtime_evidence': {'active_functions': ['eligible']}})
        units = build_force_prompt_payload(request)['new_bloc_target']['editable_units']
        self.assertTrue(any(row['source'] == source and row['kind'] == 'function_unit' for row in units))

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
