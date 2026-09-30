import json
import unittest

from niakvio_brain_llm.backend import StaticBackend
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.orchestrator import BrainOrchestrator
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.repair_family import repair_family_descriptor
from niakvio_brain_llm.retrieval import ExperienceStore


class ExplodingBackend:
    def complete(self, **kwargs):
        raise AssertionError("LLM must not be called on deterministic route")


class OrchestratorTests(unittest.TestCase):
    def test_deterministic_harness_path_never_calls_llm(self):
        planner = BrainPlanner(ExplodingBackend())
        outcome = BrainOrchestrator(planner).run(
            RepairRequest(
                provider_id="demo",
                failure_class="transport_environment_gap",
                status="HARNESS MISMATCH",
            )
        )
        self.assertEqual(outcome.routing.mode, "deterministic")
        self.assertIsNone(outcome.proposal)

    def test_probe_path_never_calls_llm(self):
        store = ExperienceStore([{
            "failure_class": "api_discovery_gap",
            "providers": ["movix"],
            "strategy": "discover_api_from_current_page_and_bundles",
        }])
        planner = BrainPlanner(ExplodingBackend(), store)
        outcome = BrainOrchestrator(planner, store).run(
            RepairRequest(
                provider_id="movix",
                failure_class="api_discovery_gap",
                provider_context={"override": "{}"},
                observations=[{"signal": "fixed endpoint 403"}],
            )
        )
        self.assertEqual(outcome.routing.mode, "probe")
        self.assertIsNone(outcome.proposal)

    def test_advisor_only_high_confidence_prior_synthesizes_without_llm(self):
        planner = BrainPlanner(ExplodingBackend())
        outcome = BrainOrchestrator(planner).run(
            RepairRequest(
                provider_id="demo",
                failure_class="route_proven_gap",
                status="ROUTE PROVEN",
                advisor_only=True,
            )
        )
        self.assertEqual(outcome.routing.mode, "deterministic_advisor")
        self.assertIsNotNone(outcome.proposal)
        self.assertEqual(
            outcome.proposal.strategy,
            "search_detail_player_terminal_traversal",
        )
        self.assertEqual(outcome.proposal.mutations, [])
        self.assertTrue(outcome.proposal.experiment)
        self.assertIn("route_policy", outcome.proposal.experiment)

    def test_advisor_negative_memory_rotates_to_new_experiment_without_llm(self):
        from niakvio_brain_llm.advisor_experiments import experiment_fingerprint, next_advisor_experiment

        initial = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            advisor_only=True,
        )
        first = next_advisor_experiment(initial, "search_detail_player_terminal_traversal")
        first_fp = experiment_fingerprint(first)
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            advisor_only=True,
            census_prior={"dominantIssue": "provider_waf_challenge"},
            provider_context={
                "advisor_experiment_history": [{
                    "profile": "proven_route_terminal_traversal_v1",
                    "llmAdvisorExperimentFingerprint": first_fp,
                    "consecutiveFailures": 1,
                    "lastOutcome": "rejected",
                    "lastReason": "provider_waf_challenge",
                }],
            },
        )
        planner = BrainPlanner(ExplodingBackend())
        outcome = BrainOrchestrator(planner).run(request)
        self.assertEqual(outcome.routing.mode, "deterministic_advisor")
        self.assertNotEqual(experiment_fingerprint(outcome.proposal.experiment), first_fp)
        self.assertTrue(outcome.proposal.experiment["session_bootstrap"])

    def test_family_replay_recompiles_without_llm(self):
        runtime = r'''function classBlocks(html,cls){var esc=cls,re=new RegExp("<div\\b[^>]*class=[\"'][^\"']*\\b"+esc+"\\b[^\"']*[\"'][^>]*>","gi"),starts=[],m;while((m=re.exec(html||""))!==null)starts.push({at:m.index,tag:m[0]});var out=[];for(var i=0;i<starts.length;i++){var end=i+1<starts.length?starts[i+1].at:Math.min(String(html||"").length,starts[i].at+12000);out.push({html:String(html||"").slice(starts[i].at,end),tag:starts[i].tag})}return out}'''
        source = (
            'MANAGED_FIX_ID="PROVIDER.DEMO.RUNTIME.V1"\n'
            'RUNTIME = r"""' + runtime + '"""\n'
        )
        request = RepairRequest(
            provider_id="demo",
            failure_class="route_proven_gap",
            status="ROUTE PROVEN",
            supported_types=["movie", "tv"],
            allowed_mutations=["provider_patch"],
            provider_context={
                "registered_patch_scripts":["scripts/provider_patches/demo_runtime_v1.py"],
                "registered_patch_sources":{"scripts/provider_patches/demo_runtime_v1.py":source},
            },
            observations=[{
                "source":"targeted-regression-current",
                "value":{
                    "debugStages":{"movie":"provider_network_zero_result"},
                    "network":{"movie":[{"status":200}]},
                    "structureHints":[
                        "movie:classes=movie-card,movie-card-format,movie-card-content;"
                        "classFacts=[movie-card;count=12;selfHref=1;nestedAnchors=24;"
                        "tags=a,div,span;signals=movie,series,year]"
                    ],
                },
            }],
        )
        family = repair_family_descriptor(request)
        store = ExperienceStore([{
            "experience_id":"family-validated",
            "failure_class":"route_proven_gap",
            "result":"validated",
            "repair_family":family,
            "mechanismFamily":"balanced-class-container",
            "strategy":"balanced-class-container",
            "successCount":2,
            "failureCount":0,
        }])
        planner = BrainPlanner(ExplodingBackend(), store)
        outcome = BrainOrchestrator(planner, store).run(request, compact_force=True)
        self.assertEqual(outcome.routing.mode, "family_replay")
        self.assertFalse(outcome.routing.requires_llm)
        self.assertIsNotNone(outcome.proposal)
        self.assertEqual(len(outcome.proposal.mutations), 1)
        self.assertIn("closeRe", outcome.proposal.mutations[0]["diff"])

    def test_llm_repair_calls_model_only_with_routed_scope(self):
        store = ExperienceStore([{
            "failure_class": "api_discovery_gap",
            "providers": ["movix"],
            "strategy": "discover_api_from_current_page_and_bundles",
        }])
        response = json.dumps({
            "provider_id": "movix",
            "diagnosis": "current API discovered from bundle",
            "strategy": "discover_api_from_current_page_and_bundles",
            "confidence": 0.96,
            "target_layer": "provider",
            "evidence": ["current bundle probe"],
            "mutations": [{
                "scope": "provider_data",
                "operation": "set",
                "path": "candidate_api_recipe.base",
                "value": "https://api.movix.fun",
            }],
            "tests": ["replay current movie fixture"],
            "abstain": False,
            "abstain_reason": "",
        })
        planner = BrainPlanner(StaticBackend(response), store)
        outcome = BrainOrchestrator(planner, store).run(
            RepairRequest(
                provider_id="movix",
                failure_class="api_discovery_gap",
                provider_context={"override": "{}"},
                observations=[{
                    "source": "current_bundle_probe",
                    "candidate_api_url": "https://api.movix.fun",
                }],
            )
        )
        self.assertEqual(outcome.routing.mode, "llm_repair")
        self.assertIsNotNone(outcome.proposal)
        self.assertEqual(
            outcome.proposal.mutations[0]["scope"],
            "provider_data",
        )


if __name__ == "__main__":
    unittest.main()
