import json
import unittest
from unittest.mock import patch

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.planner import ADVISOR_SYSTEM_PROMPT, ADVISOR_SOURCE_CONTRACT_SYSTEM_PROMPT, BrainPlanner
from niakvio_brain_llm.schema import EXPERIMENT_SPEC_SCHEMA, advisor_schema_for


class CaptureAdvisorBackend:
    max_tokens = 160

    def __init__(self):
        self.schema = None
        self.system = ""

    def complete(self, *, system, user, response_schema=None):
        self.system = system
        self.schema = response_schema
        provider = response_schema["properties"]["provider_id"]["const"]
        strategy_prop = response_schema["properties"]["strategy"]
        challenger = system == ADVISOR_SOURCE_CONTRACT_SYSTEM_PROMPT
        strategy = ("catalogue-inline-source-contract-discriminator" if challenger
                    else strategy_prop.get("const")
                    or (strategy_prop.get("enum") or ["provider_local_repair"])[0])
        layer = ("unknown" if challenger
                 else response_schema["properties"]["target_layer"]["enum"][0])
        return json.dumps({
            "provider_id": provider,
            "strategy": strategy,
            "confidence": 0.96,
            "target_layer": layer,
            "experiment": {
                "route_policy": "owned_plus_peer",
                "recipe_policy": "current_plus_provider",
                "role_order": ["detail", "player", "source"],
                "terminal_only": True,
                "alias_search": False,
                "response_salvage": True,
                "document_request_mining": False,
                "session_bootstrap": False,
                "max_depth": 4,
                "max_pages": 12,
                "max_embeds": 16,
                "max_recipe_passes": 3
            },
            "abstain": challenger,
            "abstain_reason": "independent network evidence is not official playback" if challenger else ""
        })


