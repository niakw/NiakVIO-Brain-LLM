import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.live_evidence import network_evidence, verification_feedback, observed_failure_class
from niakvio_brain_llm.prompting import build_force_prompt_payload


SCOPE = 's0123456789abcdef'
PRIVATE = 'PRIVATE_URL_HEADER_BODY_TOKEN'
ROOT = Path(__file__).resolve().parents[1]
NIAK_PATHS = [Path(os.environ['NIAKVIO_ROOT'])] if os.environ.get('NIAKVIO_ROOT') else [
    ROOT / 'niakvio', ROOT.parent / 'NiakVIO', ROOT.parent / 'niakvio']
NIAK_ROOT = next((path for path in NIAK_PATHS
                  if (path / 'scripts' / 'observed_media_evidence.py').is_file()), None)


def probe(seconds=1440):
    return {'attempted': True, 'source_ref': 'r67', 'template_ref': 'r55', 'status': 206,
            'outcome': 'response', 'media_observation': {
                'signature': 'mp4', 'durationSeconds': seconds, 'bytesSampled': 32768,
                'readState': 'data', 'cancelState': 'complete'},
            'http_observation': {'content_kind': 'media', 'url_relation': 'same_url',
                'body_state': 'not_sampled', 'sampled_bytes': 0, 'page_signal': 'unknown'}}


def parent(control):
    return {'address_scope': SCOPE, 'address_refs_truncated': False, 'address_trace_truncated': False,
            'fixture': 'Missing', 'host': 'reader.test', 'stage': 'player', 'status': 200,
            'request_ref': 'r54', 'response_ref': 'r54', 'functions': ['playerPageTitle'],
            'observed_media_probe': control,
            'response_structure': {'kind': 'html', 'player_markup': {'rows': [
                {'tag': 'source', 'value_kinds': {'src': 'absolute_url'},
                 'address_refs': {'src': ['r67']}, 'address_refs_truncated': False,
                 'count': 1, 'distinct_values': 1}]}}}


