import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.niakvio_adapter import request_from_checkout
from niakvio_brain_llm.routing import route_request


class ExactByteFrontierReuseTests(unittest.TestCase):
    def _checkout(self, parent_sha_matches=True, provider_http_status=200):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "automation").mkdir(parents=True)
        (root / "providers").mkdir(parents=True)

        provider_bytes = (
            "/* BEGIN NIAKVIO_PROVIDER */\n"
            "async function resolve(){ return []; }\n"
            "/* END NIAKVIO_PROVIDER */\n"
        ).encode("utf-8")
        provider_sha = hashlib.sha256(provider_bytes).hexdigest()
        (root / "providers" / "demo.js").write_bytes(provider_bytes)
        (root / "manifest.json").write_text(
            json.dumps({"scrapers": [{
                "id": "demo",
                "filename": "providers/demo.js",
                "enabled": True,
                "supportedTypes": ["movie"],
            }]}),
            encoding="utf-8",
        )
        (root / "provider-overrides.json").write_text("{}", encoding="utf-8")
        (root / "provider-hubs.json").write_text("{}", encoding="utf-8")
        (root / "automation" / "provider-census-status.json").write_text(
            json.dumps({"runId": "run-new", "providers": [{
                "provider": "demo",
                "status": "NO PROOF",
                "dominantIssue": "provider_network_zero_result",
                "declaredLanes": ["movie"],
                "testedThisRun": True,
            }]}),
            encoding="utf-8",
        )

        repair_sha = "b" * 64
        (root / "automation" / "provider-brain-repair-latest.json").write_text(
            json.dumps({
                "sourceCensusRunId": "run-old",
                "selectedProviders": ["demo"],
                "waves": [{"batches": [{"brain": {
                    "plans": {"published:demo": {
                        "failureClass": "media_extraction_gap",
                    }},
                    "attemptDiagnostics": [
                        {
                            "provider": "demo",
                            "phase": "attempts",
                            "status": "generated",
                            "parentSha256": provider_sha if parent_sha_matches else "a" * 64,
                            "repairSha256": repair_sha,
                        },
                        {
                            "provider": "demo",
                            "phase": "exploration_progress",
                            "reasonCode": "sandbox_diagnostic_progress",
                            "repairSha256": repair_sha,
                        },
                    ],
                }}]}],
            }),
            encoding="utf-8",
        )
        (root / "automation" / "brain-repair-memory.json").write_text(
            json.dumps({"entries": [{
                "providerId": "demo",
                "failureClass": "media_extraction_gap",
                "observedPipelineStage": "player",
                "lastOutcome": "exploration_progress_nonpublishable",
                "executionObserved": True,
            }]}),
            encoding="utf-8",
        )
        (root / "automation" / "provider-targeted-regression-recovery-latest.json").write_text(
            json.dumps({
                "sourceCensusRunId": "run-new",
                "providers": {"demo": {
                    "debugStages": {"movie": "provider_network_zero_result"},
                    "statuses": {"movie": "no_streams"},
                    "network": {"movie": [{
                        "method": "GET",
                        "host": "provider.example",
                        "path": "/search/demo",
                        "status": provider_http_status,
                        "shape": {"kind": "html", "markers": ["player"]},
                    }]},
                }},
            }),
            encoding="utf-8",
        )
        for name in (
            "brain-repair-experience.json",
            "brain-llm-force-memory.json",
            "provider-waf-browser-session-latest.json",
            "provider-repair-batch-refined-latest.json",
        ):
            (root / "automation" / name).write_text("{}", encoding="utf-8")
        return root, provider_sha

    def test_same_exact_bytes_plus_current_provider_http_reuses_frontier(self):
        root, provider_sha = self._checkout()
        request = request_from_checkout(root, "demo")
        self.assertEqual(
            request.provider_context["published_bundle"]["sha256"],
            provider_sha,
        )
        self.assertEqual(request.failure_class, "media_extraction_gap")
        current = {
            row["source"]: row["value"] for row in request.observations
        }["fast-repair-current"]
        self.assertEqual(current["sourceCensusRunId"], "run-old")
        self.assertEqual(current["currentCensusRunId"], "run-new")
        self.assertEqual(current["reuseAuthority"], "exact-byte-current-evidence")
        self.assertEqual(current["providerArtifactSha256"], provider_sha)
        self.assertEqual(current["observedPipelineStages"], ["player"])
        self.assertFalse(current["proofAuthority"])
        self.assertFalse(current["publicationAuthority"])

        decision = route_request(request)
        self.assertEqual(decision.mode, "llm_repair")
        self.assertTrue(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, ["provider_bloc"])

    def test_changed_current_bytes_reject_old_frontier(self):
        root, _ = self._checkout(parent_sha_matches=False)
        request = request_from_checkout(root, "demo")
        self.assertNotIn(
            "fast-repair-current",
            {row["source"] for row in request.observations},
        )
        self.assertNotEqual(request.failure_class, "media_extraction_gap")

    def test_tmdb_or_failed_provider_http_cannot_authorize_cross_census_reuse(self):
        root, _ = self._checkout(provider_http_status=403)
        request = request_from_checkout(root, "demo")
        self.assertNotIn(
            "fast-repair-current",
            {row["source"] for row in request.observations},
        )

    def test_shallow_frontier_still_cannot_bypass_no_proof_probe(self):
        request = RepairRequest(
            provider_id="demo",
            failure_class="media_extraction_gap",
            status="NO PROOF",
            allowed_mutations=["provider_bloc"],
            census_prior={"sourceCensusRunId": "run-current"},
            provider_context={
                "runtimeMutationSource": "function resolve(){return [];}",
                "route_contract": {
                    "synthesisPolicy": {"mode": "rediscover_by_traversal"},
                },
            },
            observations=[{
                "source": "fast-repair-current",
                "value": {
                    "currentCensusRunId": "run-current",
                    "reuseAuthority": "exact-byte-current-evidence",
                    "failureClass": "media_extraction_gap",
                    "executionObserved": True,
                    "explorationProgress": True,
                    "observedPipelineStages": ["lookup"],
                },
            }],
        )
        decision = route_request(request)
        self.assertEqual(decision.mode, "probe")
        self.assertFalse(decision.requires_llm)
        self.assertEqual(decision.allowed_mutations, [])


if __name__ == "__main__":
    unittest.main()
