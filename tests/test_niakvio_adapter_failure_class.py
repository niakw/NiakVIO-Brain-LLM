import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.niakvio_adapter import classify_census_failure, request_from_checkout

class AdapterFailureClassTests(unittest.TestCase):
    def test_current_structure_evidence_reaches_brain_as_observation_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "run-structure",
                    "providers": [{
                        "provider": "demo",
                        "status": "FULL OK",
                        "dominantIssue": "none",
                        "declaredLanes": ["movie"],
                    }],
                }),
                encoding="utf-8",
            )
            (root / "automation" / "provider-current-structure-evidence.json").write_text(
                json.dumps({
                    "schemaVersion": 1,
                    "providers": {
                        "demo": {
                            "sourceKind": "user-current-page",
                            "observedAt": "2026-10-01",
                            "originHost": "demo.example",
                            "routes": [
                                {"path": "/wp-json/demo/v1/resolve", "method": "POST", "role": "player-resolver"},
                                {"path": "https://must-not-pass.example/unsafe", "method": "GET"},
                            ],
                            "requestKeys": ["tmdb", "type", "year", "pid", "bad key"],
                            "fanout": {
                                "groupCount": 2,
                                "groupVariantCounts": [10, 9],
                                "indexedVariantCount": 19,
                                "qualityHeights": [1080, 480, 2160, 720, 0, 99999],
                                "languageLabels": ["VF", "VOSTFR", "bad label"],
                            },
                        }
                    },
                }),
                encoding="utf-8",
            )
            (root / "provider-overrides.json").write_text(
                json.dumps({"provider_patches": {}}),
                encoding="utf-8",
            )
            (root / "provider-hubs.json").write_text("{}", encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"scrapers": []}), encoding="utf-8")

            request = request_from_checkout(root, "demo")
            by_source = {row["source"]: row["value"] for row in request.observations}
            observed = by_source["current-provider-structure"]
            self.assertFalse(observed["proofAuthority"])
            self.assertFalse(observed["executionAuthority"])
            self.assertEqual(observed["originHost"], "demo.example")
            self.assertEqual(observed["routes"], [{
                "path": "/wp-json/demo/v1/resolve",
                "method": "POST",
                "role": "player-resolver",
            }])
            self.assertEqual(observed["requestKeys"], ["tmdb", "type", "year", "pid"])
            self.assertEqual(observed["fanout"]["groupVariantCounts"], [10, 9])
            self.assertEqual(observed["fanout"]["indexedVariantCount"], 19)
            self.assertEqual(observed["fanout"]["qualityHeights"], [480, 720, 1080, 2160])
            self.assertEqual(observed["fanout"]["languageLabels"], ["VF", "VOSTFR"])
            self.assertEqual(
                request.provider_context["route_contract"]["currentObservedRoutes"],
                ["/wp-json/demo/v1/resolve"],
            )
            self.assertEqual(
                request.provider_context["route_contract"]["currentObservedRoutesAuthority"],
                "observation-only",
            )

    def test_full_ok_high_runtime_variant_coverage_becomes_explicit_provider_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "scripts" / "provider_patches").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "run-coverage",
                    "providers": [{
                        "provider": "demo",
                        "status": "FULL OK",
                        "dominantIssue": "none",
                        "declaredLanes": ["movie"],
                    }],
                }),
                encoding="utf-8",
            )
            (root / "scripts" / "provider_patches" / "demo_runtime_v1.py").write_text(
                'MANAGED_FIX_ID = "PROVIDER.DEMO.RUNTIME.V1"\n'
                'WRAPPER = r"""function quality(x){return /(2160|1080|720|480)p/.test(x)} '
                'async function resolve(links){var out=[];for(var i=0;i<links.length;i++){'
                'var rows=source(links[i]);for(var j=0;j<rows.length;j++)out.push(rows[j]);'
                'if(out.length>=4)break}return out}"""\n',
                encoding="utf-8",
            )
            (root / "provider-overrides.json").write_text(
                json.dumps({
                    "provider_patches": {
                        "demo": {
                            "provider_lego_scripts": [
                                "scripts/provider_patches/demo_runtime_v1.py"
                            ]
                        }
                    }
                }),
                encoding="utf-8",
            )
            (root / "provider-hubs.json").write_text("{}", encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"scrapers": []}), encoding="utf-8")
            request = request_from_checkout(root, "demo")
            self.assertEqual(request.failure_class, "variant_coverage_gap")
            self.assertEqual(request.provider_context["runtime_variant_coverage"]["risk"], "high")
            by_source = {row["source"]: row["value"] for row in request.observations}
            self.assertEqual(by_source["runtime-variant-coverage-current"]["risk"], "high")

    def test_full_ok_dynamic_multi_player_subset_becomes_variant_coverage_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "12345",
                    "providers": [{
                        "provider": "demo",
                        "status": "FULL OK",
                        "dominantIssue": "none",
                        "declaredLanes": ["movie"],
                    }],
                }),
                encoding="utf-8",
            )
            (root / "automation" / "provider-census-sharded-12345.json").write_text(
                json.dumps({
                    "rows": [{
                        "provider_id": "demo",
                        "semantic_type": "movie",
                        "status": "playable_verified",
                        "debug_stage": "provider_returned_streams",
                        "raw": 8,
                        "playable": 8,
                        "verified": 8,
                        "contradictions": 0,
                        "announced_player_candidates": 2,
                        "announced_variant_candidates": 19,
                        "announced_player_hosts": ["player-a.test", "player-b.test"],
                        "announced_quality_heights": [480, 720, 1080],
                        "explored_player_requests": 2,
                        "explored_player_hosts": ["player-a.test", "player-b.test"],
                        "variant_fanout_state": "returned-subset",
                        "fanout_fixture_title": "Representative",
                        "debug_fetches": [],
                    }],
                }),
                encoding="utf-8",
            )
            (root / "provider-overrides.json").write_text("{}", encoding="utf-8")
            (root / "provider-hubs.json").write_text("{}", encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"scrapers": []}), encoding="utf-8")

            request = request_from_checkout(root, "demo")
            self.assertEqual(request.failure_class, "variant_coverage_gap")
            by_source = {row["source"]: row["value"] for row in request.observations}
            fanout = by_source["census-sharded-current"]["fanout"]["movie"]
            self.assertEqual(fanout["announcedPlayerCandidates"], 2)
            self.assertEqual(fanout["announcedVariantCandidates"], 19)
            self.assertEqual(fanout["streamsReturned"], 8)
            self.assertEqual(fanout["exploredPlayerRequests"], 2)
            self.assertEqual(fanout["state"], "returned-subset")

    def test_chain_reached_beats_generic_zero_issue(self):
        row = {
            "status": "CHAIN REACHED",
            "dominantIssue": "provider_network_zero_result",
            "evidenceDepth": ["anime=chain_reached"],
        }
        self.assertEqual(classify_census_failure(row), "chain_terminal_gap")

    def test_route_proven_beats_generic_zero_issue(self):
        row = {
            "status": "ROUTE PROVEN",
            "dominantIssue": "provider_network_zero_result",
            "routeProof": ["1 live route"],
        }
        self.assertEqual(classify_census_failure(row), "route_proven_gap")

    def test_harness_status_is_not_provider_failure(self):
        row = {
            "status": "HARNESS MISMATCH",
            "dominantIssue": "provider_network_exception",
        }
        self.assertEqual(classify_census_failure(row), "transport_environment_gap")

    def test_client_transport_gap_is_not_provider_failure(self):
        row = {
            "status": "CLIENT TRANSPORT GAP",
            "dominantIssue": "provider_network_exception",
        }
        self.assertEqual(classify_census_failure(row), "transport_environment_gap")

    def test_current_targeted_and_refined_evidence_reaches_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "run-1",
                    "providers": [{
                        "provider": "demo",
                        "status": "ROUTE PROVEN",
                        "dominantIssue": "provider_network_exception",
                        "declaredLanes": ["anime"],
                        "routeProof": ["1 live route"],
                    }],
                }),
                encoding="utf-8",
            )
            (root / "automation" / "brain-repair-experience.json").write_text("{}", encoding="utf-8")
            (root / "automation" / "brain-repair-memory.json").write_text("{}", encoding="utf-8")
            (root / "automation" / "provider-targeted-regression-recovery-latest.json").write_text(
                json.dumps({
                    "providers": {
                        "demo": {
                            "debugStages": {"anime": "provider_network_exception"},
                            "statuses": {"anime": "no_streams"},
                            "verifiedLanes": [],
                            "playableLanes": [],
                            "contradictions": 0,
                            "sampleTitles": {"anime": ["Example"]},
                            "network": {
                                "anime": [{
                                    "method": "GET",
                                    "host": "example.test",
                                    "path": "/search/123",
                                    "status": 403,
                                    "headers": {"Authorization": "must-not-leak"},
                                    "shape": {
                                        "kind": "json",
                                        "top": "object",
                                        "keys": ["data", "episode", "unsafe value"],
                                        "episodeKeys": ["sourceUrls", "tobeparsed"],
                                        "secret": "must-not-leak",
                                    },
                                }, {
                                    "method": "GET",
                                    "host": "example.test",
                                    "path": "/search/456",
                                    "status": 403,
                                    "shape": {
                                        "kind": "json",
                                        "top": "object",
                                        "keys": ["data", "episode", "unsafe value"],
                                        "episodeKeys": ["sourceUrls", "tobeparsed"],
                                    },
                                }],
                            },
                        }
                    }
                }),
                encoding="utf-8",
            )
            (root / "automation" / "provider-repair-batch-refined-latest.json").write_text(
                json.dumps({
                    "sourceRunId": "run-1",
                    "groups": [{
                        "groupId": "route-to-terminal|mixed#r1",
                        "parentGroupId": "route-to-terminal|mixed",
                        "repairScope": "route-to-terminal",
                        "capabilityStrategy": "mixed_embed_resolver",
                        "providers": ["demo"],
                        "dominantIssues": ["network_exception"],
                        "debugStages": ["provider_network_exception"],
                        "networkShape": ["anime:GET:example.test:403:/search/{id}"],
                        "splitReason": "observed-signature-divergence",
                    }],
                }),
                encoding="utf-8",
            )

            request = request_from_checkout(root, "demo")
            by_source = {row["source"]: row["value"] for row in request.observations}
            current = by_source["targeted-regression-current"]
            self.assertEqual(current["debugStages"]["anime"], "provider_network_exception")
            self.assertEqual(len(current["network"]["anime"]), 1)
            self.assertEqual(current["network"]["anime"][0]["host"], "example.test")
            self.assertEqual(current["network"]["anime"][0]["sameShapeRoutes"], 2)
            self.assertNotIn("headers", current["network"]["anime"][0])
            self.assertEqual(current["network"]["anime"][0]["shape"], {
                "kind": "json",
                "top": "object",
                "keys": ["data", "episode"],
                "episodeKeys": ["sourceUrls", "tobeparsed"],
            })
            self.assertNotIn("secret", current["network"]["anime"][0]["shape"])
            refined = by_source["refined-repair-batch-current"][0]
            self.assertEqual(refined["splitReason"], "observed-signature-divergence")
            self.assertEqual(refined["networkShape"], ["anime:GET:example.test:403:/search/{id}"])

    def test_fresh_targeted_waf_routes_outside_provider_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "run-waf",
                    "providers": [{
                        "provider": "demo",
                        "status": "NO PROOF",
                        "dominantIssue": "provider_waf_challenge×2",
                        "declaredLanes": ["movie", "tv"],
                    }],
                }),
                encoding="utf-8",
            )
            for name in ("brain-repair-experience.json", "brain-repair-memory.json"):
                (root / "automation" / name).write_text("{}", encoding="utf-8")
            (root / "automation" / "provider-targeted-regression-recovery-latest.json").write_text(
                json.dumps({
                    "providers": {
                        "demo": {
                            "debugStages": {
                                "movie": "provider_waf_challenge",
                                "tv": "provider_waf_challenge",
                            },
                            "statuses": {"movie": "no_streams", "tv": "no_streams"},
                            "verifiedLanes": [],
                            "playableLanes": [],
                            "network": {
                                "movie": [{"method": "GET", "host": "provider.example.org", "path": "/interactive", "status": 200}],
                                "tv": [{"method": "GET", "host": "provider.example.org", "path": "/interactive", "status": 200}],
                            },
                        }
                    }
                }),
                encoding="utf-8",
            )
            (root / "automation" / "provider-repair-batch-refined-latest.json").write_text(
                json.dumps({"sourceRunId": "run-waf", "groups": []}),
                encoding="utf-8",
            )
            request = request_from_checkout(root, "demo")
            self.assertEqual(request.failure_class, "provider_transport_gap")

    def test_persistent_waf_across_browser_and_residential_routes_outside_provider_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "run-waf-persist",
                    "providers": [{
                        "provider": "demo",
                        "status": "NO PROOF",
                        "dominantIssue": "provider_waf_challenge×2",
                        "declaredLanes": ["movie"],
                    }],
                }),
                encoding="utf-8",
            )
            for name in ("brain-repair-experience.json", "brain-repair-memory.json"):
                (root / "automation" / name).write_text("{}", encoding="utf-8")
            (root / "automation" / "provider-targeted-regression-recovery-latest.json").write_text(
                json.dumps({"providers": {"demo": {
                    "debugStages": {"movie": "provider_waf_challenge"},
                    "statuses": {"movie": "no_streams"},
                    "verifiedLanes": [],
                    "playableLanes": [],
                    "network": {"movie": [{"method": "GET", "host": "provider.example.org", "path": "/filter", "status": 403}]},
                }}}),
                encoding="utf-8",
            )
            (root / "automation" / "provider-waf-browser-session-latest.json").write_text(
                json.dumps({"rows": [{
                    "provider": "demo",
                    "lane": "movie",
                    "outcome": "browser_challenge_persisted",
                    "residentialExitNodeProfile": {"outcome": "browser_challenge_persisted"},
                }]}),
                encoding="utf-8",
            )
            (root / "automation" / "provider-repair-batch-refined-latest.json").write_text(
                json.dumps({"sourceRunId": "run-waf-persist", "groups": []}),
                encoding="utf-8",
            )
            request = request_from_checkout(root, "demo")
            self.assertEqual(request.failure_class, "transport_environment_gap")

    def test_fresh_provider_origin_403_routes_outside_provider_mutation_even_if_stage_is_http_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "run-http-403",
                    "providers": [{
                        "provider": "demo",
                        "status": "ROUTE PROVEN",
                        "dominantIssue": "provider_network_http_error",
                        "declaredLanes": ["movie"],
                        "routeProof": ["1 live route"],
                    }],
                }),
                encoding="utf-8",
            )
            for name in ("brain-repair-experience.json", "brain-repair-memory.json"):
                (root / "automation" / name).write_text("{}", encoding="utf-8")
            (root / "automation" / "provider-targeted-regression-recovery-latest.json").write_text(
                json.dumps({
                    "providers": {
                        "demo": {
                            "debugStages": {"movie": "provider_network_http_error"},
                            "statuses": {"movie": "no_streams"},
                            "verifiedLanes": [],
                            "playableLanes": [],
                            "network": {
                                "movie": [
                                    {"method": "GET", "host": "api.themoviedb.org", "path": "/3/movie/1", "status": 200},
                                    {"method": "POST", "host": "provider.example.org", "path": "/search", "status": 403},
                                ],
                            },
                        }
                    }
                }),
                encoding="utf-8",
            )
            (root / "automation" / "provider-repair-batch-refined-latest.json").write_text(
                json.dumps({"sourceRunId": "run-http-403", "groups": []}),
                encoding="utf-8",
            )
            request = request_from_checkout(root, "demo")
            self.assertEqual(request.failure_class, "route_proven_gap")

    def test_residential_provider_replay_outranks_narrow_waf_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "run-replay",
                    "providers": [{
                        "provider": "demo",
                        "status": "ROUTE PROVEN",
                        "dominantIssue": "provider_waf_challenge",
                        "declaredLanes": ["movie"],
                        "routeProof": ["1 live route"],
                    }],
                }),
                encoding="utf-8",
            )
            for name in ("brain-repair-experience.json", "brain-repair-memory.json"):
                (root / "automation" / name).write_text("{}", encoding="utf-8")
            (root / "automation" / "provider-targeted-regression-recovery-latest.json").write_text(
                json.dumps({"providers": {"demo": {
                    "debugStages": {"movie": "provider_waf_challenge"},
                    "statuses": {"movie": "no_streams"},
                    "verifiedLanes": [],
                    "playableLanes": [],
                    "network": {"movie": [{"method": "GET", "host": "provider.example.org", "path": "/filter", "status": 403}]},
                }}}),
                encoding="utf-8",
            )
            (root / "automation" / "provider-waf-browser-session-latest.json").write_text(
                json.dumps({
                    "rows": [{
                        "provider": "demo",
                        "lane": "movie",
                        "outcome": "browser_challenge_persisted",
                        "residentialExitNodeProfile": {"outcome": "browser_challenge_persisted"},
                    }],
                    "residentialProviderReplay": {"rows": [{
                        "provider": "demo",
                        "lane": "movie",
                        "status": "no_streams",
                        "debugStage": "provider_zero_before_provider_network",
                        "raw": 0,
                        "playable": 0,
                        "verified": 0,
                        "contradictions": 0,
                        "identitySafe": True,
                    }]},
                }),
                encoding="utf-8",
            )
            (root / "automation" / "provider-repair-batch-refined-latest.json").write_text(
                json.dumps({"sourceRunId": "run-replay", "groups": []}),
                encoding="utf-8",
            )
            request = request_from_checkout(root, "demo")
            self.assertEqual(request.failure_class, "route_proven_gap")

    def test_waf_client_content_reached_routes_to_client_transport_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "run-client",
                    "providers": [{
                        "provider": "demo",
                        "status": "ROUTE PROVEN",
                        "dominantIssue": "provider_network_http_error",
                        "declaredLanes": ["movie"],
                        "routeProof": ["1 live route"],
                    }],
                }),
                encoding="utf-8",
            )
            for name in ("brain-repair-experience.json", "brain-repair-memory.json"):
                (root / "automation" / name).write_text("{}", encoding="utf-8")
            (root / "automation" / "provider-targeted-regression-recovery-latest.json").write_text(
                json.dumps({
                    "providers": {
                        "demo": {
                            "debugStages": {"movie": "provider_network_http_error"},
                            "statuses": {"movie": "no_streams"},
                            "verifiedLanes": [],
                            "playableLanes": [],
                            "network": {
                                "movie": [
                                    {"method": "GET", "host": "provider.example.org", "path": "/movie/1", "status": 403},
                                ],
                            },
                        }
                    }
                }),
                encoding="utf-8",
            )
            (root / "automation" / "provider-waf-browser-session-latest.json").write_text(
                json.dumps({
                    "rows": [{
                        "provider": "demo",
                        "lane": "movie",
                        "outcome": "browser_content_reached",
                        "contentProfiles": ["nuvio-tv-okhttp-jvm"],
                        "residentialExitNodeProfile": {"outcome": "browser_content_reached"},
                        "nativeTvTransportStillUnproven": True,
                    }],
                    "residentialProviderReplay": {"rows": []},
                }),
                encoding="utf-8",
            )
            (root / "automation" / "provider-repair-batch-refined-latest.json").write_text(
                json.dumps({"sourceRunId": "run-client", "groups": []}),
                encoding="utf-8",
            )
            request = request_from_checkout(root, "demo")
            self.assertEqual(request.failure_class, "client_transport_gap")
            by_source = {row["source"]: row["value"] for row in request.observations}
            self.assertIn("waf-client-differential-current", by_source)
            self.assertIn("nuvio-tv-okhttp-jvm", by_source["waf-client-differential-current"]["contentProfiles"])

    def test_stale_targeted_evidence_is_not_injected_or_routed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "new",
                    "providers": [{
                        "provider": "demo",
                        "status": "ROUTE PROVEN",
                        "dominantIssue": "provider_network_zero_result",
                        "declaredLanes": ["movie"],
                    }],
                }),
                encoding="utf-8",
            )
            for name in ("brain-repair-experience.json", "brain-repair-memory.json"):
                (root / "automation" / name).write_text("{}", encoding="utf-8")
            (root / "automation" / "provider-targeted-regression-recovery-latest.json").write_text(
                json.dumps({
                    "sourceCensusRunId": "old",
                    "providers": {"demo": {
                        "debugStages": {"movie": "provider_waf_challenge"},
                        "verifiedLanes": [],
                        "playableLanes": [],
                        "network": {"movie": [{
                            "method": "GET",
                            "host": "provider.example.org",
                            "path": "/interactive",
                            "status": 200,
                        }]},
                    }},
                }),
                encoding="utf-8",
            )
            (root / "automation" / "provider-repair-batch-refined-latest.json").write_text(
                json.dumps({"sourceRunId": "new", "groups": []}),
                encoding="utf-8",
            )
            request = request_from_checkout(root, "demo")
            self.assertEqual(request.failure_class, "route_proven_gap")
            self.assertNotIn(
                "targeted-regression-current",
                {row["source"] for row in request.observations},
            )

    def test_current_census_replay_evidence_reaches_policy_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({
                    "runId": "run-current",
                    "providers": [{
                        "provider": "demo",
                        "status": "ROUTE PROVEN",
                        "dominantIssue": "provider_network_zero_result",
                        "declaredLanes": ["movie"],
                        "routeProof": ["1 live route"],
                        "testedThisRun": True,
                        "residentialProviderReplayClass": "provider_zero_before_provider_network",
                        "residentialProviderReplayEvidence": [
                            "movie:provider_zero_before_provider_network:raw=0:playable=0:verified=0"
                        ],
                    }],
                }),
                encoding="utf-8",
            )
            for name in (
                "brain-repair-experience.json",
                "brain-repair-memory.json",
                "provider-targeted-regression-recovery-latest.json",
                "provider-waf-browser-session-latest.json",
                "provider-repair-batch-refined-latest.json",
            ):
                (root / "automation" / name).write_text("{}", encoding="utf-8")
            request = request_from_checkout(root, "demo")
            self.assertTrue(request.census_prior["testedThisRun"])
            self.assertEqual(
                request.census_prior["residentialProviderReplayClass"],
                "provider_zero_before_provider_network",
            )
            self.assertEqual(len(request.census_prior["residentialProviderReplayEvidence"]), 1)

    def test_stale_refined_evidence_is_not_injected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "automation").mkdir(parents=True)
            (root / "automation" / "provider-census-status.json").write_text(
                json.dumps({"runId": "new", "providers": [{"provider": "demo", "status": "NO PROOF"}]}),
                encoding="utf-8",
            )
            for name in ("brain-repair-experience.json", "brain-repair-memory.json", "provider-targeted-regression-recovery-latest.json"):
                (root / "automation" / name).write_text("{}", encoding="utf-8")
            (root / "automation" / "provider-repair-batch-refined-latest.json").write_text(
                json.dumps({"sourceRunId": "old", "groups": [{"providers": ["demo"], "networkShape": ["stale"]}]}),
                encoding="utf-8",
            )
            request = request_from_checkout(root, "demo")
            self.assertNotIn(
                "refined-repair-batch-current",
                {row["source"] for row in request.observations},
            )

    def test_provider_waf_without_route_proof_is_transport_gap(self):
        row = {
            "status": "NO PROOF",
            "dominantIssue": "provider_waf_challenge×2",
            "evidenceDepth": ["movie=none", "tv=none"],
        }
        self.assertEqual(classify_census_failure(row), "provider_transport_gap")

    def test_provider_network_exception_without_route_proof_is_transport_gap(self):
        row = {
            "status": "NO PROOF",
            "dominantIssue": "provider_network_exception",
        }
        self.assertEqual(classify_census_failure(row), "provider_transport_gap")

    def test_candidate_proof_uses_replay_gap(self):
        row = {
            "status": "CANDIDATE OK",
            "candidateProof": ["known candidate"],
            "dominantIssue": "provider_network_zero_result",
        }
        self.assertEqual(classify_census_failure(row), "candidate_replay_gap")

if __name__ == "__main__":
    unittest.main()
