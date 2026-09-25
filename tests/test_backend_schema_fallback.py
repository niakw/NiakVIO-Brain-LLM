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
