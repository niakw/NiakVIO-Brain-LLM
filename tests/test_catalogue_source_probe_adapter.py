"""Source-pinned independent catalogue probe is Brain evidence, not media proof."""
import copy
import json
import unittest

from niakvio_brain_llm.niakvio_adapter import (
    _provider_catalogue_source_probe_observations,
    _refine_failure_from_catalogue_source_targets,
)


class CatalogueSourceProbeAdapterTests(unittest.TestCase):
    digest = "9e917c77" + "a" * 56
    native_sha = "e7c7c920" + "b" * 32
    probe_sha = "6bacd084" + "c" * 32
    native_run = "44781039914"
    probe_run = "44798438960"

    def native(self):
        return [{
            "client": "tv",
            "historicalOnly": True,
            "appSelected": True,
            "readerEvidenceComplete": True,
            "nativeExtractionZeroObserved": True,
            "sourceRunId": self.native_run,
            "sourceNiakvioSha": self.native_sha,
            "providerArtifactSha256": self.digest,
            "manifestScope": "manifest.json",
            "fixture": "mushoku-tensei-s01e01",
            "nativeSourceScriptShapePatterns": [
                "script_http_missing", "script_html_2xx",
            ],
            "proofAuthority": False,
            "publicationAuthority": False,
            "nativePlaybackAuthority": False,
            "providerMutationAuthority": False,
        }]

    def ledger(self):
        row = {
            "providerId": "anime-sama",
            "fixture": "mushoku-tensei-s01e01",
            "parentNativeRunId": self.native_run,
            "parentNativeNiakvioSha": self.native_sha,
            "parentNativeProviderArtifactSha256": self.digest,
            "latestProbeRunId": self.probe_run,
            "latestProbeSourceSha": self.probe_sha,
            "inputCatalogueSlug": "",
            "candidateNextSlug": "mushoku-tensei",
            "manifestScope": "manifest.json",
            "probeRequestCount": 13,
            "inlineTokenResponseCount": 1,
            "tokenResolverProbeCount": 1,
            "tokenResolverJsonUrlCount": 1,
            "leadHypothesis": "catalogue_inline_token_resolver_observed_unverified",
            "independentNetworkNotOfficialClient": True,
            "sourceContractVerifiedOnOfficialTv": False,
            "catalogueIdentityVerified": False,
            "episodeIdentityVerified": False,
            "candidateMutationAllowed": False,
            "generatedByBrain": False,
            "modelExecuted": False,
            "validatedRepair": False,
            "publicationAllowed": False,
            "proofAuthority": False,
            "publicationAuthority": False,
            "nativePlaybackAuthority": False,
            "providerMutationAuthority": False,
            "evidence": [
                {
                    "originHost": "anime-sama.to",
                    "catalogueStatus": 200,
                    "seasonPageStatus": 200,
                    "seasonSourceShape": "catalogue_inline_token_episode",
                    "legacyScriptStatus": 403,
                    "searchStatus": 200,
                    "searchLinkCount": 2,
                    "tokenResolverStatus": 200,
                    "tokenResolverContract": "same-origin-api-lien-j-l-v1",
                    "tokenResolverJsonObjectObserved": True,
                    "tokenResolverUrlFieldObserved": True,
                    "tokenResolverHttpsUrlObserved": True,
                    "rawHtml": "PRIVATE token",
                    "videoUrl": "https://secrets.invalid/private?auth=PRIVATE",
                },
                {
                    "originHost": "animes-sama.fr",
                    "catalogueStatus": 200,
                    "seasonPageStatus": 200,
                    "seasonSourceShape": "script_html_2xx",
                    "legacyScriptStatus": 404,
                    "searchStatus": 200,
                    "searchLinkCount": 1,
                },
            ],
            "rawHtml": "PRIVATE epsJeton",
            "signedUrl": "https://secrets.invalid/?PRIVATE=1",
        }
        return {
            "schemaVersion": 1,
            "authority": "independent-ci-source-shape-diagnostic-only",
            "primaryClient": "independent-github-runner-not-official-android-tv",
            "proofAuthority": False,
            "publicationAuthority": False,
            "nativePlaybackAuthority": False,
            "providerMutationAuthority": False,
            "rows": [row],
        }

    def project(self, ledger=None, native=None, digest=None, scopes=None):
        return _provider_catalogue_source_probe_observations(
            self.ledger() if ledger is None else ledger,
            "anime-sama",
            current_bundle_sha256=self.digest if digest is None else digest,
            active_manifest_scopes=["manifest.json"] if scopes is None else scopes,
            official_tv_observations=self.native() if native is None else native,
        )

    def test_exact_parent_attestation_preserves_only_bounded_source_shape(self):
        output = self.project()
        self.assertEqual(len(output), 1)
        value = output[0]
        self.assertEqual(value["source"], "independent-ci-source-shape")
        self.assertEqual(value["nativeParentRunId"], self.native_run)
        self.assertEqual(value["probeRunId"], self.probe_run)
        self.assertEqual(value["catalogueSlugUnverified"], "mushoku-tensei")
        self.assertEqual(value["inputCatalogueSlugUnverified"], "")
        self.assertEqual(value["candidateNextSlugUnverified"], "mushoku-tensei")
        self.assertEqual(value["inlineTokenResponseCount"], 1)
        self.assertTrue(value["sourceObservations"][0]["inlineTokenSeasonObserved"])
        self.assertEqual(value["tokenResolverProbeCount"], 1)
        self.assertEqual(value["tokenResolverJsonUrlCount"], 1)
        self.assertEqual(
            value["sourceObservations"][0]["tokenResolverContract"],
            "same-origin-api-lien-j-l-v1",
        )
        self.assertTrue(value["sourceObservations"][0]["tokenResolverHttpsUrlObserved"])
        self.assertEqual(value["sourceObservations"][1]["seasonSourceShape"], "script_html_2xx")
        self.assertTrue(value["historicalOnly"])
        self.assertTrue(value["independentNetworkNotOfficialClient"])
        for key in (
            "catalogueIdentityVerified", "episodeIdentityVerified",
            "sourceContractVerifiedOnOfficialTv",
            "proofAuthority", "publicationAuthority",
            "nativePlaybackAuthority", "providerMutationAuthority",
        ):
            self.assertIs(value[key], False)
        for private in ("PRIVATE", "signedUrl", "videoUrl", "https://", "epsJeton"):
            self.assertNotIn(private, json.dumps(output))


    def test_html_player_target_refines_only_provider_local_gap(self):
        ledger = self.ledger()
        row = ledger["rows"][0]
        row["probeRequestCount"] = 14
        row["resolvedTargetProbeCount"] = 1
        row["resolvedTargetDirectMediaCount"] = 0
        row["resolvedTargetPlayerPageCount"] = 1
        row["leadHypothesis"] = "catalogue_inline_token_player_target_observed_unresolved"
        row["evidence"][0].update({
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
            "resolvedTargetRequestSameOriginLiteralCount": 1,
            "resolvedTargetRequestCrossOriginLiteralCount": 1,
            "resolvedTargetPostFormObserved": True,
            "resolvedTargetRequestBootstrapObserved": True,
            "resolvedTargetPackedScriptObserved": False,
            "resolvedTargetBase64DecodeObserved": True,
            "resolvedTargetMetaRefreshObserved": False,
        })
        projected = self.project(ledger=ledger)
        self.assertEqual(len(projected), 1)
        player = projected[0]["sourceObservations"][0]
        self.assertEqual(player["resolvedTargetPlayerStructureClass"], "mixed")
        self.assertEqual(player["resolvedTargetIframeCount"], 1)
        self.assertEqual(player["resolvedTargetFormCount"], 1)
        self.assertEqual(player["resolvedTargetHiddenInputCount"], 2)
        self.assertEqual(player["resolvedTargetRequestCallCount"], 4)
        self.assertEqual(player["resolvedTargetRequestDynamicUrlCount"], 2)
        self.assertEqual(player["resolvedTargetRequestCrossOriginLiteralCount"], 1)
        self.assertTrue(player["resolvedTargetRequestBootstrapObserved"])
        self.assertTrue(player["resolvedTargetBase64DecodeObserved"])
        self.assertEqual(
            _refine_failure_from_catalogue_source_targets(
                "chain_terminal_gap", projected
            ),
            "media_extraction_gap",
        )
        self.assertEqual(
            _refine_failure_from_catalogue_source_targets(
                "provider_zero_before_provider_network", projected
            ),
            "media_extraction_gap",
        )
        # Independent source shape is never allowed to override a real
        # transport/environment owner.
        self.assertEqual(
            _refine_failure_from_catalogue_source_targets(
                "transport_environment_gap", projected
            ),
            "transport_environment_gap",
        )
        forged = copy.deepcopy(projected)
        forged[0]["providerMutationAuthority"] = True
        self.assertEqual(
            _refine_failure_from_catalogue_source_targets(
                "chain_terminal_gap", forged
            ),
            "chain_terminal_gap",
        )
        unsafe = self.ledger()
        unsafe_row = unsafe["rows"][0]
        unsafe_row.update({
            "probeRequestCount": 14,
            "resolvedTargetProbeCount": 1,
            "resolvedTargetDirectMediaCount": 0,
            "resolvedTargetPlayerPageCount": 1,
            "leadHypothesis": "catalogue_inline_token_player_target_observed_unresolved",
        })
        unsafe_row["evidence"][0].update(row["evidence"][0])
        unsafe_row["evidence"][0]["resolvedTargetIframeCount"] = 99
        unsafe_projected = self.project(ledger=unsafe)
        self.assertEqual(len(unsafe_projected), 1)
        self.assertFalse(any(
            source.get("resolvedTargetShape") == "html_player"
            for source in unsafe_projected[0]["sourceObservations"]
        ))
        self.assertEqual(
            _refine_failure_from_catalogue_source_targets(
                "chain_terminal_gap", unsafe_projected
            ),
            "chain_terminal_gap",
        )

    def test_old_and_new_run_both_remain_visible_not_mutation(self):
        ledger = self.ledger()
        old = copy.deepcopy(ledger["rows"][0])
        old.update({
            "latestProbeRunId": "44797871788",
            "latestProbeSourceSha": "c" * 40,
            "inputCatalogueSlug": "mushoku-tensei-jobless-reincarnation",
            "probeRequestCount": 12,
            "inlineTokenResponseCount": 0,
            "leadHypothesis": "catalogue_search_slug_mismatch_unverified",
            "evidence": [{
                "originHost": "anime-sama.to",
                "catalogueStatus": 404,
                "seasonPageStatus": 404,
                "legacyScriptStatus": 403,
                "searchStatus": 200,
            }],
        })
        ledger["rows"].insert(0, old)
        values = self.project(ledger=ledger)
        self.assertEqual([x["probeRunId"] for x in values],
                         [self.probe_run, "44797871788"])
        self.assertEqual([x["inlineTokenResponseCount"] for x in values],
                         [1, 0])
        self.assertTrue(all(x["providerMutationAuthority"] is False for x in values))

    def test_no_exact_official_tv_parent_no_observation(self):
        for changed in (
            {"appSelected": False}, {"readerEvidenceComplete": False},
            {"historicalOnly": False}, {"nativeExtractionZeroObserved": False},
            {"sourceRunId": "44781039915"},
            {"providerArtifactSha256": "f" * 64},
            {"manifestScope": "vf/manifest.json"},
            {"providerMutationAuthority": True},
            {"nativeSourceScriptShapePatterns": ["other"]},
        ):
            with self.subTest(changed=changed):
                native = [{**self.native()[0], **changed}]
                self.assertEqual(self.project(native=native), [])
        self.assertEqual(self.project(native=[]), [])

    def test_stale_or_forged_ci_evidence_never_enters_brain(self):
        base = self.ledger()
        corruptions = [
            ("envelope", "authority", "certified"),
            ("envelope", "publicationAuthority", True),
            ("row", "providerId", "someone-else"),
            ("row", "parentNativeNiakvioSha", "0" * 40),
            ("row", "parentNativeRunId", "44781039915"),
            ("row", "parentNativeProviderArtifactSha256", "f" * 64),
            ("row", "latestProbeSourceSha", "bad"),
            ("row", "fixture", "../outside"),
            ("row", "inputCatalogueSlug", "../outside"),
            ("row", "sourceContractVerifiedOnOfficialTv", True),
            ("row", "candidateMutationAllowed", True),
            ("row", "validatedRepair", True),
            ("row", "generatedByBrain", True),
            ("row", "modelExecuted", True),
            ("row", "nativePlaybackAuthority", True),
            ("row", "catalogueIdentityVerified", True),
            ("row", "inlineTokenResponseCount", 19),
            ("row", "probeRequestCount", 19),
        ]
        for part, key, val in corruptions:
            with self.subTest(field=key):
                ledger = copy.deepcopy(base)
                target = ledger if part == "envelope" else ledger["rows"][0]
                target[key] = val
                self.assertEqual(self.project(ledger=ledger), [])
        self.assertEqual(self.project(digest="0" * 64), [])
        self.assertEqual(self.project(scopes=["vf/manifest.json"]), [])
        invalid = copy.deepcopy(base)
        invalid["rows"][0]["evidence"] = [{
            "originHost": "https://private.invalid/?PRIVATE=1",
            "catalogueStatus": 200,
        }]
        self.assertEqual(self.project(ledger=invalid), [])


if __name__ == "__main__":
    unittest.main()
