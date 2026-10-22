from __future__ import annotations

import json
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
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

    def test_niakvio_environment_key_and_hosted_default_ignore_local_model(self):
        with patch.dict("os.environ", {
            "NIAKVIO_OPENAI_API_KEY": "test-niakvio-only",
            "OPENAI_API_KEY": "test-other-key",
            "NIAKVIO_LLM_MODEL": "qwen-local-only",
        }, clear=True):
            model = HostedResponsesBackend.from_environment()
        self.assertEqual(model.api_key, "test-niakvio-only")
        self.assertEqual(model.model, "gpt-6.1-sol")
        self.assertNotIn("test-niakvio-only", repr(model))

    def test_hosted_environment_override_and_generic_key_fallback(self):
        with patch.dict("os.environ", {
            "OPENAI_API_KEY": "test-generic-only",
            "NIAKVIO_HOSTED_MODEL": "gpt-6-astra",
        }, clear=True):
            model = HostedResponsesBackend.from_environment(max_tokens=4096)
            explicit = HostedResponsesBackend.from_environment(model="gpt-6.1-sol")
        self.assertEqual(model.api_key, "test-generic-only")
        self.assertEqual(model.model, "gpt-6-astra")
        self.assertEqual(model.max_tokens, 4096)
        self.assertEqual(explicit.model, "gpt-6.1-sol")

    def test_environment_missing_key_has_no_request(self):
        with patch.dict("os.environ", {}, clear=True), patch("niakvio_brain_llm.backend.urlopen") as send:
            with self.assertRaisesRegex(RuntimeError, "NIAKVIO_OPENAI_API_KEY or OPENAI_API_KEY"):
                HostedResponsesBackend.from_environment()
            send.assert_not_called()

    def test_hosted_cli_uses_niakvio_environment_without_model_argument(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "plan_batch_from_checkout.py"
        spec = importlib.util.spec_from_file_location("hosted_batch_cli", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "automation").mkdir()
            (root / "automation" / "provider-census-status.json").write_text('{"providers":[]}', encoding="utf-8")
            argv = [str(script), "--niakvio-root", str(root), "--experience", str(root / "experience.jsonl"),
                    "--documents", str(root / "documents.jsonl"), "--output", str(root / "out.jsonl"),
                    "--backend", "hosted"]
            with patch.dict("os.environ", {"NIAKVIO_OPENAI_API_KEY": "test-cli-only"}, clear=True), \
                    patch.object(sys, "argv", argv), \
                    patch.object(HostedResponsesBackend, "from_environment", wraps=HostedResponsesBackend.from_environment) as factory, \
                    patch("niakvio_brain_llm.backend.urlopen") as send, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 0)
            factory.assert_called_once_with(model=None, timeout_seconds=90, max_tokens=768)
            send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
