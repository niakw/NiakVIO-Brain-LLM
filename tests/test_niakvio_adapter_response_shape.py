import unittest

from niakvio_brain_llm.niakvio_adapter import _provider_sharded_observation, _provider_targeted_observation, _safe_response_shape


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

    def test_selector_names_are_exact_observed_ascii_strings(self):
        exact = "c" * 48
        shape = _safe_response_shape({
            "kind": "html",
            "forms": True,
            "classTokens": ["movie-card", exact, exact + "x", True, False, None, "épisode"],
            "idTokens": ["results", exact, exact + "x", True, None, "épisode"],
            "classFacts": [
                {"token": exact + "x", "count": 3},
                {"token": True, "count": 3},
                {"token": "épisode", "count": 3},
                {"token": "movie-card", "count": 3,
                 "tags": ["DIV", "a", "t" * 17, True, None, "élément"]},
            ],
        })
        self.assertEqual(shape["classTokens"], ["movie-card", exact])
        self.assertEqual(shape["idTokens"], ["results", exact])
        self.assertNotIn("forms", shape)
        self.assertEqual(shape["classFacts"], [{
            "token": "movie-card", "count": 3, "tags": ["div", "a"],
            "selfHref": 0, "nestedAnchors": 0, "signals": [],
        }])

    def test_malformed_fact_counters_do_not_abort_current_observations(self):
        for field in ("count", "selfHref", "nestedAnchors"):
            for invalid in ("not-a-count", "5", {}, [], True, 1.5, None):
                with self.subTest(field=field, invalid=invalid):
                    observation = _provider_targeted_observation({"providers": {"demo": {
                        "network": {"movie": [{"status": 200, "shape": {
                            "kind": "html", "classFacts": [
                                {"token": "invalid-card", field: invalid},
                                {"token": "movie-card", "count": 99, "selfHref": 99,
                                 "nestedAnchors": 99, "tags": ["a"]},
                            ],
                        }}]},
                    }}}, "demo")
                    facts = observation["network"]["movie"][0]["shape"]["classFacts"]
                    self.assertEqual([row["token"] for row in facts], ["movie-card"])
                    self.assertEqual((facts[0]["count"], facts[0]["selfHref"],
                                      facts[0]["nestedAnchors"]), (12, 12, 24))
                    self.assertNotIn("invalid-card", repr(observation))

    def test_imported_fact_does_not_fabricate_a_truncated_selector_hint(self):
        fabricated = "movie-card" + "x" * 38
        observation = _provider_sharded_observation({"rows": [{
            "provider_id": "demo", "semantic_type": "movie", "status": "no_streams",
            "debug_fetches": [{"url": "https://provider.invalid/", "status": 200,
                              "response_shape": {"kind": "html", "classFacts": [
                                  {"token": fabricated + "-suffix", "count": 4,
                                   "tags": ["div"], "nestedAnchors": 4},
                                  {"token": "movie-card", "count": 2, "tags": ["a"]},
                              ]}}],
        }]}, "demo")
        self.assertNotIn(fabricated, repr(observation))
        self.assertIn("classFacts=[movie-card;count=2;", observation["structureHints"][0])

    def test_malformed_tag_or_signal_containers_do_not_create_facts(self):
        for invalid in ("article", True, {"private": "value"}, 42):
            with self.subTest(invalid=invalid):
                shape = _safe_response_shape({"kind": "html", "classFacts": [{
                    "token": "movie-card", "count": 2, "tags": invalid, "signals": invalid,
                }]})
                self.assertEqual(shape["classFacts"][0]["tags"], [])
                self.assertEqual(shape["classFacts"][0]["signals"], [])


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



    def test_sharded_observation_surfaces_current_html_structure_hint(self):
        payload = {
            "rows": [{
                "provider_id": "demo",
                "semantic_type": "movie",
                "status": "no_streams",
                "debug_stage": "provider_network_zero_result",
                "playable": 0,
                "verified": 0,
                "contradictions": 0,
                "sample_titles": ["Demo Movie"],
                "debug_fetches": [{
                    "url": "https://provider.invalid/?s=demo&secret=redacted",
                    "response_url": "https://provider.invalid/?s=demo&secret=redacted",
                    "method": "GET",
                    "status": 200,
                    "response_shape": {
                        "kind": "html",
                        "classTokens": ["movie-card", "movie-card-title"],
                        "idTokens": ["search"],
                        "classFacts": [{
                            "token": "movie-card",
                            "count": 5,
                            "tags": ["a", "div"],
                            "selfHref": 1,
                            "nestedAnchors": 5,
                            "signals": ["movie", "year"],
                        }],
                        "markers": ["download"],
                    },
                }],
            }]
        }
        observation = _provider_sharded_observation(payload, "demo")
        self.assertEqual(observation["debugStages"]["movie"], "provider_network_zero_result")
        self.assertEqual(observation["network"]["movie"][0]["host"], "provider.invalid")
        self.assertEqual(observation["network"]["movie"][0]["path"], "/")
        self.assertNotIn("secret", repr(observation))
        self.assertIn("classFacts=[movie-card;count=5;selfHref=1;nestedAnchors=5;tags=a,div;signals=movie,year]", observation["structureHints"][0])


if __name__ == "__main__":
    unittest.main()
