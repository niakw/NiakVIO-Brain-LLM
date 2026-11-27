"""Keep exact native-attested independent source contract through LLM prompt budgets."""
from __future__ import annotations

import copy
import json
import unittest

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import (
    _source_contract_prompt_witness,
    build_prompt_payload,
)


class SourceContractPromptWitnessTests(unittest.TestCase):
    sha = "a" * 40
    digest = "b" * 64
    native_run_id = "44781039914"
    probe_run = "44798438960"

    def request(self):
        parent = {
            "source": "official-android-tv-emulator",
            "value": {
                "client": "tv",
                "sourceRunId": self.native_run_id,
                "sourceNiakvioSha": self.sha,
                "providerArtifactSha256": self.digest,
                "fixture": "mushoku-tensei-s01e01",
                "manifestScope": "manifest.json",
                "nativeSourceScriptShapePatterns": [
                    "script_html_2xx", "script_http_missing"
                ],
                "appSelected": True,
                "readerEvidenceComplete": True,
                "historicalOnly": True,
                "nativeExtractionZeroObserved": True,
                "proofAuthority": False,
                "publicationAuthority": False,
                "nativePlaybackAuthority": False,
                "providerMutationAuthority": False,
            },
        }
        independent = {
            "source": "independent-catalogue-source-probe",
            "value": {
                "source": "independent-ci-source-shape",
                "nativeParentRunId": self.native_run_id,
                "nativeParentSourceSha": self.sha,
                "currentProviderArtifactSha256": self.digest,
                "probeRunId": self.probe_run,
                "fixture": "mushoku-tensei-s01e01",
                "manifestScope": "manifest.json",
                "catalogueSlugUnverified": "mushoku-tensei",
                "historicalOnly": True,
                "independentNetworkNotOfficialClient": True,
                "catalogueIdentityVerified": False,
                "episodeIdentityVerified": False,
                "sourceContractVerifiedOnOfficialTv": False,
                "proofAuthority": False,
                "publicationAuthority": False,
                "nativePlaybackAuthority": False,
                "providerMutationAuthority": False,
                "rawHtml": "PRIVATE_JETON",
                "mediaUrl": "https://SECRET.invalid/PRIVATE",
                "sourceObservations": [
                    {
                        "originHost": "anime-sama.to",
                        "seasonSourceShape": "catalogue_inline_token_episode",
                        "seasonPageStatus": 200,
                        "legacyScriptStatus": 403,
                        "inlineTokenSeasonObserved": True,
                        "tokenResolverStatus": 200,
                        "tokenResolverContract": "same-origin-api-lien-j-l-v1",
                        "tokenResolverJsonObjectObserved": True,
                        "tokenResolverUrlFieldObserved": True,
                        "tokenResolverHttpsUrlObserved": True,
                        "resolvedTargetStatus": 200,
                        "resolvedTargetShape": "html_player",
                        "resolvedTargetDirectMediaObserved": False,
                        "resolvedTargetPlayerEmbedObserved": True,
                        "resolvedTargetSameOrigin": False,
                        "resolvedTargetRedirectObserved": False,
                        "resolvedTargetPlayerStructureClass": "mixed",
                        "resolvedTargetIframeCount": 1,
                        "resolvedTargetVideoTagCount": 0,
                        "resolvedTargetSourceTagCount": 0,
                        "resolvedTargetExternalScriptCount": 1,
                        "resolvedTargetInlineScriptCount": 1,
                        "resolvedTargetFormCount": 1,
                        "resolvedTargetHiddenInputCount": 2,
                        "resolvedTargetRequestCallCount": 4,
                        "resolvedTargetFetchCallCount": 1,
                        "resolvedTargetXhrCallCount": 1,
                        "resolvedTargetAxiosCallCount": 1,
                        "resolvedTargetAjaxCallCount": 1,
                        "resolvedTargetRequestLiteralUrlCount": 2,
                        "resolvedTargetRequestDynamicUrlCount": 2,
                        "resolvedTargetRequestTemplateUrlCount": 1,
                        "resolvedTargetRequestConcatUrlCount": 0,
                        "resolvedTargetRequestIdentifierUrlCount": 1,
                        "resolvedTargetRequestMemberUrlCount": 0,
                        "resolvedTargetRequestCallExpressionUrlCount": 0,
                        "resolvedTargetRequestOtherDynamicUrlCount": 1,
                        "resolvedTargetRequestSameOriginLiteralCount": 1,
                        "resolvedTargetRequestCrossOriginLiteralCount": 1,
            "resolvedTargetRequestStaticCandidateCount": 2,
            "resolvedTargetRequestStaticSameOriginCount": 1,
            "resolvedTargetRequestStaticCrossOriginCount": 1,
            "resolvedTargetRequestStaticMediaIntentCount": 1,
            "resolvedTargetRequestStaticSameOriginMediaIntentCount": 0,
                        "resolvedTargetPostFormObserved": True,
                        "resolvedTargetRequestBootstrapObserved": True,
                        "resolvedTargetPackedScriptObserved": False,
                        "resolvedTargetBase64DecodeObserved": True,
                        "resolvedTargetMetaRefreshObserved": False,
                        "rawPlayer": "https://SECRET.invalid/PRIVATE",
                    },
                    {
                        "originHost": "animes-sama.fr",
                        "seasonSourceShape": "script_html_2xx",
                        "seasonPageStatus": 200,
                        "legacyScriptStatus": 404,
                        "inlineTokenSeasonObserved": False,
                    },
                ],
            },
        }
        return RepairRequest(
            provider_id="anime-sama",
            failure_class="route_proven_gap",
            status="REGRESSION PROVIDER",
            supported_types=["anime"],
            observations=[
                {"source": "census_current", "value": {"large": "z" * 7000}},
                parent, independent,
            ],
            provider_context={
                "registered_patch_sources": {"scripts/provider_patches/anime_runtime.py": "x" * 8000},
                "route_contract": {"historicalRoutes": ["route" * 250] * 3},
                "advisor_experiment_history": [{"failure": "previous" * 120} for _ in range(5)],
            },
            advisor_only=True,
        )

    def test_attested_bounded_witness_survives_prompt_context_shrinking(self):
        request = self.request()
        witness = _source_contract_prompt_witness(request)
        self.assertEqual(witness["seasonHtmlShape"], "catalogue_inline_token_episode")
        self.assertEqual(witness["catalogueSlugUnverified"], "mushoku-tensei")
        self.assertEqual(witness["observedOriginHostUnverified"], "anime-sama.to")
        self.assertEqual(witness["legacyJsStatus"], 403)
        self.assertEqual(witness["tokenResolverStatus"], 200)
        self.assertEqual(witness["tokenResolverContract"], "same-origin-api-lien-j-l-v1")
        self.assertTrue(witness["tokenResolverHttpsUrlObserved"])
        self.assertEqual(witness["resolvedTargetShape"], "html_player")
        self.assertEqual(witness["resolvedTargetPlayerStructureClass"], "mixed")
        self.assertEqual(witness["resolvedTargetIframeCount"], 1)
        self.assertEqual(witness["resolvedTargetFormCount"], 1)
        self.assertEqual(witness["resolvedTargetHiddenInputCount"], 2)
        self.assertEqual(witness["resolvedTargetRequestCallCount"], 4)
        self.assertEqual(witness["resolvedTargetRequestDynamicUrlCount"], 2)
        self.assertEqual(witness["resolvedTargetRequestIdentifierUrlCount"], 1)
        self.assertEqual(witness["resolvedTargetRequestCrossOriginLiteralCount"], 1)
        self.assertEqual(witness["resolvedTargetRequestStaticCandidateCount"], 2)
        self.assertEqual(witness["resolvedTargetRequestStaticSameOriginMediaIntentCount"], 0)
        self.assertTrue(witness["resolvedTargetPostFormObserved"])
        self.assertTrue(witness["resolvedTargetRequestBootstrapObserved"])
        self.assertTrue(witness["resolvedTargetBase64DecodeObserved"])
        self.assertFalse(witness["sourceContractVerifiedOnOfficialTv"])
        payload = build_prompt_payload(
            request, experiences=[], documents=[],
            causal_prior={"confidence": 0.91, "target_layer": "unknown"},
            mutation_policy={"allow_mutations": False, "allowed_scopes": []},
        )
        self.assertEqual(payload["source_contract_witness"], witness)
        self.assertLessEqual(payload["context_budget"]["serialized_user_chars"], 7600)
        self.assertFalse(payload["mutation_policy"]["allow_mutations"])
        for forbidden in ("PRIVATE", "SECRET.invalid", "https://"):
            self.assertNotIn(forbidden, json.dumps(payload["source_contract_witness"]))
        for flag in (
            "proofAuthority", "publicationAuthority",
            "nativePlaybackAuthority", "providerMutationAuthority",
        ):
            self.assertIs(payload["source_contract_witness"][flag], False)

    def test_unattested_or_forged_source_cannot_claim_prompt_witness(self):
        original = self.request()
        for variant in (
            "no_parent", "wrong_parent_run", "wrong_parent_digest",
            "false_app", "unselected", "forged_authority", "fake_shape",
            "wrong_client", "wrong_slug", "wrong_origin", "unsafe_player_structure",
        ):
            with self.subTest(variant=variant):
                req = copy.deepcopy(original)
                native = req.observations[1]["value"]
                probe = req.observations[2]["value"]
                if variant == "no_parent":
                    req.observations.pop(1)
                elif variant == "wrong_parent_run":
                    probe["nativeParentRunId"] = "44781039915"
                elif variant == "wrong_parent_digest":
                    probe["currentProviderArtifactSha256"] = "f" * 64
                elif variant == "false_app":
                    native["appSelected"] = False
                elif variant == "unselected":
                    native["readerEvidenceComplete"] = False
                elif variant == "forged_authority":
                    probe["publicationAuthority"] = True
                elif variant == "fake_shape":
                    probe["sourceObservations"][0]["seasonSourceShape"] = "unknown_response_shape"
                elif variant == "wrong_client":
                    native["client"] = "desktop"
                elif variant == "wrong_slug":
                    probe["catalogueSlugUnverified"] = "../secret"
                elif variant == "wrong_origin":
                    probe["sourceObservations"][0]["originHost"] = "https://bad.invalid/"
                elif variant == "unsafe_player_structure":
                    probe["sourceObservations"][0]["resolvedTargetIframeCount"] = 99
                witness = _source_contract_prompt_witness(req)
                if variant == "unsafe_player_structure":
                    self.assertTrue(witness)
                    self.assertNotIn("resolvedTargetShape", witness)
                    self.assertNotIn("resolvedTargetPlayerStructureClass", witness)
                else:
                    self.assertEqual(witness, {})
                payload = build_prompt_payload(
                    req, experiences=[], documents=[],
                    causal_prior={"confidence": 0.91},
                    mutation_policy={"allow_mutations": False},
                )
                if variant == "unsafe_player_structure":
                    self.assertIn("source_contract_witness", payload)
                    self.assertNotIn(
                        "resolvedTargetPlayerStructureClass",
                        payload["source_contract_witness"],
                    )
                else:
                    self.assertNotIn("source_contract_witness", payload)


if __name__ == "__main__":
    unittest.main()
