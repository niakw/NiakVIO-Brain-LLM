import json
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from niakvio_brain_llm.backend import HostedResponsesBackend
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.mutation_guard import validate_mutation
from niakvio_brain_llm.planner import _compact_wire_schema_for
from niakvio_brain_llm.schema import hosted_wire_schema


class Response:
    def __init__(self, edit):
        self.content = json.dumps({'edit': edit, 'abstain_reason': ''})

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({'status': 'completed', 'output': [{'type': 'message',
            'content': [{'type': 'output_text', 'text': self.content}]}]}).encode()


class HostedDataWireTests(unittest.TestCase):
    def setUp(self):
        self.schema = _compact_wire_schema_for(RepairRequest(provider_id='demo', failure_class='domain_gap'),
                                               {'allowed_scopes': ['provider_data']})

    def complete(self, edit):
        with patch('niakvio_brain_llm.backend.urlopen', return_value=Response(edit)):
            return json.loads(HostedResponsesBackend(api_key='test-only').complete(
                system='Public diagnostic only.', user='JSON fixture.', response_schema=self.schema))

    def test_actual_compact_schema_is_api_strict_without_changing_local_schema(self):
        before = json.dumps(self.schema, sort_keys=True)
        captured = {}
        def send(request, *, timeout):
            captured.update(json.loads(request.data))
            return Response({'scope': 'provider_data', 'operation': 'set',
                'path': 'official_site', 'value_json': json.dumps('https://anime-sama.fr')})
        with patch('niakvio_brain_llm.backend.urlopen', side_effect=send):
            value = json.loads(HostedResponsesBackend(api_key='test-only').complete(
                system='Public diagnostic.', user='JSON fixture.', response_schema=self.schema))
        variant = captured['text']['format']['schema']['properties']['edit']['anyOf'][0]
        self.assertEqual(set(variant['required']), set(variant['properties']))
        self.assertEqual(variant['properties']['value_json']['type'], 'string')
        self.assertNotIn('value', variant['properties'])
        self.assertTrue(captured['text']['format']['strict'])
        self.assertFalse(captured['store'])
        self.assertIn('value_json', captured['instructions'])
        self.assertEqual(json.dumps(self.schema, sort_keys=True), before)
        self.assertEqual(value['edit']['value'], 'https://anime-sama.fr')
        self.assertNotIn('value_json', value['edit'])
        validate_mutation('demo', value['edit'])

    def test_arbitrary_json_value_roundtrips_without_interpreting_nested_data(self):
        for value in ('text', ['a', {'b': 2}], {'scope': 'provider_data', 'mode': True},
                      7, 2.5, True, None):
            with self.subTest(kind=type(value).__name__):
                result = self.complete({'scope': 'provider_data', 'operation': 'set',
                    'path': 'notes.transport_probe', 'value_json': json.dumps(value)})
                self.assertEqual(result['edit']['value'], value)
                validate_mutation('demo', result['edit'])
        result = self.complete({'scope': 'provider_data', 'operation': 'delete',
            'path': 'notes.transport_probe', 'value_json': 'null'})
        self.assertNotIn('value', result['edit'])
        validate_mutation('demo', result['edit'])
        self.assertIsNone(self.complete(None)['edit'])

    def test_malformed_or_non_json_encoding_fails_without_echoing_payload(self):
        base = {'scope': 'provider_data', 'operation': 'set', 'path': 'notes.transport_probe'}
        bad_values = ({}, {'value_json': 'PRIVATE_INVALID'}, {'value_json': 'NaN'},
                      {'value_json': 'Infinity'}, {'value_json': 1},
                      {'value_json': 'null', 'value': 'PRIVATE_AMBIGUOUS'},
                      {'value_json': '"' + 'x' * 24000 + '"'},
                      {'operation': 'delete', 'value_json': 'false'})
        for bad in bad_values:
            with self.subTest(keys=list(bad)):
                with self.assertRaisesRegex(RuntimeError, 'invalid DATA value encoding') as error:
                    self.complete({**base, **bad})
                self.assertNotIn('PRIVATE', str(error.exception))

    def test_restoration_does_not_bypass_existing_mutation_receiver_guards(self):
        result = self.complete({'scope': 'provider_data', 'operation': 'set',
            'path': 'official_site', 'value_json': json.dumps('https://example.com')})
        with self.assertRaises(ValueError):
            validate_mutation('demo', result['edit'])
        result = self.complete({'scope': 'provider_data', 'operation': 'set',
            'path': '../../Core', 'value_json': 'true'})
        with self.assertRaises(ValueError):
            validate_mutation('demo', result['edit'])

    def test_no_data_transport_adaptation_for_other_scope(self):
        schema = {'type': 'object', 'properties': {'scope': {'const': 'provider_bloc'},
            'value': {}}, 'additionalProperties': False}
        adapted, enabled = hosted_wire_schema(schema)
        self.assertFalse(enabled)
        self.assertEqual(adapted, schema)

    def test_http_schema_diagnostic_exposes_only_fixed_codes_and_parameters(self):
        error = {'error': {'code': 'invalid_json_schema', 'param': 'text.format.schema',
                          'message': 'PRIVATE_PROMPT_HEADER_BODY'}}
        failure = HTTPError('https://api.openai.com/v1/responses', 400, 'private', {},
                            io.BytesIO(json.dumps(error).encode()))
        with patch('niakvio_brain_llm.backend.urlopen', side_effect=failure) as send:
            with self.assertRaises(RuntimeError) as caught:
                HostedResponsesBackend(api_key='PRIVATE_KEY').complete(system='s', user='u')
        self.assertEqual(str(caught.exception),
            'hosted model HTTP 400 code=invalid_json_schema param=text.format.schema')
        self.assertEqual(send.call_count, 1)
        self.assertNotIn('PRIVATE', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
