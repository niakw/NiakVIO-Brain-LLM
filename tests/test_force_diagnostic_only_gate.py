"""FORCE may not synthesize provider edits when native evidence demands diagnosis."""
import unittest
from pathlib import Path

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.force_scope_order import diagnostic_only_route
from niakvio_brain_llm.routing import RoutingDecision, route_request


class ForceDiagnosisBoundaryTests(unittest.TestCase):
    def tv(self, **changes):
        base = {
            "source": "official-android-tv-emulator",
            "client": "tv",
            "appSelected": True,
            "historicalOnly": True,
            "nativeExtractionPositiveObserved": True,
            "nativeExtractionReturnedCount": 2,
            "playerVideoFormatUnverified": True,
            "independentTerminalHttpStatuses": [403],
            "proofAuthority": False,
            "publicationAuthority": False,
            "nativePlaybackAuthority": False,
            "providerMutationAuthority": False,
        }
        base.update(changes)
        return RepairRequest(
            provider_id="french-manga",
            failure_class="candidate_replay_gap",
            status="CANDIDATE OK",
            allowed_mutations=["provider_patch", "provider_bloc"],
            observations=[{"source": "official-android-tv-emulator", "value": base}],
        )

    def test_real_tv_extraction_403_never_targets_provider_mutation(self):
        decision = route_request(self.tv())
        self.assertEqual(decision.mode, "llm_diagnose")
        self.assertEqual(decision.target_layer, "unknown")
        self.assertEqual(decision.strategy, "trace_tv_hls_403_headers_client_fetch_and_decoded_video")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, [])
        self.assertTrue(diagnostic_only_route(decision))

    def test_native_timeout_is_diagnosis_not_repair(self):
        request = self.tv(
            nativeExtractionPositiveObserved=False,
            nativeExtractionReturnedCount=0,
            independentTerminalHttpStatuses=[],
            nativeHardTimeoutObserved=True,
            nativeHardTimeoutMs=25000,
        )
        decision = route_request(request)
        self.assertEqual(decision.mode, "llm_diagnose")
        self.assertEqual(decision.strategy, "discriminate_tv_native_hard_timeout_owner")
        self.assertTrue(diagnostic_only_route(decision))

    def test_no_synthesis_for_unproven_or_forged_mutation_permission(self):
        self.assertFalse(diagnostic_only_route(RoutingDecision(
            mode="llm_repair", strategy="confirmed_provider_fix",
            requires_llm=True, allowed_mutations=["provider_patch"],
        )))
        with self.assertRaises(ValueError):
            diagnostic_only_route(RoutingDecision(
                mode="llm_diagnose", strategy="contradictory",
                requires_llm=True, allowed_mutations=["provider_js"],
            ))
        self.assertFalse(diagnostic_only_route(RoutingDecision(mode="probe")))

    def test_force_entrypoint_short_circuits_before_scope_portfolio(self):
        source = (Path(__file__).resolve().parents[1] /
                  "scripts/plan_batch_from_checkout.py").read_text("utf-8")
        block = source[source.index('if args.mode == "repair" and not args.advisor_only:'):]
        self.assertLess(block.index("if diagnostic_only_route(causal_route):"),
                        block.index("scopes = _force_scope_order(request)"))
        self.assertIn("orchestrator.run(request, compact_force=False)", block)
        self.assertIn("result[\"diagnostic_only\"] = True", block)
        self.assertIn('"provider_mutation_authority": False', block)


if __name__ == "__main__":
    unittest.main()
