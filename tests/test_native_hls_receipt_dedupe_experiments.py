"""V31 Brain chooses a different generic Core tactic only after exact V30 zero."""
from __future__ import annotations

import json

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.native_hls_receipt_experiments import native_hls_root_receipt_experiment
from niakvio_brain_llm.native_hls_receipt_dedupe_experiments import native_hls_receipt_dedupe_experiment, native_hls_receipt_dedupe_positive_result
from niakvio_brain_llm.routing import route_request


def example():
    s, digest, client = "a"*40, "b"*64, "c"*40
    observation = {
        "source": "official-android-tv-emulator",
        "value": {
            "appSelected": True, "nativeExtractionZeroObserved": True,
            "sameMediaRootSuccessThenForbidden": True,
            "hlsPlaylist2xxNearProviderBudgetZeroObserved": True,
            "tvPromiseControl": "bridge_ok", "nativeHardTimeoutObserved": False,
            "historicalOnly": True, "sourceNiakvioSha": s,
            "providerArtifactSha256": digest, "sourceRunId": "44669003629",
            "officialClientSha": client,
            "fixture": "jujutsu-kaisen-s01e01", "requestType": "anime",
            "nativePrePlayerHostOutcomes": [
                {"kind": "player-page", "sequence": 4, "host": "failed.example", "httpStatus": 522},
                {"kind": "player-page", "sequence": 5, "host": "good.example", "httpStatus": 200},
                {"kind": "hls", "sequence": 6, "host": "", "httpStatus": 200},
            ],
            "proofAuthority": False, "publicationAuthority": False,
            "nativePlaybackAuthority": False, "providerMutationAuthority": False,
        }
    }
    parent = {
        "providerId": "french-manga", "providerArtifactSha256": digest,
        "runtimeScope": "native-blocking-fetch",
        "preferredHosts": ["good.example"], "deprioritizedHosts": ["failed.example"],
        "evidencePattern": "player-5xx-then-alternate-2xx-then-hls-2xx-near-budget-zero",
        "candidateOnly": True, "generatedByBrain": True,
        "proofAuthority": False, "publicationAuthority": False,
        "nativePlaybackAuthority": False, "providerMutationAuthority": False,
        "candidateAttempts": [{
            "candidateRunId": "44671941015",
            "candidateSourceSha": "d"*40, "candidateJsSha256": "e"*64,
            "candidateVerdict": "candidate_zero_stream",
            "candidateExecutionObserved": True, "candidateRestoredObserved": True,
            "candidateDecodedVideoObserved": False, "validatedRepair": False,
            "publicationAllowed": False,
        }],
    }
    request = RepairRequest(
        provider_id="french-manga", status="CANDIDATE OK",
        failure_class="candidate_replay_gap", advisor_only=True,
        observations=[observation],
        provider_context={"native_candidate_experiment_history": [parent]},
    )
    v30 = native_hls_root_receipt_experiment(request)
    assert v30["experimentType"] == "native-hls-master-receipt-v30"
    parent["candidateFollowUpExperimentFingerprints"] = [v30["experimentFingerprint"]]
    parent["executedHlsReceiptFollowups"] = [{
        "experimentType": "native-hls-master-receipt-v30",
        "experimentFingerprint": v30["experimentFingerprint"],
        "priorCandidateRunId": "44671941015",
        "priorCandidateSourceSha": "d"*40, "priorCandidateJsSha256": "e"*64,
        "candidateAttempts": [{
            "candidateExperimentType": "native-hls-master-receipt-v30",
            "candidateRunId": "44710894643",
            "candidateSourceSha": "f"*40,
            "candidateJsSha256": "1"*64,
            "candidateVerdict": "candidate_zero_stream",
            "candidateExecutionObserved": True, "candidateRestoredObserved": True,
            "candidateDecodedVideoObserved": False, "validatedRepair": False,
            "publicationAllowed": False,
        }],
    }]
    parent["candidateV31ExperimentFingerprints"] = []
    return request, parent, observation


def test_v31_source_pinned_negative_and_no_repeat():
    request, parent, obs = example()
    generated = native_hls_receipt_dedupe_experiment(request)
    assert generated["experimentType"] == "native-hls-master-receipt-dedupe-v31"
    assert generated["priorCandidateRunId"] == "44710894643"
    assert generated["priorCandidateJsSha256"] == "1"*64
    assert generated["parentExperimentFingerprint"] == parent["executedHlsReceiptFollowups"][0]["experimentFingerprint"]
    assert generated == native_hls_receipt_dedupe_experiment(request)
    assert generated["candidateOnly"] is True
    assert generated["generatedByBrain"] is True
    assert generated["modelExecuted"] is False
    assert generated["publicationAuthority"] is False
    assert not any(token in json.dumps(generated) for token in (
        "https://", "good.example", "failed.example", "cookie", "token=", "Authorization"
    ))
    route = route_request(request)
    assert route.target_layer == "core"
    assert route.strategy == "preserve_hls_receipt_across_playback_key_dedupe"
    assert route.allowed_mutations == []
    parent["candidateV31ExperimentFingerprints"] = [generated["experimentFingerprint"]]
    assert not native_hls_receipt_dedupe_experiment(request)
    parent["candidateV31ExperimentFingerprints"] = []
    parent["executedHlsReceiptFollowups"][0]["candidateAttempts"][0]["candidateRestoredObserved"] = False
    assert not native_hls_receipt_dedupe_experiment(request)
    parent["executedHlsReceiptFollowups"][0]["candidateAttempts"][0]["candidateRestoredObserved"] = True
    parent["executedHlsReceiptFollowups"][0]["candidateAttempts"][0]["candidateVerdict"] = "candidate_terminal_decode_observed"
    assert not native_hls_receipt_dedupe_experiment(request)
    parent["executedHlsReceiptFollowups"][0]["candidateAttempts"][0]["candidateVerdict"] = "candidate_zero_stream"
    obs["value"]["sameMediaRootSuccessThenForbidden"] = False
    assert not native_hls_receipt_dedupe_experiment(request)
    obs["value"]["sameMediaRootSuccessThenForbidden"] = True
    obs["value"]["officialClientSha"] = "9"*40
    assert not native_hls_receipt_dedupe_experiment(request)


