import copy
import json
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.live_evidence import apply_verified_live_failure, verified_live_failure
from niakvio_brain_llm.orchestrator import BrainOrchestrator
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.policy import build_mutation_policy
from niakvio_brain_llm.priors import build_causal_prior


SHA = 'a' * 40


class CountingBackend:
    def __init__(self):
        self.prompts = []

    def complete(self, **kwargs):
        self.prompts.append(json.loads(kwargs['user']))
        return json.dumps({'edit': None, 'abstain_reason': 'Test backend does not claim a repair.'})


def request():
    return RepairRequest(provider_id='demo', status='FULL OK', failure_class='route_proven_gap',
        census_prior={'status': 'FULL OK', 'repairEligible': False},
        allowed_mutations=['provider_data'], provider_context={'override': {'official_site': 'https://old-provider.org'}},
        observations=[{'source': 'census_current', 'value': {'status': 'FULL OK', 'testedThisRun': False}}])


def preflight():
    return {'provider': 'demo', 'sourceSha': SHA,
            'fixture_evidence': [{'fixture': 'JJK S01E01', 'streamsReturned': 0, 'streamsPlayable': 0}],
            'network_evidence': [{'fixture': 'JJK S01E01', 'host': 'old-provider.org',
                                  'stage': 'content_lookup', 'status': 404}]}


class LivePreflightPolicyTests(unittest.TestCase):
    def test_stale_full_ok_current_404_reaches_real_policy_and_backend_once(self):
        old = request()
        prior = copy.deepcopy(old.census_prior)
        backend = CountingBackend()
        orchestrator = BrainOrchestrator(BrainPlanner(backend))
        before = orchestrator.run(old, compact_force=True)
        self.assertEqual(before.routing.mode, 'probe')
        self.assertEqual(backend.prompts, [])
        current = preflight()
        unchanged = copy.deepcopy(current)
        self.assertTrue(apply_verified_live_failure(old, current, SHA, ['demo']))
        self.assertEqual(current, unchanged)
        self.assertEqual(old.census_prior, prior)
        self.assertEqual(old.status, 'CURRENT FAILURE')
        self.assertEqual(old.failure_class, 'provider_transport_gap')
        self.assertTrue(verified_live_failure(old))
        policy = build_mutation_policy(old, build_causal_prior(old, []))
        self.assertFalse(policy['force_abstain'])
        self.assertEqual(policy['allowed_scopes'], ['provider_data'])
        outcome = orchestrator.run(old, compact_force=True)
        self.assertEqual(outcome.routing.mode, 'llm_repair')
        self.assertEqual(len(backend.prompts), 1)
        self.assertTrue(outcome.proposal.abstain)
        self.assertEqual(outcome.proposal.mutations, [])
        trace = old.observations[0]
        self.assertEqual(trace['source'], 'verified-live-preflight')
        self.assertEqual(trace['value']['historicalStatus'], 'FULL OK')
        self.assertEqual(trace['value']['sourceSha'], SHA)
        self.assertFalse(trace['value']['publicationAuthority'])

    def test_positive_missing_incoherent_and_unrelated_evidence_never_bypass_policy(self):
        variants = []
        for key, value in [('provider', 'other'), ('sourceSha', 'b' * 40)]:
            value_live = preflight(); value_live[key] = value; variants.append(value_live)
        for field, value in [('streamsReturned', None), ('streamsPlayable', None),
                             ('streamsReturned', True), ('streamsPlayable', False),
                             ('streamsReturned', -1), ('fixture', ''), ('fixture', 'JJK\n')]:
            value_live = preflight(); value_live['fixture_evidence'][0][field] = value; variants.append(value_live)
        for fixture in ({'fixture': 'JJK S01E01'},
                        {'fixture': 'JJK S01E01', 'streamsReturned': 1, 'streamsPlayable': 1},
                        {'fixture': 'JJK S01E01', 'streamsReturned': 0, 'streamsPlayable': 1},
                        {'fixture': 'JJK S01E01', 'streamsReturned': 0, 'streamsPlayable': 0, 'decodedMediaControls': 1}):
            value_live = preflight(); value_live['fixture_evidence'] = [fixture]; variants.append(value_live)
        for status in (None, 200, 403, True):
            value_live = preflight(); value_live['network_evidence'][0]['status'] = status; variants.append(value_live)
        value_live = preflight(); value_live['network_evidence'][0]['infrastructure'] = True; variants.append(value_live)
        value_live = preflight(); value_live['network_evidence'][0]['fixture'] = 'Other'; variants.append(value_live)
        value_live = preflight(); value_live['fixture_evidence'] *= 2; variants.append(value_live)
        variants += [{}, None]
        for live in variants:
            with self.subTest(live=live):
                old = request(); unchanged = copy.deepcopy(old.to_dict())
                self.assertFalse(apply_verified_live_failure(old, live, SHA, ['demo']))
                self.assertEqual(old.to_dict(), unchanged)
                backend = CountingBackend()
                result = BrainOrchestrator(BrainPlanner(backend)).run(old, compact_force=True)
                self.assertEqual(result.routing.mode, 'probe')
                self.assertEqual(backend.prompts, [])
        for explicit in ([], ['other']):
            self.assertFalse(apply_verified_live_failure(request(), preflight(), SHA, explicit))
        self.assertFalse(apply_verified_live_failure(request(), preflight(), 'b' * 40, ['demo']))

    def test_each_failed_fixture_requires_its_own_404_and_existing_context_is_still_required(self):
        live = preflight()
        live['fixture_evidence'].append({'fixture': 'Hell S01E01', 'streamsReturned': 0, 'streamsPlayable': 0})
        self.assertFalse(apply_verified_live_failure(request(), live, SHA, ['demo']))
        live['network_evidence'].append({'fixture': 'Hell S01E01', 'stage': 'search', 'status': 404})
        old = request(); old.provider_context = {}
        self.assertTrue(apply_verified_live_failure(old, live, SHA, ['demo']))
        policy = build_mutation_policy(old, build_causal_prior(old, []))
        self.assertTrue(policy['force_abstain'])
        self.assertEqual(policy['reason'], 'no provider-local patch context is available')


if __name__ == '__main__':
    unittest.main()
