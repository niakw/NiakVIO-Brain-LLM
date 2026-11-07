import ast
import copy
import json
from pathlib import Path
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.live_evidence import public_domain_references, domain_reference_focus, fixture_evidence, verification_feedback, network_evidence, NETWORK_ERROR_CODES
from niakvio_brain_llm.prompting import build_force_prompt_payload


SHA = 'a' * 40
REFERENCE = {'origin': 'https://anime-sama.to',
             'source_url': 'https://github.com/Gowaru/gowaru-nuvio-providers/blob/' + SHA + '/src/anime-sama/http.js',
             'source_sha': SHA}


def evidence(status=404):
    return {'public_domain_references': [dict(REFERENCE)],
            'fixture_evidence': [{'fixture': 'JJK', 'streamsReturned': 0, 'streamsPlayable': 0}],
            'network_evidence': [{'fixture': 'JJK', 'host': 'old-provider.org', 'stage': 'search', 'status': status}]}


def production_scope_order(request):
    path = Path(__file__).resolve().parents[1] / 'scripts/plan_batch_from_checkout.py'
    tree = ast.parse(path.read_text())
    function = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == '_force_scope_order')
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['_force_scope_order'](request)


class PublicDomainReferenceTests(unittest.TestCase):
    def test_network_error_codes_reach_prompt_only_from_fixed_allowlist(self):
        for code in NETWORK_ERROR_CODES:
            row = {'fixture': 'JJK', 'stage': 'content_lookup', 'host': 'provider.org',
                   'status': None, 'error_code': code}
            live = evidence(None)
            live['network_evidence'] = [row]
            live['previous_verification'] = {'candidate_network': [row]}
            payload = build_force_prompt_payload(RepairRequest(provider_id='demo',
                failure_class='chain_terminal_gap', provider_context={'live_runtime_evidence': live}))
            self.assertEqual(payload['current_network_evidence'][0]['error_code'], code)
            self.assertEqual(payload['previous_verification']['candidate_network'][0]['error_code'], code)
            self.assertFalse(domain_reference_focus(live))
        for invalid in ('PRIVATE', 'enotfound', 'ENOTFOUND\n', True, [], {}):
            clean = network_evidence([{'error_code': invalid}])
            self.assertNotIn('error_code', clean[0])
            self.assertNotIn('PRIVATE', json.dumps(clean))

    def test_optional_decoded_control_counter_reaches_fixture_feedback_without_probe_payloads(self):
        for raw, expected in ((1, 1), (999, 8), (True, 0), ('1', 0), (-1, 0)):
            with self.subTest(raw=raw):
                fixture = {'fixture': 'JJK', 'streamsReturned': 0, 'streamsPlayable': 0,
                           'decodedMediaControls': raw, 'probes': ['PRIVATE']}
                clean = fixture_evidence([fixture])
                self.assertEqual(clean[0]['decodedMediaControls'], expected)
                self.assertEqual(fixture_evidence(clean), clean)
                feedback = verification_feedback({'candidate': {'fixtureCoverage': [fixture]}})
                self.assertEqual(feedback['candidate']['fixtureCoverage'][0]['decodedMediaControls'], expected)
                self.assertNotIn('PRIVATE', json.dumps(feedback))
        self.assertNotIn('decodedMediaControls', fixture_evidence([{'fixture': 'JJK'}])[0])

    def test_public_immutable_candidates_are_bounded_and_strip_authority(self):
        refs = [{**REFERENCE, 'origin': 'https://provider' + str(index) + '.org',
                 'publicationAuthority': True, 'body': 'PRIVATE'} for index in range(5)]
        clean = public_domain_references(refs)
        self.assertEqual(len(clean), 3)
        self.assertEqual(public_domain_references(clean), clean)
        self.assertEqual(set(clean[0]), {'origin', 'source_url', 'source_sha'})
        self.assertNotIn('PRIVATE', json.dumps(clean))
        raw = {**REFERENCE, 'source_url': 'https://raw.githubusercontent.com/Gowaru/gowaru-nuvio-providers/'
               + SHA + '/src/anime-sama/http.js'}
        self.assertEqual(public_domain_references([raw]), [raw])

    def test_invalid_origins_sources_and_revisions_do_not_reach_prompt(self):
        bad_origins = ['http://anime-sama.to', 'https://anime-sama.to/', 'https://anime-sama.to/path',
                       'https://anime-sama.to?token=PRIVATE', 'https://anime-sama.to#PRIVATE',
                       'https://user:PRIVATE@anime-sama.to', 'https://anime-sama.to:443',
                       'https://127.0.0.1', 'https://[::1]', 'https://localhost',
                       'https://site.local', 'https://site.internal', 'https://site.test',
                       'https://anime-sama.to\n', 'https://anime-sama.to\\PRIVATE', [], True]
        bad_sources = ['https://github.com/Gowaru/repo/blob/main/src.js',
                       REFERENCE['source_url'] + '?token=PRIVATE', REFERENCE['source_url'] + '#PRIVATE',
                       REFERENCE['source_url'].replace(SHA, 'b' * 40),
                       'https://github.com.evil.org/owner/repo/blob/' + SHA + '/src.js',
                       'https://github.com/owner/repo/blob/' + SHA + '/../PRIVATE',
                       'https://PRIVATE@github.com/owner/repo/blob/' + SHA + '/src.js',
                       'https://github.com/owner/repo/blob/' + SHA + '/%50RIVATE', [], None]
        for key, values in (('origin', bad_origins), ('source_url', bad_sources),
                            ('source_sha', ['b' * 40, SHA + '\n', True, {}, None])):
            for value in values:
                with self.subTest(key=key, value=value):
                    invalid = {**REFERENCE, key: value}
                    self.assertEqual(public_domain_references([invalid]), [])
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            provider_context={'live_runtime_evidence': {'public_domain_references': [
                {**REFERENCE, 'origin': 'https://anime-sama.to?token=PRIVATE'}]}})
        payload = build_force_prompt_payload(request)
        self.assertNotIn('public_domain_references', payload)
        self.assertNotIn('PRIVATE', json.dumps(payload))

    def test_only_current_failed_404_evidence_prioritizes_provider_data(self):
        context = {'override': {'official_site': 'https://old-provider.org'},
                   'runtimeMutationSource': 'function lookup(){return [];}',
                   'runtime_template_prior': {'reuseBeforeNovelBloc': True},
                   'registered_patch_sources': {'provider.py': 'NIAKVIO_PROVIDER_RUNTIME_RESOLVER_V1'},
                   'live_runtime_evidence': evidence()}
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap', provider_context=context)
        order = production_scope_order(request)
        self.assertEqual(order[0], 'provider_data')
        self.assertIn('provider_bloc', order)
        self.assertTrue(domain_reference_focus(evidence()))
        for status in (403, 200, None, 500):
            request.provider_context['live_runtime_evidence'] = evidence(status)
            self.assertEqual(production_scope_order(request)[0], 'provider_bloc')
            self.assertFalse(domain_reference_focus(evidence(status)))
        request.provider_context['live_runtime_evidence'] = evidence()
        request.provider_context['live_runtime_evidence']['network_evidence'].append(
            {'fixture': 'JJK', 'host': 'old-provider.org', 'stage': 'content_lookup', 'status': 200})
        self.assertEqual(production_scope_order(request)[0], 'provider_bloc')
        request.provider_context['live_runtime_evidence'] = evidence()
        request.provider_context['live_runtime_evidence']['public_domain_references'] = []
        self.assertEqual(production_scope_order(request)[0], 'provider_bloc')
        request.provider_context['live_runtime_evidence'] = evidence()
        request.allowed_mutations = ['provider_bloc']
        self.assertEqual(production_scope_order(request), ['provider_bloc'])

    def test_player_or_media_404_cannot_reclassify_provider_domain(self):
        # Real-world TV failures can reach a reader/embed or media URL while
        # the upstream catalogue is healthy. A bare 404 is not domain proof.
        for stage in ('player', 'source', 'media', 'playback', 'unknown', ''):
            with self.subTest(stage=stage):
                live = evidence(404)
                live['network_evidence'][0]['stage'] = stage
                self.assertFalse(domain_reference_focus(live))
                request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
                    provider_context={'override': {'official_site': 'https://old-provider.org'},
                        'runtimeMutationSource': 'function lookup(){return [];}', 'live_runtime_evidence': live},
                    allowed_mutations=['provider_data', 'provider_bloc'])
                # The domain hypothesis may not preempt the parser/player
                # remediation just because a terminal 404 was observed.
                self.assertNotEqual(production_scope_order(request)[0], 'provider_data')
        live = evidence(404)
        live['network_evidence'].append({
            'fixture': 'JJK', 'host': 'reader.cdn.test',
            'stage': 'media', 'status': 404,
        })
        self.assertFalse(domain_reference_focus(live))
        live = evidence(404)
        live['fixture_evidence'].append({
            'fixture': 'Spartacus S00E01', 'category': 'tv',
            'streamsReturned': 0, 'streamsPlayable': 0,
        })
        self.assertFalse(domain_reference_focus(live))
        live['network_evidence'].append({
            'fixture': 'Spartacus S00E01', 'host': 'old-provider.org',
            'stage': 'episode', 'status': 404,
        })
        self.assertEqual(domain_reference_focus(live)['fixtures'],
                         ['JJK', 'Spartacus S00E01'])

    def test_domain_data_prompt_retains_relevant_maps_without_claiming_repair(self):
        override = {'notes': 'PRIVATE' * 1000,
                    'official_site': 'https://old-provider.org', 'official_hub': 'https://provider-hub.org',
                    'domain_substitutions': {'anime-sama.to': 'old-provider.org'},
                    'runtime_domain_replacements': {'anime-sama.to': 'old-provider.org'},
                    'manifest_overrides': {'name': 'Demo'}, 'api_recipe': {'private': 'PRIVATE'}}
        request = RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            provider_context={'override': override, 'live_runtime_evidence': evidence()},
            allowed_mutations=['provider_data'])
        before = copy.deepcopy(request.provider_context)
        payload = build_force_prompt_payload(request)
        self.assertEqual(request.provider_context, before)
        target = payload['mutation_target']
        self.assertEqual(target['scope'], 'provider_data')
        self.assertEqual(target['source']['official_site'], override['official_site'])
        self.assertEqual(target['source']['domain_substitutions'], override['domain_substitutions'])
        self.assertEqual(set(target['source']), {'official_site', 'official_hub', 'domain_substitutions',
                                               'runtime_domain_replacements', 'manifest_overrides'})
        self.assertEqual(payload['public_domain_references'], [REFERENCE])
        self.assertIn('unverified domain candidate', payload['domain_candidate_policy'])
        self.assertIn('external execution', payload['domain_candidate_policy'])
        self.assertNotIn('PRIVATE', json.dumps(payload))


if __name__ == '__main__':
    unittest.main()
