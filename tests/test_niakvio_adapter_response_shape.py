import unittest

from niakvio_brain_llm.niakvio_adapter import _safe_response_shape


class ResponseShapeAdapterTests(unittest.TestCase):
    def test_html_structural_tokens_are_bounded_and_filtered(self):
        shape = _safe_response_shape({
            "kind": "html",
            "sampleBytes": 12000,
            "anchors": 30,
            "classTokens": ["movie-card", "episode_row", "bad token", "1bad", "x", "A" * 60],
            "idTokens": ["results", "download-list", "bad token", "2bad"],
            "markers": ["download", "episode", "forbidden"],
        })
        self.assertEqual(shape["classTokens"], ["movie-card", "episode_row"])
        self.assertEqual(shape["idTokens"], ["results", "download-list"])
        self.assertEqual(shape["markers"], ["download", "episode"])
        self.assertNotIn("bad token", repr(shape))
        self.assertNotIn("forbidden", repr(shape))


if __name__ == "__main__":
    unittest.main()
