import json
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.live_evidence import response_structure, network_evidence
from niakvio_brain_llm.prompting import build_force_prompt_payload


class InlineResponseShapeTests(unittest.TestCase):
    def test_shape_only_inline_fields_and_scripts_are_bounded_private_and_idempotent(self):
        shape = {'kind': 'html', 'inline_fields': [
            {'name': 'epoch', 'type': 'number', 'key_syntax': 'bare', 'value': 'PRIVATE_NUMBER'},
            {'name': 'partB', 'type': 'string', 'key_syntax': 'quoted', 'value': 'PRIVATE_STRING'},
            {'name': 'apiKey', 'type': 'string', 'key_syntax': 'quoted', 'value': 'PRIVATE_KEY'}],
            'script_resources': [{'kind': 'root_relative_url', 'role': 'app_entry',
                'location': 'inline_import', 'url': '/app/PRIVATE.js', 'body': 'PRIVATE_BODY'}]}
        clean = response_structure(shape)
        self.assertEqual(clean['inline_fields'], [
            {'name': 'epoch', 'type': 'number', 'key_syntax': 'bare'},
            {'name': 'partB', 'type': 'string', 'key_syntax': 'quoted'}])
        self.assertEqual(clean['script_resources'], [
            {'kind': 'root_relative_url', 'role': 'app_entry', 'location': 'inline_import'}])
        self.assertEqual(response_structure(clean), clean)
        self.assertNotIn('PRIVATE', json.dumps(clean))
        bounded = response_structure({'kind': 'html', 'inline_fields': shape['inline_fields'][:1] * 20,
                                      'script_resources': shape['script_resources'] * 20})
        self.assertEqual(len(bounded['inline_fields']), 12)
        self.assertEqual(len(bounded['script_resources']), 8)
        invalid = response_structure({'kind': 'html', 'inline_fields': [
            {'name': 'x' * 49, 'type': 'string', 'key_syntax': 'bare'},
            {'name': 'epoch', 'type': ['number'], 'key_syntax': 'bare'},
            {'name': 'epoch', 'type': 'number', 'key_syntax': 'PRIVATE'}],
            'script_resources': [{'kind': [], 'role': 'app_entry', 'location': 'inline_import'},
                                 {'kind': 'absolute_url', 'role': 'PRIVATE', 'location': 'src_attribute'}]})
        self.assertEqual(invalid['inline_fields'], [])
        self.assertEqual(invalid['script_resources'], [])
        self.assertEqual(response_structure(invalid), invalid)

    def test_diagnostics_reach_both_prompt_channels_without_resource_addresses(self):
        event = {'fixture': 'JJK', 'host': 'provider.org', 'stage': 'search', 'status': 200,
            'response_structure': {'kind': 'html', 'inline_fields': [
                {'name': 'partB', 'type': 'string', 'key_syntax': 'bare', 'value': 'PRIVATE_VALUE'}],
                'script_resources': [{'kind': 'relative_path', 'role': 'chunk',
                    'location': 'src_attribute', 'url': 'PRIVATE_URL'}]}}
        live = {'network_evidence': [event], 'previous_verification': {'candidate_network': [event]}}
        payload = build_force_prompt_payload(RepairRequest(provider_id='demo', failure_class='chain_terminal_gap',
            provider_context={'live_runtime_evidence': live}))
        for channel in (payload['current_network_evidence'], payload['previous_verification']['candidate_network']):
            self.assertEqual(channel[0]['response_structure']['inline_fields'][0]['key_syntax'], 'bare')
            self.assertEqual(channel[0]['response_structure']['script_resources'][0]['kind'], 'relative_path')
            self.assertEqual(network_evidence(channel), channel)
        self.assertNotIn('PRIVATE', json.dumps(payload))


if __name__ == '__main__':
    unittest.main()
