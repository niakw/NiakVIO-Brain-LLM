import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.repair_family import repair_family_descriptor
from niakvio_brain_llm.retrieval import ExperienceStore
from niakvio_brain_llm.routing import route_request


class RoutingTests(unittest.TestCase):
    def test_full_ok_without_failure_skips_llm(self):
        decision = route_request(
            RepairRequest(provider_id="demo", failure_class="healthy", status="FULL OK")
        )
        self.assertEqual(decision.mode, "skip")
        self.assertFalse(decision.requires_llm)

    def test_official_tv_script_200_html_zero_routes_source_family_not_provider_patch(self):
        base = {
            "source": "official-android-tv-emulator", "client": "tv",
            "historicalOnly": True, "appSelected": True,
            "readerEvidenceComplete": True,
            "nativeExtractionZeroObserved": True,
            "nativeSourceScriptShapePatterns": ["script_http_missing", "script_html_2xx"],
            "tvPromiseControl": "bridge_ok",
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False, "providerMutationAuthority": False,
        }

        def decide(row):
            return route_request(RepairRequest(
                provider_id="anime-sama",
                failure_class="media_extraction_gap",
                status="REGRESSION PROVIDER",
                allowed_mutations=["provider_patch", "provider_bloc"],
                observations=[{"source": "official-android-tv-emulator", "value": row}],
            ))

        routed = decide(base)
        self.assertEqual(routed.strategy, "discriminate_catalogue_script_html_vs_missing_source_shape")
        self.assertEqual(routed.mode, "llm_diagnose")
        self.assertEqual(routed.target_layer, "unknown")
        self.assertTrue(routed.requires_llm)
        self.assertEqual(routed.allowed_mutations, [])
        self.assertTrue(any("episodes.js" in x for x in routed.next_actions))
        for changed in (
            {"nativeSourceScriptShapePatterns": ["script_http_missing"]},
            {"nativeExtractionZeroObserved": False},
            {"appSelected": False},
            {"readerEvidenceComplete": False},
            {"historicalOnly": False},
            {"nativePlaybackAuthority": True},
            {"providerMutationAuthority": True},
        ):
            with self.subTest(changed=changed):
                self.assertNotEqual(
                    decide({**base, **changed}).strategy,
                    "discriminate_catalogue_script_html_vs_missing_source_shape",
                )

    def test_official_tv_hard_timeout_is_not_generic_provider_replay(self):
        value = {
            "source": "official-android-tv-emulator", "client": "tv",
            "historicalOnly": True, "appSelected": True,
            "nativeHardTimeoutObserved": True, "nativeHardTimeoutMs": 25000,
            "quickJsPhases": ["call"], "quickJsReturned": 0,
            "nativeExtractionZeroObserved": False, "nativeExtractionPositiveObserved": False,
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False, "providerMutationAuthority": False,
        }
        def route(value):
            return route_request(RepairRequest(
                provider_id="sadisflix",
                failure_class="media_extraction_gap", status="REGRESSION PROVIDER",
                allowed_mutations=["provider_patch", "provider_bloc"],
                observations=[{"source": "official-android-tv-emulator", "value": value}],
            ))
        decision = route(value)
        self.assertEqual(decision.mode, "llm_diagnose")
        self.assertEqual(decision.strategy, "discriminate_tv_native_hard_timeout_owner")
        self.assertEqual(decision.target_layer, "unknown")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, [])
        self.assertTrue(any("fetch" in step for step in decision.next_actions))
        for bad in (
            {**value, "nativeHardTimeoutObserved": False},
            {**value, "nativeHardTimeoutMs": 0},
            {**value, "nativeHardTimeoutMs": 25.0},
            {**value, "appSelected": False},
            {**value, "historicalOnly": False},
            {**value, "nativePlaybackAuthority": True},
        ):
            with self.subTest(bad=bad):
                self.assertNotEqual(
                    route(bad).strategy, "discriminate_tv_native_hard_timeout_owner"
                )

    def test_tv_hls_2xx_near_25s_zero_routes_owner_not_provider_mutation(self):
        base = {
            "source": "official-android-tv-emulator", "client": "tv",
            "historicalOnly": True, "appSelected": True,
            "nativeExtractionZeroObserved": True,
            "hlsPlaylist2xxNearProviderBudgetZeroObserved": True,
            "sameMediaRootSuccessThenForbidden": False,
            "tvPromiseControl": "bridge_ok",
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False, "providerMutationAuthority": False,
        }

        def decide(row):
            return route_request(RepairRequest(
                provider_id="french-manga", status="CANDIDATE OK",
                failure_class="media_extraction_gap",
                allowed_mutations=["provider_bloc", "provider_patch"],
                observations=[{
                    "source": "official-android-tv-emulator",
                    "value": row,
                }],
            ))

        route = decide(base)
        self.assertEqual(route.mode, "llm_diagnose")
        self.assertEqual(route.target_layer, "unknown")
        self.assertEqual(route.strategy, "discriminate_tv_hls_success_zero_near_js_budget_owner")
        self.assertTrue(route.requires_llm)
        self.assertEqual(route.allowed_mutations, [])
        self.assertTrue(any("ProviderBase" in step for step in route.next_actions))
        self.assertTrue(any("Call.execute" in step and "Promise.all" in step
                            for step in route.next_actions))
        self.assertTrue(any("reject JS-only hedging" in step
                            for step in route.next_actions))
        for bad in (
            {**base, "hlsPlaylist2xxNearProviderBudgetZeroObserved": False},
            {**base, "nativeExtractionZeroObserved": False},
            {**base, "appSelected": False},
            {**base, "historicalOnly": False},
            {**base, "nativePlaybackAuthority": True},
            {**base, "providerMutationAuthority": True},
        ):
            with self.subTest(bad=bad):
                self.assertNotEqual(
                    decide(bad).strategy,
                    "discriminate_tv_hls_success_zero_near_js_budget_owner",
                )

    def test_tv_promise_bridge_failure_is_client_owned_not_provider_mutation(self):
        base = {
            "source": "official-android-tv-emulator",
            "client": "tv", "historicalOnly": True,
            "appSelected": True,
            "nativeExtractionZeroObserved": True,
            "tvPromiseControl": "promise_delivery_gap",
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False, "providerMutationAuthority": False,
        }
        def decide(value):
            return route_request(RepairRequest(
                provider_id="demo", status="REGRESSION PROVIDER",
                failure_class="media_extraction_gap",
                allowed_mutations=["provider_patch"],
                observations=[{
                    "source": "official-android-tv-emulator",
                    "value": value,
                }],
            ))
        route = decide(base)
        self.assertEqual(route.mode, "llm_diagnose")
        self.assertEqual(route.target_layer, "client")
        self.assertEqual(route.strategy, "diagnose_android_tv_quickjs_promise_completion")
        self.assertTrue(route.requires_llm)
        self.assertEqual(route.allowed_mutations, [])
        self.assertTrue(any("synthetic" in line for line in route.next_actions))
        baseline = decide({**base, "tvPromiseControl": "baseline_failed"})
        self.assertEqual(baseline.mode, "probe")
        self.assertEqual(baseline.strategy, "isolate_android_tv_quickjs_baseline")
        self.assertEqual(baseline.allowed_mutations, [])
        for bad in (
            {**base, "proofAuthority": True},
            {**base, "appSelected": False},
            {**base, "nativeExtractionZeroObserved": False},
            {**base, "historicalOnly": False},
            {**base, "tvPromiseControl": "bridge_ok"},
        ):
            with self.subTest(bad=bad):
                result = decide(bad)
                self.assertNotEqual(
                    result.strategy, "diagnose_android_tv_quickjs_promise_completion"
                )
                self.assertNotEqual(result.strategy, "isolate_android_tv_quickjs_baseline")

    def test_android_tv_is_primary_probe_for_cross_client_visibility_gap(self):
        report = {
            "source": "user-client-field-report",
            "value": {
                "authority": "historical-user-report-only",
                "crossClientVisibilityDiscrepancy": True,
                "proofAuthority": False,
                "publicationAuthority": False,
                "mutationAuthority": False,
                "executedJsKnown": False,
            },
        }
        base = {
            "provider_id": "french-manga",
            "failure_class": "candidate_replay_gap",
            "status": "CANDIDATE OK",
        }
        before = route_request(RepairRequest(**base, observations=[report]))
        self.assertEqual(before.mode, "probe")
        self.assertEqual(before.target_layer, "client")
        self.assertEqual(before.strategy, "run_official_android_tv_emulator_first")
        self.assertEqual(before.allowed_mutations, [])
        self.assertFalse(before.requires_llm)

        tv = {
            "source": "official-android-tv-emulator",
            "value": {
                "source": "official-android-tv-emulator",
                "client": "tv", "historicalOnly": True,
                "appSelected": True,
                "quickJsReturned": 0,
                "quickJsErrors": ["reference_error"],
                "proofAuthority": False,
                "publicationAuthority": False,
                "nativePlaybackAuthority": False,
                "providerMutationAuthority": False,
            },
        }
        diagnosed = route_request(RepairRequest(**base, observations=[report, tv]))
        self.assertEqual(diagnosed.mode, "llm_diagnose")
        self.assertEqual(diagnosed.target_layer, "client")
        self.assertEqual(diagnosed.strategy, "trace_tv_quickjs_media_context_and_transport")
        self.assertEqual(diagnosed.allowed_mutations, [])
        self.assertTrue(diagnosed.requires_llm)

        # Even emulator 'ready' on the same JS needs a real correct-media proof.
        tv_positive = {"source": "official-android-tv-emulator", "value": {
            **tv["value"], "quickJsReturned": 1,
            "quickJsErrors": [], "playerStates": ["ready"],
        }}
        unresolved = route_request(RepairRequest(**base, observations=[report, tv_positive]))
        self.assertEqual(unresolved.mode, "probe")
        self.assertEqual(unresolved.strategy, "complete_official_android_tv_player_probe")
        self.assertEqual(unresolved.allowed_mutations, [])

        tv_forged = {"source": "official-android-tv-emulator", "value": {
            **tv["value"], "nativePlaybackAuthority": True,
        }}
        refused = route_request(RepairRequest(**base, observations=[report, tv_forged]))
        self.assertEqual(refused.mode, "probe")
        self.assertEqual(refused.strategy, "run_official_android_tv_emulator_first")

    def test_android_tv_quickjs_call_only_never_infers_a_returned_zero(self):
        report = {
            "source": "user-client-field-report",
            "value": {
                "authority": "historical-user-report-only",
                "crossClientVisibilityDiscrepancy": True,
                "proofAuthority": False,
                "publicationAuthority": False,
                "mutationAuthority": False,
                "executedJsKnown": False,
            },
        }
        tv = {
            "source": "official-android-tv-emulator",
            "value": {
                "source": "official-android-tv-emulator",
                "client": "tv", "historicalOnly": True,
                "appSelected": True, "quickJsPhases": ["call"],
                "quickJsReturned": 0, "quickJsErrors": [],
                "nativeExtractionZeroObserved": False,
                "proofAuthority": False, "publicationAuthority": False,
                "nativePlaybackAuthority": False, "providerMutationAuthority": False,
            },
        }
        args = dict(provider_id="french-manga", status="CANDIDATE OK",
                    failure_class="candidate_replay_gap")
        unknown = route_request(RepairRequest(**args, observations=[report, tv]))
        self.assertEqual(unknown.mode, "probe")
        self.assertEqual(unknown.strategy, "complete_android_tv_quickjs_execution_trace")
        self.assertEqual(unknown.allowed_mutations, [])

        tv["value"]["nativeExtractionZeroObserved"] = True
        confirmed_zero = route_request(RepairRequest(**args, observations=[report, tv]))
        self.assertEqual(confirmed_zero.mode, "llm_diagnose")
        self.assertEqual(confirmed_zero.target_layer, "unknown")
        self.assertEqual(confirmed_zero.strategy,
                         "discriminate_tv_runtime_network_core_vs_provider")
        self.assertEqual(confirmed_zero.allowed_mutations, [])
        self.assertTrue(confirmed_zero.requires_llm)

        tv["value"]["providerMutationAuthority"] = True
        forgery = route_request(RepairRequest(**args, observations=[report, tv]))
        self.assertEqual(forgery.mode, "probe")
        self.assertEqual(forgery.strategy, "run_official_android_tv_emulator_first")

    def test_full_ok_variant_coverage_gap_routes_provider_synthesis(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="variant_coverage_gap",
                status="FULL OK",
                allowed_mutations=["provider_bloc"],
                provider_context={
                    "runtimeMutationSource": (
                        "function resolve(links){var out=[];"
                        "for(var i=0;i<links.length;i++){if(out.length>=4)break}"
                        "return out}"
                    ),
                    "runtime_variant_coverage": {
                        "riskKind": "variant-coverage-truncation",
                        "risk": "high",
                    },
                },
            )
        )
        self.assertEqual(decision.mode, "llm_repair")
        self.assertEqual(decision.target_layer, "provider")
        self.assertEqual(decision.strategy, "enumerate_stream_variants_before_global_cap")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, ["provider_bloc"])

    def test_harness_failure_is_deterministic(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="transport_environment_gap",
                status="HARNESS MISMATCH",
            )
        )
        self.assertEqual(decision.mode, "deterministic")
        self.assertEqual(decision.target_layer, "harness")
        self.assertFalse(decision.requires_llm)

    def test_confirmed_cross_network_browser_native_gap_uses_llm_architecture_diagnosis(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="transport_environment_gap",
                status="CLIENT TRANSPORT GAP",
                census_prior={"harnessTransportClass": "browser-profile-only-both-networks"},
            )
        )
        self.assertEqual(decision.mode, "llm_diagnose")
        self.assertEqual(decision.target_layer, "harness")
        self.assertEqual(decision.strategy, "native_tls_browser_differential_v1")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, [])

    def test_legacy_harness_mismatch_with_confirmed_differential_also_uses_llm(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="transport_environment_gap",
                status="HARNESS MISMATCH",
                census_prior={"harnessTransportClass": "browser-profile-only-both-networks"},
            )
        )
        self.assertEqual(decision.mode, "llm_diagnose")
        self.assertTrue(decision.requires_llm)

    def test_api_discovery_without_fresh_url_probes_first(self):
        store = ExperienceStore([{
            "experience_id": "movix",
            "failure_class": "api_discovery_gap",
            "providers": ["movix"],
            "strategy": "discover_api_from_current_page_and_bundles",
        }])
        decision = route_request(
            RepairRequest(
                provider_id="movix",
                failure_class="api_discovery_gap",
                status="NO PROOF",
                provider_context={"override": "{}"},
                observations=[{"signal": "fixed endpoint 403"}],
            ),
            store,
        )
        self.assertEqual(decision.mode, "probe")
        self.assertFalse(decision.requires_llm)

    def test_no_proof_provider_transport_requires_recognition_before_llm(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="provider_transport_gap",
                status="NO PROOF",
                allowed_mutations=["provider_patch", "provider_bloc"],
                provider_context={
                    "route_contract": {
                        "synthesisPolicy": {
                            "mode": "rediscover_by_traversal",
                            "runtimeSynthesisAllowed": False,
                        }
                    },
                    "runtimeMutationSource": "function resolve(){return [];}",
                },
            )
        )
        self.assertEqual(decision.mode, "probe")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, [])
        self.assertEqual(decision.strategy, "rediscover_current_provider_route_by_traversal")
        self.assertIn("persist newly proven route DATA", decision.next_actions)

    def test_rediscovery_policy_blocks_llm_even_if_status_is_not_no_proof(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="provider_transport_gap",
                status="ROUTE PROVEN",
                allowed_mutations=["provider_bloc"],
                provider_context={
                    "route_contract": {
                        "synthesisPolicy": {
                            "mode": "rediscover_by_traversal",
                            "runtimeSynthesisAllowed": False,
                        }
                    },
                    "runtimeMutationSource": "function resolve(){return [];}",
                },
            )
        )
        self.assertEqual(decision.mode, "probe")
        self.assertFalse(decision.requires_llm)

    def test_provider_patch_with_fresh_evidence_uses_llm(self):
        store = ExperienceStore([{
            "experience_id": "movix",
            "failure_class": "api_discovery_gap",
            "providers": ["movix"],
            "strategy": "discover_api_from_current_page_and_bundles",
        }])
        decision = route_request(
            RepairRequest(
                provider_id="movix",
                failure_class="api_discovery_gap",
                provider_context={"override": "{}"},
                observations=[{
                    "source": "current_bundle_probe",
                    "candidate_api_url": "https://api.movix.fun",
                }],
            ),
            store,
        )
        self.assertEqual(decision.mode, "llm_repair")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, ["provider_data"])

    def test_advisor_only_high_confidence_provider_strategy_is_deterministic(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="route_proven_gap",
                status="ROUTE PROVEN",
                advisor_only=True,
            )
        )
        self.assertEqual(decision.mode, "deterministic_advisor")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.target_layer, "provider")
        self.assertEqual(decision.strategy, "search_detail_player_terminal_traversal")
        self.assertEqual(decision.allowed_mutations, [])

    def test_advisor_only_failed_current_strategy_rotates_without_llm(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="route_proven_gap",
                status="ROUTE PROVEN",
                advisor_only=True,
                provider_context={
                    "advisor_experiment_history": [{
                        "profile": "proven_route_terminal_traversal_v1",
                        "llmAdvisorExperimentFingerprint": "a" * 64,
                        "consecutiveFailures": 2,
                        "lastOutcome": "rejected",
                    }],
                },
            )
        )
        self.assertEqual(decision.mode, "deterministic_advisor")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.strategy, "search_detail_player_terminal_traversal")
        self.assertEqual(decision.allowed_mutations, [])

    def test_executed_advisor_family_debt_escalates_to_model(self):
        history = [{
            "profile": "proven_route_terminal_traversal_v1",
            "llmAdvisorExperimentFingerprint": f"{index:064x}",
            "consecutiveFailures": 1,
            "lastOutcome": "rejected",
            "executionObserved": True,
        } for index in (1, 2, 3)]
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            advisor_only=True,
            provider_context={"advisor_experiment_history": history},
        )
        decision = route_request(request)
        self.assertEqual(decision.mode, "llm_repair")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.target_layer, "provider")
        self.assertEqual(decision.allowed_mutations, [])

    def test_unexecuted_legacy_and_duplicate_experiments_do_not_force_model(self):
        history = [{
            "profile": "proven_route_terminal_traversal_v1",
            "llmAdvisorExperimentFingerprint": "a" * 64,
            "consecutiveFailures": 3,
            "lastOutcome": "rejected",
            "executionObserved": True,
        }] * 4
        history.extend([{
            "profile": "proven_route_terminal_traversal_v1",
            "llmAdvisorExperimentFingerprint": f"{index:064x}",
            "consecutiveFailures": 1,
            "lastOutcome": "rejected",
            "executionObserved": False,
        } for index in (2, 3, 4)])
        history.append({
            "profile": "chain_terminal_extractor_v1",
            "llmAdvisorExperimentFingerprint": "f" * 64,
            "consecutiveFailures": 9,
            "lastOutcome": "rejected",
            "executionObserved": True,
        })
        decision = route_request(RepairRequest(
            provider_id="demo", failure_class="route_proven_gap",
            status="ROUTE PROVEN", advisor_only=True,
            provider_context={"advisor_experiment_history": history},
        ))
        self.assertEqual(decision.mode, "deterministic_advisor")
        self.assertFalse(decision.requires_llm)

    def test_advisor_only_candidate_replay_gets_bounded_experiment(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="candidate_replay_gap",
                status="CANDIDATE OK",
                advisor_only=True,
            )
        )
        self.assertEqual(decision.mode, "deterministic_advisor")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.strategy, "same_provider_candidate_program_replay")

    def test_client_field_report_adds_discriminating_app_selection_only_when_non_authoritative(self):
        current = {
            "source": "current-provider-retest-media",
            "value": {
                "source": "same-js-current-retest",
                "playable": 2, "verified": 0,
                "identityReasons": ["insufficient_identity_metadata"],
                "proofAuthority": False, "publicationAuthority": False,
                "nativePlaybackAuthority": False,
            },
        }
        field = {
            "source": "user-client-field-report",
            "value": {
                "authority": "historical-user-report-only",
                "crossClientVisibilityDiscrepancy": True,
                "executedJsKnown": False,
                "proofAuthority": False,
                "publicationAuthority": False,
                "mutationAuthority": False,
            },
        }
        def decision(field_row):
            return route_request(RepairRequest(
                provider_id="demo", failure_class="candidate_replay_gap",
                status="CANDIDATE OK", advisor_only=True,
                observations=[current, field_row],
            ))
        route = decision(field)
        self.assertEqual(route.mode, "llm_diagnose")
        self.assertEqual(route.allowed_mutations, [])
        self.assertTrue(any("installed manifest projection" in x for x in route.next_actions))
        self.assertTrue(any("native app media-type selection" in x for x in route.next_actions))
        fake = {
            **field, "value": {**field["value"], "mutationAuthority": True}
        }
        self.assertFalse(any("installed manifest projection" in x for x in decision(fake).next_actions))
        self.assertFalse(any("installed manifest projection" in x for x in
                             decision({"source": "user-client-field-report",
                                       "value": {**field["value"], "executedJsKnown": True}}).next_actions))

    def test_exact_current_unverified_candidate_escalates_to_causal_diagnosis(self):
        candidate = {
            "source": "same-js-current-retest",
            "playable": 2, "verified": 0,
            "identityReasons": ["insufficient_identity_metadata", "duration_incomplete_hls"],
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False,
        }
        request = RepairRequest(
            provider_id="demo", failure_class="candidate_replay_gap",
            status="CANDIDATE OK", advisor_only=True,
            observations=[{"source": "current-provider-retest-media", "value": candidate}],
        )
        route = route_request(request)
        self.assertEqual(route.mode, "llm_diagnose")
        self.assertTrue(route.requires_llm)
        self.assertEqual(route.strategy, "trace_independent_episode_and_hls_provenance")
        self.assertEqual(route.target_layer, "unknown")
        self.assertEqual(route.allowed_mutations, [])
        self.assertGreaterEqual(len(route.next_actions), 3)

    def test_historical_or_stale_identity_gap_does_not_trigger_model(self):
        candidate = {
            "source": "same-js-current-retest", "playable": 2, "verified": 0,
            "identityReasons": ["insufficient_identity_metadata"],
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False,
        }
        cases = [
            {"source": "historical-provider-retest-media", "value": candidate},
            {"source": "current-provider-retest-media",
             "value": {**candidate, "source": "historical-exact-js-retest"}},
            {"source": "current-provider-retest-media",
             "value": {**candidate, "proofAuthority": True}},
            {"source": "current-provider-retest-media",
             "value": {**candidate, "verified": 1}},
            {"source": "current-provider-retest-media",
             "value": {**candidate, "playable": 0}},
            {"source": "current-provider-retest-media",
             "value": {**candidate, "identityReasons": []}},
        ]
        for observation in cases:
            with self.subTest(observation=observation):
                request = RepairRequest(
                    provider_id="demo", failure_class="candidate_replay_gap",
                    status="CANDIDATE OK", advisor_only=True,
                    observations=[observation],
                )
                self.assertEqual(route_request(request).mode, "deterministic_advisor")

    def test_validated_same_family_routes_before_llm(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            supported_types=["movie", "tv"],
            allowed_mutations=["provider_patch"],
            provider_context={
                "registered_patch_scripts":["scripts/provider_patches/demo_runtime_v1.py"],
                "registered_patch_sources":{
                    "scripts/provider_patches/demo_runtime_v1.py":"function classBlocks(html,cls){return []}"
                },
            },
            observations=[{
                "source":"targeted-regression-current",
                "value":{
                    "debugStages":{"movie":"provider_network_zero_result"},
                    "network":{"movie":[{"status":200}]},
                    "structureHints":[
                        "movie:classes=movie-card,movie-card-format;"
                        "classFacts=[movie-card;count=12;selfHref=1;nestedAnchors=24;"
                        "tags=a,div,span;signals=movie,series,year]"
                    ],
                },
            }],
        )
        family = repair_family_descriptor(request)
        store = ExperienceStore([{
            "experience_id":"family-1",
            "failure_class":"route_proven_gap",
            "result":"validated",
            "repair_family":family,
            "mechanismFamily":"balanced-class-container",
            "strategy":"balanced-class-container",
            "successCount":3,
            "failureCount":0,
        }])
        decision = route_request(request, store)
        self.assertEqual(decision.mode, "family_replay")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.strategy, "balanced-class-container")
        self.assertEqual(decision.allowed_mutations, ["provider_patch"])

    def test_clean_residential_replay_routes_provider_gap_to_llm_repair(self):
        decision = route_request(
            RepairRequest(
                provider_id="demo",
                failure_class="route_proven_gap",
                status="ROUTE PROVEN",
                allowed_mutations=["provider_bloc"],
                provider_context={
                    "runtimeMutationSource": "function getStreams(item){return [];}",
                },
                observations=[
                    {
                        "source": "census_current",
                        "value": {"status": "ROUTE PROVEN"},
                    },
                    {
                        "source": "targeted-regression-current",
                        "value": {
                            "debugStages": {"movie": "provider_waf_challenge"},
                            "network": {"movie": [{"host": "provider.example", "status": 403}]},
                        },
                    },
                    {
                        "source": "waf-client-differential-current",
                        "value": {
                            "residentialReplay": [{
                                "status": "no_streams",
                                "debugStage": "provider_zero_before_provider_network",
                                "contradictions": 0,
                                "identitySafe": True,
                            }],
                        },
                    },
                ],
            )
        )
        self.assertEqual(decision.target_layer, "provider")
        self.assertEqual(decision.mode, "llm_repair")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, ["provider_bloc"])

    def test_unknown_failure_uses_llm_diagnosis_without_mutations(self):
        decision = route_request(
            RepairRequest(provider_id="demo", failure_class="novel_unknown_failure")
        )
        self.assertEqual(decision.mode, "llm_diagnose")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, [])


if __name__ == "__main__":
    unittest.main()
