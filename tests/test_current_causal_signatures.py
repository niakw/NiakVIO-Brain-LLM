"""Sanitized, per-family live observation signatures; no bypass of playback."""
from __future__ import annotations
import json
import unittest

from niakvio_brain_llm.current_evidence import current_causal_signatures
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import build_force_prompt_payload


class CausalSignaturesContract(unittest.TestCase):
    def test_graphql_200_is_not_success_and_never_copies_payloads(self):
        live = {
            "fixture_evidence": [{"fixture": "PRIVATE_NAME", "streamsPlayable": 0}],
            "network_evidence": [{
                "host": "private.example", "status": 200, "stage": "episode",
                "response_structure": {"kind": "json", "graphql": {
                    "errorCount": 1, "dataState": "null",
                    "codes": ["PRIVATE_SECRET"],
                }},
            }],
        }
        result = current_causal_signatures(live)
        self.assertIn("graphql_response_errors", result["signals"])
        self.assertIn("graphql_null_result", result["signals"])
        self.assertFalse(result["proof_authority"])
        self.assertFalse(result["media_identity_verified"])
        self.assertNotIn("PRIVATE", json.dumps(result))
        request = RepairRequest(
            provider_id="demo", failure_class="chain_terminal_gap",
            allowed_mutations=["provider_bloc"],
            provider_context={
                "runtimeMutationSource": "function resolve(){return source();}",
                "runtimeMutationFilename": "providers/demo.js",
                "live_runtime_evidence": live,
            },
        )
        prompt = build_force_prompt_payload(
            request, {}, {"allowed_scopes": ["provider_bloc"], "allow_mutations": True},
        )
        self.assertIn("graphql_response_errors", prompt["current_causal_signatures"]["signals"])

    def test_html_player_and_api_transport_are_separate_failure_families(self):
        html = current_causal_signatures({
            "fixture_evidence": [{"streamsPlayable": 0}],
            "network_evidence": [
                {"stage": "player", "status": 200, "announced_players": 3,
                 "response_structure": {"kind": "html"}}
            ],
        })
        self.assertEqual(html["signals"], ["announced_player_unresolved"])
        blocked = current_causal_signatures({
            "fixture_evidence": [{"streamsPlayable": 0}],
            "network_evidence": [
                {"stage": "search", "status": 403,
                 "response_structure": {"kind": "html"}}
            ],
        })
        self.assertEqual(blocked["signals"], ["http_origin_rejection_or_throttle"])
        self.assertIn("separate_waf_transport_from_provider_parse", blocked["next_evidence"])

    def test_no_request_is_not_network_transport_and_raw_data_never_proves_media(self):
        zero = current_causal_signatures({
            "fixture_evidence": [{"streamsPlayable": 0}], "network_evidence": [],
        })
        self.assertEqual(zero["signals"], ["no_observed_provider_network"])
        self.assertEqual(zero["next_evidence"],
                         ["compare_exact_bytes_deep_vs_nuvio_invocation"])
        media = current_causal_signatures({
            "fixture_evidence": [{"streamsPlayable": 0}],
            "network_evidence": [
                {"stage": "media", "status": 206,
                 "media_observation": {"signature": "mp4", "durationSeconds": 4,
                                       "url": "https://PRIVATE.example/?token=PRIVATE"},
                 "response_structure": {"kind": "binary"}}
            ],
        })
        self.assertIn("terminal_media_observed_but_unverified", media["signals"])
        self.assertFalse(media["media_identity_verified"])
        self.assertNotIn("PRIVATE", json.dumps(media))

    def test_no_fake_failure_when_playback_or_evidence_missing(self):
        self.assertEqual(current_causal_signatures({})["signals"], [])
        success = current_causal_signatures({
            "fixture_evidence": [{"streamsPlayable": 1}],
            "network_evidence": [{"stage": "player", "status": 200,
                                  "response_structure": {"kind": "html"}}],
        })
        self.assertEqual(success["signals"], [])


if __name__ == "__main__":
    unittest.main()