class AdvisorCompactWireTests(unittest.TestCase):
    def test_schema_omits_production_repair_payload(self):
        schema = advisor_schema_for(
            "coflix",
            {
                "confidence": 0.96,
                "target_layer": "provider",
                "strategy_prior": "mixed_embed_resolver"
            }
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["properties"]),
            {
                "provider_id", "strategy", "confidence", "target_layer",
                "experiment", "abstain", "abstain_reason"
            }
        )
        self.assertNotIn("mutations", schema["properties"])
        self.assertNotIn("evidence", schema["properties"])
        self.assertNotIn("tests", schema["properties"])
        self.assertEqual(schema["properties"]["strategy"]["const"], "mixed_embed_resolver")
        self.assertEqual(schema["properties"]["target_layer"]["enum"], ["provider"])
        self.assertEqual(
            set(schema["properties"]["experiment"]["required"]),
            set(EXPERIMENT_SPEC_SCHEMA["properties"])
        )

    def test_native_attested_source_witness_challenges_stale_high_confidence_prior(self):
        prior = {"confidence": 0.96, "target_layer": "provider",
                 "strategy_prior": "failed_old_traversal"}
        locked = advisor_schema_for("anime-sama", prior)
        self.assertEqual(locked["properties"]["strategy"]["const"], "failed_old_traversal")
        unlocked = advisor_schema_for("anime-sama", prior, source_contract_challenge=True)
        self.assertNotIn("const", unlocked["properties"]["strategy"])
        self.assertEqual(set(unlocked["properties"]["target_layer"]["enum"]),
                         {"provider", "core", "harness", "network", "unknown"})

        native = {
            "client": "tv", "historicalOnly": True, "appSelected": True,
            "readerEvidenceComplete": True, "nativeExtractionZeroObserved": True,
            "sourceRunId": "44781039914", "sourceNiakvioSha": "a" * 40,
            "providerArtifactSha256": "b" * 64,
            "fixture": "mushoku-tensei-s01e01", "manifestScope": "manifest.json",
            "nativeSourceScriptShapePatterns": ["script_http_missing", "script_html_2xx"],
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False, "providerMutationAuthority": False
        }
        independent = {
            "source": "independent-ci-source-shape",
            "currentProviderArtifactSha256": "b" * 64,
            "nativeParentRunId": "44781039914", "nativeParentSourceSha": "a" * 40,
            "fixture": "mushoku-tensei-s01e01", "manifestScope": "manifest.json",
            "catalogueSlugUnverified": "mushoku-tensei", "probeRunId": "44798438960",
            "independentNetworkNotOfficialClient": True, "historicalOnly": True,
            "catalogueIdentityVerified": False,
            "episodeIdentityVerified": False,
            "sourceContractVerifiedOnOfficialTv": False,
            "sourceObservations": [{
                "originHost": "anime-sama.to",
                "seasonSourceShape": "catalogue_inline_token_episode",
                "seasonPageStatus": 200,
                "inlineTokenSeasonObserved": True, "legacyScriptStatus": 403
            }],
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False, "providerMutationAuthority": False
        }
        request = RepairRequest(
            provider_id="anime-sama", failure_class="route_proven_gap",
            status="REGRESSION PROVIDER", advisor_only=True, allowed_mutations=[],
            observations=[
                {"source": "official-android-tv-emulator", "value": native},
                {"source": "independent-catalogue-source-probe", "value": independent}
            ]
        )
        with patch("niakvio_brain_llm.planner.build_causal_prior", return_value=prior):
            backend = CaptureAdvisorBackend()
            decision = BrainPlanner(backend).plan(request)
        self.assertEqual(backend.system, ADVISOR_SOURCE_CONTRACT_SYSTEM_PROMPT)
        self.assertNotIn("const", backend.schema["properties"]["strategy"])
        self.assertEqual(decision.strategy, "catalogue-inline-source-contract-discriminator")
        self.assertEqual(decision.target_layer, "unknown")
        self.assertTrue(decision.abstain)
        self.assertEqual(decision.mutations, [])

        for observations in (
            [request.observations[1]],
            [request.observations[0], {
                "source": "independent-catalogue-source-probe",
                "value": {**independent, "currentProviderArtifactSha256": "c" * 64}
            }]
        ):
            with self.subTest(observations=observations):
                forged = RepairRequest(
                    provider_id="anime-sama", failure_class="route_proven_gap",
                    advisor_only=True, observations=observations
                )
                with patch("niakvio_brain_llm.planner.build_causal_prior",
                           return_value=prior):
                    backend = CaptureAdvisorBackend()
                    proposal, _, _ = BrainPlanner(backend)._generate(
                        forged, constrained=True
                    )
                self.assertEqual(backend.system, ADVISOR_SYSTEM_PROMPT)
                self.assertEqual(backend.schema["properties"]["strategy"]["const"],
                                 "failed_old_traversal")
                self.assertEqual(proposal.strategy, "failed_old_traversal")

    def test_exhausted_executor_unlocks_strategy_but_keeps_provider_layer(self):
        prior = {
            "confidence": 0.96,
            "target_layer": "provider",
            "strategy_prior": "terminal-media-extractor-with-playback-validation",
        }
        history = [
            {
                "profile": "chain_terminal_extractor_v1",
                "executionObserved": True,
                "consecutiveFailures": 1,
                "lastOutcome": "rejected",
                "llmAdvisorExperimentFingerprint": ("%064x" % ordinal),
            }
            for ordinal in (1, 2, 3)
        ]
        request = RepairRequest(
            provider_id="generic-terminal-provider",
            failure_class="chain_terminal_gap",
            status="CHAIN REACHED",
            advisor_only=True,
            allowed_mutations=[],
            provider_context={"advisor_experiment_history": history},
        )
        with patch("niakvio_brain_llm.planner.build_causal_prior", return_value=prior):
            backend = CaptureAdvisorBackend()
            proposal = BrainPlanner(backend).plan(request)
        strategy_schema = backend.schema["properties"]["strategy"]
        self.assertNotIn("const", strategy_schema)
        self.assertNotIn(prior["strategy_prior"], strategy_schema.get("enum") or [])
        self.assertEqual(backend.schema["properties"]["target_layer"]["enum"], ["provider"])
        self.assertNotEqual(proposal.strategy, prior["strategy_prior"])
        self.assertEqual(proposal.target_layer, "provider")
        self.assertFalse(proposal.abstain)
        self.assertEqual(proposal.mutations, [])

    def test_strong_runtime_stall_excludes_executor_after_one_real_causal_no_gain(self):
        prior = {
            "confidence": 0.96,
            "target_layer": "provider",
            "strategy_prior": "discover-api-from-current-page-and-bundles",
        }
        history = [{
            "profile": "search_contract_inference_v1",
            "executionObserved": True,
            "causalExerciseObserved": True,
            "consecutiveFailures": 1,
            "lastOutcome": "rejected",
            "llmAdvisorExperimentFingerprint": "c" * 64,
            "networkExecutionDelta": {
                "providerRequestDelta": 0,
                "successfulProviderRequestDelta": 0,
                "networkFailureDelta": 0,
                "stageRankDelta": 0,
                "stageAdvanced": False,
                "newMethods": [],
                "newStages": [],
                "newResponseKinds": [],
                "statusBucketDelta": {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "network": 0},
            },
        }]
        request = RepairRequest(
            provider_id="generic-terminal-provider",
            failure_class="variant_coverage_gap",
            status="CHAIN REACHED",
            advisor_only=True,
            allowed_mutations=[],
            provider_context={"advisor_experiment_history": history},
        )
        with patch("niakvio_brain_llm.planner.build_causal_prior", return_value=prior):
            backend = CaptureAdvisorBackend()
            proposal = BrainPlanner(backend).plan(request)
        strategy_schema = backend.schema["properties"]["strategy"]
        self.assertNotIn(prior["strategy_prior"], strategy_schema.get("enum") or [])
        self.assertNotEqual(proposal.strategy, prior["strategy_prior"])
        self.assertEqual(proposal.target_layer, "provider")

    def test_planner_reconstructs_full_proposal_locally(self):
        backend = CaptureAdvisorBackend()
        proposal = BrainPlanner(backend).plan(
            RepairRequest(
                provider_id="coflix",
                failure_class="variant_coverage_gap",
                status="FULL OK",
                advisor_only=True,
                provider_context={
                    "runtime_variant_coverage": {
                        "riskKind": "variant-coverage-truncation",
                        "dimensions": ["quality", "player", "source"]
                    }
                }
            )
        )
        self.assertEqual(backend.system, ADVISOR_SYSTEM_PROMPT)
        self.assertNotIn("mutations", backend.schema["properties"])
        self.assertEqual(proposal.provider_id, "coflix")
        self.assertEqual(proposal.diagnosis, "advisor-only strategy/experiment guidance")
        self.assertEqual(proposal.mutations, [])
        self.assertEqual(proposal.evidence, [])
        self.assertIn("replay_provider_on_current_bytes", proposal.tests)
        self.assertIn("validate_playback_identity_and_non_regression", proposal.tests)
        self.assertTrue(proposal.experiment)


if __name__ == "__main__":
    unittest.main()
