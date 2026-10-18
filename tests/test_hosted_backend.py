from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from niakvio_brain_llm.backend import HostedResponsesBackend


class Response:
    def __init__(self, payload: dict) -> None:
        self.data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def read(self):
        return self.data


class HostedBackendTests(unittest.TestCase):
    def test_explicit_schema_and_no_retention_or_tools(self):
        captured = {}

        def send(request, *, timeout):
            captured["url"] = request.full_url
            captured["auth"] = request.get_header("Authorization")
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return Response({
                "status": "completed",
                "output": [
                    {"type": "reasoning", "summary": []},
                    {"type": "message", "content": [{"type": "output_text", "text": '{"mutations":[]}'}]},
                ],
            })

        model = HostedResponsesBackend(api_key="test-only", model="gpt-6.1-sol", max_tokens=320)
        with patch("niakvio_brain_llm.backend.urlopen", side_effect=send):
            content = model.complete(system="system", user="public fixture", response_schema={"type": "object"})
        self.assertEqual(content, '{"mutations":[]}')
        self.assertEqual(captured["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(captured["auth"], "Bearer test-only")
        body = captured["payload"]
        self.assertFalse(body["store"])
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        self.assertEqual(body["model"], "gpt-6.1-sol")
        self.assertEqual(body["max_output_tokens"], 1024)
        self.assertNotIn("cache_prompt", body)
        self.assertNotIn("tools", body)

    def test_http_failure_is_redacted(self):
        model = HostedResponsesBackend(api_key="do-not-log-secret")
        with patch("niakvio_brain_llm.backend.urlopen", side_effect=HTTPError(
            "https://api.openai.com/v1/responses", 401, "fake secret diagnostic", None, None
        )):
            with self.assertRaisesRegex(RuntimeError, "hosted model HTTP 401") as ctx:
                model.complete(system="s", user="u")
        self.assertNotIn("do-not-log-secret", str(ctx.exception))

    def test_no_key_no_call(self):
        model = HostedResponsesBackend(api_key="")
        with patch("niakvio_brain_llm.backend.urlopen") as send:
            with self.assertRaisesRegex(RuntimeError, "requires an API key"):
                model.complete(system="s", user="u")
            send.assert_not_called()

    def test_incomplete_and_empty_fail_closed(self):
        model = HostedResponsesBackend(api_key="test-only")
        for response in ({"status": "incomplete", "output": []}, {"status": "completed", "output": []}):
            with self.subTest(response=response):
                with patch("niakvio_brain_llm.backend.urlopen", return_value=Response(response)):
                    with self.assertRaises(RuntimeError):
                        model.complete(system="s", user="u")

    def test_unapproved_model_refused(self):
        model = HostedResponsesBackend(api_key="test-only", model="unverified-model")
        with self.assertRaisesRegex(ValueError, "unapproved hosted model"):
            model.complete(system="s", user="u")


if __name__ == "__main__":
    unittest.main()
