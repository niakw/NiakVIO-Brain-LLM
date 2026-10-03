import io
import json
import unittest
from urllib.error import HTTPError

import niakvio_brain_llm.backend as backend_mod
from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class BackendSchemaFallbackTests(unittest.TestCase):
    def test_http_400_schema_retries_without_response_format(self):
        calls = []
        original = backend_mod.urlopen

        def fake_urlopen(request, timeout=0):
            body = json.loads(request.data.decode("utf-8"))
            calls.append(body)
            if len(calls) == 1:
                raise HTTPError(
                    request.full_url,
                    400,
                    "Bad Request",
                    {},
                    io.BytesIO(b'{"error":"schema unsupported"}'),
                )
            return _Response({
                "choices": [{"message": {"content": '{"ok":true}'}}],
            })

        backend_mod.urlopen = fake_urlopen
        try:
            backend = LocalOpenAICompatibleBackend()
            result = backend.complete(
                system="system",
                user="user",
                response_schema={"type": "object"},
            )
        finally:
            backend_mod.urlopen = original

        self.assertEqual(result, '{"ok":true}')
        self.assertEqual(len(calls), 2)
        self.assertIn("response_format", calls[0])
        self.assertNotIn("response_format", calls[1])
        self.assertTrue(calls[0].get("cache_prompt"))
        self.assertTrue(calls[1].get("cache_prompt"))

    def test_prefill_shares_one_backend_deadline_and_uses_cache(self):
        calls = []
        original = backend_mod.urlopen

        def fake_urlopen(request, timeout=0):
            body = json.loads(request.data.decode("utf-8"))
            calls.append((body, timeout))
            return _Response({
                "choices": [{"message": {"content": '{"ok":true}'}}],
            })

        backend_mod.urlopen = fake_urlopen
        try:
            backend = LocalOpenAICompatibleBackend(
                timeout_seconds=30,
                max_tokens=512,
                prefill_prompt=True,
            )
            result = backend.complete(
                system="system",
                user="user",
                response_schema={"type": "object"},
            )
        finally:
            backend_mod.urlopen = original

        self.assertEqual(result, '{"ok":true}')
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0]["max_tokens"], 1)
        self.assertNotIn("response_format", calls[0][0])
        self.assertTrue(calls[0][0].get("cache_prompt"))
        self.assertEqual(calls[1][0]["max_tokens"], 512)
        self.assertIn("response_format", calls[1][0])
        self.assertTrue(calls[1][0].get("cache_prompt"))
        self.assertLessEqual(calls[1][1], calls[0][1])

    def test_length_finish_reason_is_rejected(self):
        original = backend_mod.urlopen

        def fake_urlopen(request, timeout=0):
            return _Response({
                "choices": [{
                    "finish_reason": "length",
                    "message": {"content": '{"provider_id":"coflix",'}
                }],
            })

        backend_mod.urlopen = fake_urlopen
        try:
            backend = LocalOpenAICompatibleBackend(max_tokens=160)
            with self.assertRaisesRegex(RuntimeError, "completion truncated by max_tokens"):
                backend.complete(
                    system="system",
                    user="user",
                    response_schema={"type": "object"},
                )
        finally:
            backend_mod.urlopen = original

    def test_non_400_is_not_retried(self):
        calls = []
        original = backend_mod.urlopen

        def fake_urlopen(request, timeout=0):
            calls.append(1)
            raise HTTPError(
                request.full_url,
                500,
                "Server Error",
                {},
                io.BytesIO(b'{"error":"server"}'),
            )

        backend_mod.urlopen = fake_urlopen
        try:
            backend = LocalOpenAICompatibleBackend()
            with self.assertRaises(HTTPError):
                backend.complete(
                    system="system",
                    user="user",
                    response_schema={"type": "object"},
                )
        finally:
            backend_mod.urlopen = original

        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
