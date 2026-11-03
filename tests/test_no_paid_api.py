import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from niakvio_brain_llm.backend import HostedResponsesBackend, LocalOpenAICompatibleBackend


class NoPaidApiTests(unittest.TestCase):
    def test_workflows_cannot_bypass_backend_billing_guard(self):
        root = Path(__file__).resolve().parents[1]
        for workflow in (root / '.github/workflows').glob('*.yml'):
            text = workflow.read_text(encoding='utf-8')
            with self.subTest(workflow=workflow.name):
                self.assertNotIn('api.openai.com', text)
                self.assertNotRegex(text, r'secrets\.(?:NIAKVIO_)?OPENAI_API_KEY')
                self.assertNotRegex(text, r'NIAKVIO_ALLOW_PAID_API:\s*[\"\x27]?1')
        disabled = (root / '.github/workflows/hosted-api-check.yml').read_text(encoding='utf-8')
        self.assertIn('if: ${{ false }}', disabled)

    def test_key_presence_cannot_enable_paid_requests(self):
        for setting in (None, '', '0', 'true'):
            env = {'NIAKVIO_OPENAI_API_KEY': 'test-only'}
            if setting is not None:
                env['NIAKVIO_ALLOW_PAID_API'] = setting
            with patch.dict('os.environ', env, clear=True), patch('niakvio_brain_llm.backend.urlopen') as send:
                with self.assertRaisesRegex(RuntimeError, 'paid model API is disabled'):
                    HostedResponsesBackend.from_environment()
                with self.assertRaisesRegex(RuntimeError, 'paid model API is disabled'):
                    HostedResponsesBackend(api_key='test-only').complete(system='s', user='u')
                send.assert_not_called()

    def test_local_mode_cannot_be_pointed_at_a_paid_remote_endpoint(self):
        for origin in ('https://api.openai.com', 'https://api.example.org',
                       'http://localhost.evil.org:8080', 'http://key@127.0.0.1:8080'):
            with patch('niakvio_brain_llm.backend.urlopen') as send:
                with self.assertRaisesRegex(ValueError, 'loopback endpoint'):
                    LocalOpenAICompatibleBackend(base_url=origin).complete(system='s', user='u')
                send.assert_not_called()

    def test_unavailable_local_model_never_falls_back_to_hosted(self):
        with patch('niakvio_brain_llm.backend.urlopen', side_effect=URLError('local unavailable')) as send, \
                patch.object(HostedResponsesBackend, 'complete') as paid:
            with self.assertRaises(URLError):
                LocalOpenAICompatibleBackend().complete(system='s', user='u')
            self.assertEqual(send.call_count, 1)
            paid.assert_not_called()


if __name__ == '__main__':
    unittest.main()
