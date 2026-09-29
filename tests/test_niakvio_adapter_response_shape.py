import unittest

from niakvio_brain_llm.niakvio_adapter import _provider_targeted_observation, _safe_response_shape


class ResponseShapeAdapterTests(unittest.TestCase):
    def test_html_structural_tokens_are_bounded_and_filtered(self):
        shape = _safe_response_shape({
            "kind": "html",
            "sampleBytes": 12000,
            "anchors": 30,
            "classTokens": ["movie-card", "episode_row", "bad token", "1bad", "x", "A" * 60],
            "idTokens": ["results", "download-list", "bad token", "2bad"],
            "classFacts": [
                {"token": "movie-card", "count": 4, "tags": ["div"], "selfHref": 0, "nestedAnchors": 4, "signals": ["movie", "year", "forbidden"]},
                {"token": "bad token", "count": 99, "tags": ["script"], "selfHref": 99, "nestedAnchors": 99, "signals": ["download"]},
            ],
            "markers": ["download", "episode", "forbidden"],
        })
        self.assertEqual(shape["classTokens"], ["movie-card", "episode_row"])
        self.assertEqual(shape["idTokens"], ["results", "download-list"])
        self.assertEqual(shape["markers"], ["download", "episode"])
        self.assertEqual(shape["classFacts"], [{
            "token": "movie-card",
            "count": 4,
            "tags": ["div"],
            "selfHref": 0,
            "nestedAnchors": 4,
            "signals": ["movie", "year"],
        }])
        self.assertNotIn("bad token", repr(shape))
        self.assertNotIn("forbidden", repr(shape))


    def test_targeted_observation_surfaces_shallow_html_structure_hint(self):
        payload = {
            "providers": {
                "demo": {
                    "debugStages": {"movie": "provider_network_zero_result"},
                    "statuses": {"movie": "no_streams"},
                    "network": {
                        "movie": [
                            {
                                "method": "GET",
                                "host": "provider.invalid",
                                "path": "/",
                                "status": 200,
                                "shape": {
                                    "kind": "html",
                                    "classTokens": ["movie-card", "movie-card-title", "movie-card-meta"],
                                    "idTokens": ["search", "results"],
                                    "classFacts": [
                                        {"token": "movie-card", "count": 5, "tags": ["div"], "selfHref": 0, "nestedAnchors": 5, "signals": ["movie", "year"]}
                                    ],
                                    "markers": ["download", "episode"],
                                },
                            }
                        ]
                    },
                }
            }
        }
        observation = _provider_targeted_observation(payload, "demo")
        self.assertEqual(len(observation["structureHints"]), 1)
        hint = observation["structureHints"][0]
        self.assertIn("movie:classes=movie-card,movie-card-title,movie-card-meta", hint)
        self.assertIn("ids=search,results", hint)
        self.assertIn("markers=download,episode", hint)
        self.assertIn("classFacts=[movie-card;count=5;selfHref=0;nestedAnchors=5;tags=div;signals=movie,year]", hint)



if __name__ == "__main__":
    unittest.main()
