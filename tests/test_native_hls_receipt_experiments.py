"""Brain V30 receipt experiment must require exact native negative and HLS evidence."""
from __future__ import annotations

import json

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.native_hls_receipt_experiments import native_hls_root_receipt_experiment


def request():
    source, digest = "a" * 40, "b" * 64
    obs = {
        "source": "official-android-tv-emulator",
        "appSelected": True,
        "nativeExtractionZeroObserved": True,
        "sameMediaRootSuccessThenForbidden": True,
        "hlsPlaylist2xxNearProviderBudgetZeroObserved": True,
        "tvPromiseControl": "bridge_ok",
        "nativeHardTimeoutObserved": False,
        "historicalOnly": True,
        "sourceNiakvioSha": source,
        "providerArtifactSha256": digest,
        "sourceRunId": "44669003629",
        "officialClientSha": "c" * 40,
        "fixture": "jujutsu-kaisen-s01e01",
        "requestType": "anime",
        "nativePrePlayerHostOutcomes": [
            {"kind": "player-page", "sequence": 4, "host": "vidzy.live", "httpStatus": 522},
            {"kind": "player-page", "sequence": 5, "host": "lplaygo.com", "httpStatus": 200},
            {"kind": "hls", "sequence": 6, "host": "", "httpStatus": 200},
            {"kind": "hls", "sequence": 11, "host": "", "httpStatus": 403},
        ],
        "proofAuthority": False,
        "publicationAuthority": False,
        "nativePlaybackAuthority": False,
        "providerMutationAuthority": False,
    }
    prior = {
        "providerId": "french-manga",
        "providerArtifactSha256": digest,
        "runtimeScope": "native-blocking-fetch",
        "preferredHosts": ["lplaygo.com"],
        "deprioritizedHosts": ["vidzy.live"],
        "evidencePattern": "player-5xx-then-alternate-2xx-then-hls-2xx-near-budget-zero",
        "candidateOnly": True,
        "generatedByBrain": True,
        "proofAuthority": False,
        "publicationAuthority": False,
        "nativePlaybackAuthority": False,
        "providerMutationAuthority": False,
        "candidateAttempts": [{
            "candidateRunId": "44671941015",
            "candidateSourceSha": "d" * 40,
            "candidateJsSha256": "e" * 64,
            "candidateExecutionObserved": True,
            "candidateRuntimeReturnedCount": 0,
            "candidateRestoredObserved": True,
            "candidateExtractionNonEmpty": False,
            "candidateTerminalReaderHealthy": False,
            "candidateDecodedVideoObserved": False,
            "candidateFrAudioObserved": False,
            "candidateVerdict": "candidate_zero_stream",
            "validatedRepair": False,
            "publicationAllowed": False,
        }],
    }
    req = RepairRequest(
        provider_id="french-manga", status="CANDIDATE OK",
        failure_class="candidate_replay_gap",
        advisor_only=True,
        observations=[{"source": "official-android-tv-emulator", "value": obs}],
        provider_context={"native_candidate_experiment_history": [prior]},
    )
    return req, obs, prior


def test_v30_uses_exact_negative_and_original_success_then_403():
    req, obs, prior = request()
    generated = native_hls_root_receipt_experiment(req)
    assert generated["experimentType"] == "native-hls-master-receipt-v30"
    assert generated["providerId"] == "french-manga"
    assert generated["priorCandidateRunId"] == "44671941015"
    assert generated["priorCandidateJsSha256"] == "e" * 64
    assert generated["sourceNiakvioSha"] == "a" * 40
    assert generated["providerArtifactSha256"] == "b" * 64
    assert len(generated["experimentFingerprint"]) == 64
    assert generated == native_hls_root_receipt_experiment(req), "stable fingerprint"
    assert generated["candidateOnly"] and generated["generatedByBrain"]
    assert generated["modelExecuted"] is False
    for flag in ("proofAuthority", "publicationAuthority", "nativePlaybackAuthority", "providerMutationAuthority"):
        assert generated[flag] is False
    wire = json.dumps(generated)
    for forbidden in ("https://", "vidzy.live", "lplaygo.com", "cookie", "token=", "Authorization"):
        assert forbidden not in wire

    prior["candidateFollowUpExperimentFingerprints"] = ["f" * 64]
    assert not native_hls_root_receipt_experiment(req), "one V30 plan per source-byte family"
    prior["candidateFollowUpExperimentFingerprints"] = []
    obs["fixture"] = "unexpected-episode"
    assert not native_hls_root_receipt_experiment(req), "fixture must be source-pinned"
    obs["fixture"] = "jujutsu-kaisen-s01e01"
    obs["officialClientSha"] = "f" * 40
    assert not native_hls_root_receipt_experiment(req), "official client SHA must match"
    obs["officialClientSha"] = "c" * 40
    obs["sameMediaRootSuccessThenForbidden"] = False
    assert not native_hls_root_receipt_experiment(req), "no generic 403 inference"
    obs["sameMediaRootSuccessThenForbidden"] = True
    prior["candidateAttempts"][0]["candidateRestoredObserved"] = False
    assert not native_hls_root_receipt_experiment(req), "no un-restored execution authority"
    prior["candidateAttempts"][0]["candidateRestoredObserved"] = True
    prior["candidateAttempts"][0]["candidateExecutionObserved"] = False
    assert not native_hls_root_receipt_experiment(req), "no unexecuted candidate authority"
    prior["candidateAttempts"][0]["candidateExecutionObserved"] = True
    prior["candidateAttempts"][0]["candidateVerdict"] = "candidate_integrity_failure"
    assert not native_hls_root_receipt_experiment(req), "integrity failure is harness, not Core"


def test_v30_refuses_stale_or_forged_native_evidence():
    req, obs, prior = request()
    obs["providerArtifactSha256"] = "f" * 64
    assert not native_hls_root_receipt_experiment(req)
    obs["providerArtifactSha256"] = "b" * 64
    obs["historicalOnly"] = False
    assert not native_hls_root_receipt_experiment(req)
    obs["historicalOnly"] = True
    obs["publicationAuthority"] = True
    assert not native_hls_root_receipt_experiment(req)
    obs["publicationAuthority"] = False
    obs["nativeHardTimeoutObserved"] = True
    assert not native_hls_root_receipt_experiment(req)
    obs["nativeHardTimeoutObserved"] = False
    prior["candidateAttempts"] = []
    assert not native_hls_root_receipt_experiment(req)