def test_v31_does_not_trigger_without_v30():
    request, parent, obs = example()
    parent["executedHlsReceiptFollowups"] = []
    assert not native_hls_receipt_dedupe_experiment(request)
    assert route_request(request).strategy != "preserve_hls_receipt_across_playback_key_dedupe"


def test_v31_decoded_candidate_routes_to_evidence_not_replaying_v30():
    request, parent, observed = example()
    plan = native_hls_receipt_dedupe_experiment(request)
    parent["candidateV31ExperimentFingerprints"] = [plan["experimentFingerprint"]]
    a30 = parent["executedHlsReceiptFollowups"][0]["candidateAttempts"][0]
    good = {
        "candidateExperimentType": "native-hls-master-receipt-dedupe-v31",
        "candidateRunId": "44753273273",
        "candidateSourceSha": "2"*40,
        "candidateJsSha256": "3"*64,
        "candidateRuntimeReturnedCount": 2,
        "candidateVerdict": "candidate_terminal_decode_observed",
        "candidateExecutionObserved": True,
        "candidateRestoredObserved": True,
        "candidateExtractionNonEmpty": True,
        "candidateTerminalReaderHealthy": True,
        "candidateDecodedVideoObserved": True,
        "candidateFrAudioObserved": False,
        "validatedRepair": False,
        "publicationAllowed": False,
    }
    follow = {
        "experimentType": plan["experimentType"],
        "experimentFingerprint": plan["experimentFingerprint"],
        "parentExperimentFingerprint": plan["parentExperimentFingerprint"],
        "sourceNiakvioSha": plan["sourceNiakvioSha"],
        "sourceRunId": str(plan["sourceRunId"]),
        "officialClientSha": plan["officialClientSha"],
        "fixture": plan["fixture"],
        "requestType": plan["requestType"],
        "priorCandidateRunId": str(a30["candidateRunId"]),
        "priorCandidateSourceSha": a30["candidateSourceSha"],
        "priorCandidateJsSha256": a30["candidateJsSha256"],
        "candidateAttempts": [good],
    }
    parent["executedHlsDedupeFollowups"] = [follow]
    result = native_hls_receipt_dedupe_positive_result(request)
    assert result["candidateRunId"] == "44753273273"
    assert result["candidateRuntimeReturnedCount"] == 2
    assert result["candidateFrAudioObserved"] is False
    assert result["validatedRepair"] is False
    assert result["publicationAllowed"] is False
    assert native_hls_receipt_dedupe_experiment(request) == {}
    route = route_request(request)
    assert route.mode == "deterministic_advisor"
    assert route.target_layer == "core"
    assert route.strategy == "verify_hls_receipt_dedupe_visual_audio_family_before_promotion"
    assert route.allowed_mutations == []
    assert not route.requires_llm
    assert "correct episode" in " ".join(route.next_actions)
    # The full positive path is fail-closed across every authority boundary.
    for key,bad in (
        ("candidateRestoredObserved", False),
        ("candidateExecutionObserved", False),
        ("candidateExtractionNonEmpty", False),
        ("candidateTerminalReaderHealthy", False),
        ("candidateDecodedVideoObserved", False),
        ("candidateRuntimeReturnedCount", 0),
        ("candidateVerdict", "candidate_zero_stream"),
        ("publicationAllowed", True),
        ("validatedRepair", True),
        ("candidateSourceSha", "bogus"),
        ("candidateJsSha256", "bad"),
    ):
        old=good[key]
        good[key]=bad
        assert native_hls_receipt_dedupe_positive_result(request) == {}, key
        assert route_request(request).strategy != "verify_hls_receipt_dedupe_visual_audio_family_before_promotion", key
        good[key]=old
    old=follow["priorCandidateJsSha256"]
    follow["priorCandidateJsSha256"]="a"*64
    assert native_hls_receipt_dedupe_positive_result(request) == {}
    follow["priorCandidateJsSha256"]=old
    old=follow["sourceNiakvioSha"]
    follow["sourceNiakvioSha"]="1"*40
    assert native_hls_receipt_dedupe_positive_result(request) == {}
    follow["sourceNiakvioSha"]=old
    observed["value"]["sameMediaRootSuccessThenForbidden"]=False
    assert native_hls_receipt_dedupe_positive_result(request) == {}