class ObservedMediaContextTests(unittest.TestCase):
    def test_five_and_1440_second_diagnostics_reach_prompt_without_stream_authority(self):
        for seconds in (5, 1440):
            with self.subTest(seconds=seconds):
                expected = probe(seconds)
                raw = parent({**expected, 'url': PRIVATE, 'headers': {'Cookie': PRIVATE}, 'body': PRIVATE})
                fixtures = [{'fixture': 'Missing', 'expectedDurationSeconds': 1440,
                             'streamsReturned': 0, 'streamsPlayable': 0}]
                feedback = {'executionObserved': True, 'materializedMutationObserved': True,
                    'reason': 'insufficient_playable_stream_proof', 'candidate_network': [raw],
                    'baseline': {'streamsPlayable': 0, 'streamsReturned': 0, 'fixtureCoverage': fixtures},
                    'candidate': {'streamsPlayable': 0, 'streamsReturned': 0, 'fixtureCoverage': fixtures}}
                normalized = verification_feedback(feedback)
                self.assertEqual(verification_feedback(normalized), normalized)
                payload = build_force_prompt_payload(RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
                    provider_context={'live_runtime_evidence': {'network_evidence': [raw],
                        'fixture_evidence': fixtures, 'previous_verification': feedback}}))
                for channel in (payload['current_network_evidence'], payload['previous_verification']['candidate_network']):
                    self.assertEqual(channel[0]['observed_media_probe'], expected)
                    self.assertEqual(network_evidence(channel), channel)
                self.assertEqual(payload['current_fixture_evidence'][0]['streamsPlayable'], 0)
                self.assertEqual(payload['current_fixture_evidence'][0]['streamsReturned'], 0)
                self.assertEqual(payload['previous_verification']['candidate']['streamsPlayable'], 0)
                self.assertEqual(payload['previous_verification']['candidate']['streamsReturned'], 0)
                self.assertIn('never a returned or validated stream', payload['observed_media_probe_policy'])
                self.assertNotIn(PRIVATE, json.dumps(payload))

    def test_independent_projection_requires_scope_refs_and_exact_boolean(self):
        expected = probe()
        raw = parent({**expected, 'url': 'https://private.test/' + PRIVATE,
                      'headers': {'Authorization': PRIVATE}, 'body': PRIVATE})
        projected = network_evidence([raw])
        self.assertEqual(projected[0]['observed_media_probe'], expected)
        self.assertEqual(network_evidence(projected), projected)
        self.assertNotIn(PRIVATE, json.dumps(projected))
        independent = network_evidence([{**raw, 'request_ref': PRIVATE}])[0]
        self.assertEqual(independent['observed_media_probe'], expected)
        self.assertTrue(independent['address_refs_truncated'])
        self.assertNotIn(PRIVATE, json.dumps(independent))
        for scope in (None, '', 'S0123456789abcdef', 's0123456789abcdeF', SCOPE + '\n', [SCOPE]):
            with self.subTest(scope=scope):
                self.assertNotIn('observed_media_probe', network_evidence([{**raw, 'address_scope': scope}])[0])
        for value in (None, {}, [], PRIVATE):
            self.assertNotIn('observed_media_probe', network_evidence([parent(value)])[0])
        for key in ('source_ref', 'template_ref'):
            for value in ('r0', 'r01', 'r513', 'r1\n', PRIVATE, 1, True, []):
                with self.subTest(key=key, value=value):
                    self.assertNotIn('observed_media_probe', network_evidence([parent({**expected, key: value})])[0])
            for value in ('r1', 'r512'):
                self.assertEqual(network_evidence([parent({**expected, key: value})])[0]['observed_media_probe'][key], value)
        for attempted in (None, 1, 0, 'true', [], {}):
            self.assertNotIn('observed_media_probe', network_evidence([parent({**expected, 'attempted': attempted})])[0])
        self.assertNotIn('observed_media_probe', network_evidence([parent({**expected, 'attempted': False})])[0])

    def test_probe_status_outcomes_counters_and_enums_are_revalidated(self):
        original = probe()
        for outcome in ('response', 'timeout', 'error', PRIVATE, [], {}):
            for status in (206, True, 206.5, 99, 600, PRIVATE):
                with self.subTest(outcome=outcome, status=status):
                    value = {**original, 'status': status, 'outcome': outcome,
                        'media_observation': {'signature': [PRIVATE], 'durationSeconds': 99999999,
                            'bytesSampled': 999999, 'readState': PRIVATE, 'cancelState': [PRIVATE], 'body': PRIVATE},
                        'http_observation': {'content_kind': [PRIVATE], 'sampled_bytes': 999999, 'body': PRIVATE}}
                    projected = network_evidence([parent(value)])
                    clean = projected[0]['observed_media_probe']
                    self.assertEqual(clean['status'], status if outcome == 'response' and type(status) is int
                                     and 100 <= status <= 599 else None)
                    self.assertEqual(clean['outcome'], outcome if isinstance(outcome, str)
                                     and outcome in {'response', 'timeout', 'error'} else 'error')
                    self.assertEqual(clean['media_observation'], {'signature': 'unknown', 'durationSeconds': 1209600,
                                     'bytesSampled': 32768, 'readState': 'not_read', 'cancelState': 'not_requested'})
                    self.assertEqual(clean['http_observation']['sampled_bytes'], 8192)
                    self.assertNotIn(PRIVATE, json.dumps(clean))
                    self.assertEqual(network_evidence(projected), projected)
        budget = network_evidence([parent({**original, 'attempted': False, 'outcome': 'budget_exhausted'})])
        self.assertFalse(budget[0]['observed_media_probe']['attempted'])
        self.assertIsNone(budget[0]['observed_media_probe']['status'])
        self.assertEqual(network_evidence(budget), budget)
        noninteger = network_evidence([parent({**original, 'media_observation': {
            'durationSeconds': True, 'bytesSampled': '32768'}})])[0]['observed_media_probe']['media_observation']
        self.assertIsNone(noninteger['durationSeconds'])
        self.assertEqual(noninteger['bytesSampled'], 0)

    def test_diagnostic_parent_survives_bounded_selection_without_stream_authority(self):
        events = [parent(None) for _ in range(9)]
        for row, status in zip(events, [200, 200, 201, 202, 203, 204, 205, 206, 207]):
            row['status'] = status
        before = network_evidence(events)
        events[1]['observed_media_probe'] = probe()
        after = network_evidence(events)
        self.assertEqual(len(after), len(before))
        self.assertEqual(after[0], before[0])
        self.assertEqual(after[1]['observed_media_probe'], probe())
        self.assertEqual(network_evidence(after), after)
        live = {'network_evidence': [parent(probe())], 'fixture_evidence': [
            {'fixture': 'Missing', 'expectedDurationSeconds': 1440, 'streamsReturned': 0, 'streamsPlayable': 0}]}
        self.assertEqual(observed_failure_class('candidate_replay_gap', live), 'candidate_replay_gap')
        payload = build_force_prompt_payload(RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            provider_context={'live_runtime_evidence': live}))
        self.assertEqual(payload['current_fixture_evidence'][0]['streamsPlayable'], 0)
        self.assertEqual(payload['current_fixture_evidence'][0]['streamsReturned'], 0)
        self.assertNotIn('source_selection_focus', payload)
        policy = payload['observed_media_probe_policy']
        for phrase in ('never a returned or validated stream', 'episode identity', 'address_scope',
                       'five-second', '1440-second', 'inconclusive', 'previous_verification'):
            self.assertIn(phrase, policy)

    @unittest.skipUnless(NIAK_ROOT, 'integration requires a NiakVIO checkout with observed media evidence')
    def test_actual_evaluation_and_feedback_normalizers_reach_both_prompt_channels(self):
        code = '''import json, sys
sys.path.insert(0, sys.argv[1] + '/scripts')
import evaluate_brain_llm_force_candidates as verifier
from run_hosted_brain_repair_loop import verification_feedback
summary = verifier.result_summary(json.load(sys.stdin))
feedback = verification_feedback({'rows': [{'executionObserved': True, 'materializedMutationObserved': True,
    'reason': 'insufficient_playable_stream_proof', 'baseline': summary, 'candidate': summary}]})
print(json.dumps({'summary': summary, 'feedback': feedback}))
'''
        for seconds in (5, 1440):
            with self.subTest(seconds=seconds):
                control = probe(seconds)
                event = parent({**control, 'url': PRIVATE, 'headers': {'Cookie': PRIVATE}, 'body': PRIVATE})
                event['provider_function_names'] = event.pop('functions')
                template = {'address_scope': SCOPE, 'address_refs_truncated': False, 'address_trace_truncated': False,
                    'request_ref': 'r55', 'response_ref': 'r55', 'referer_ref': 'r54', 'stage': 'media',
                    'host': 'media.test', 'status': 206, 'media_observation': probe(5)['media_observation']}
                evaluation = {'provider': 'demo', 'tests': [{'fixture': {'label': 'Missing', 'category': 'anime',
                    'expectedDurationMinutes': 24}, 'streams_returned': 0, 'streams_playable': 0,
                    'network_observations': [event, template]}]}
                result = json.loads(subprocess.check_output([sys.executable, '-c', code, str(NIAK_ROOT)],
                    input=json.dumps(evaluation), text=True, cwd=NIAK_ROOT))
                self.assertEqual(result['summary']['networkTrace'][0]['observedMediaProbe'], control)
                self.assertEqual(result['summary']['streamsPlayable'], 0)
                feedback = verification_feedback(result['feedback'])
                self.assertEqual(feedback['candidate_network'][0]['observed_media_probe'], control)
                self.assertEqual(verification_feedback(feedback), feedback)
                live = {'network_evidence': result['feedback']['candidate_network'],
                        'fixture_evidence': result['summary']['fixtureCoverage'], 'previous_verification': result['feedback']}
                payload = build_force_prompt_payload(RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
                    provider_context={'live_runtime_evidence': live}))
                current = payload['current_network_evidence']
                previous = payload['previous_verification']['candidate_network']
                for channel in (current, previous):
                    self.assertEqual(channel[0]['observed_media_probe'], control)
                    self.assertEqual(channel[1]['media_observation']['durationSeconds'], 5)
                    self.assertEqual(network_evidence(channel), channel)
                self.assertEqual(payload['current_fixture_evidence'][0]['expectedDurationSeconds'], 1440)
                self.assertEqual(payload['previous_verification']['candidate']['streamsPlayable'], 0)
                self.assertEqual(payload['previous_verification']['candidate']['streamsReturned'], 0)
                self.assertNotIn(PRIVATE, json.dumps(payload))

    def test_late_repeated_reader_control_survives_phase_and_shape_selection(self):
        events = []
        for index, stage in enumerate(('player', 'search', 'content_lookup', 'episode', 'media')):
            row = parent(None)
            row.update(stage=stage, status=200 + index)
            events.append(row)
        events += [dict(events[0]) for _ in range(5)]
        events[-1]['observed_media_probe'] = probe(5)
        selected = network_evidence(events)
        self.assertEqual([row['stage'] for row in selected[:5]],
                         ['player', 'search', 'content_lookup', 'episode', 'media'])
        self.assertEqual(selected[5]['observed_media_probe'], probe(5))
        self.assertTrue(selected[5]['address_trace_truncated'])
        self.assertEqual(network_evidence(selected), selected)


if __name__ == '__main__':
    unittest.main()
