from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

from niakvio_brain_llm.niakvio_adapter import _provider_negative_memory
from niakvio_brain_llm.advisor_experiments import experiment_fingerprint as runtime_fingerprint, next_advisor_experiment
from niakvio_brain_llm.contracts import RepairRequest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "publish_niakvio_guidance", ROOT / "scripts" / "publish_niakvio_guidance.py"
)
assert SPEC and SPEC.loader
publish = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish)

payload = {
    "entries": [
        {
            "providerId": "AnimeSalt",
            "failureClass": "route_proven_gap",
            "profile": "proven_route_terminal_traversal_v1",
            "llmAdvisorExperimentFingerprint": "a" * 64,
            "consecutiveFailures": 3,
            "failures": 3,
            "successes": 0,
            "lastOutcome": "rejected",
            "lastReason": "required_category_playable_proof:anime",
            "executionObserved": True,
        },
        {"providerId": "other", "llmAdvisorExperimentFingerprint": "b" * 64},
    ]
}
rows = _provider_negative_memory(payload, "animesalt")
assert len(rows) == 1, rows
assert rows[0]["llmAdvisorExperimentFingerprint"] == "a" * 64
assert rows[0]["consecutiveFailures"] == 3

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "automation").mkdir()
    (root / "automation" / "brain-repair-memory.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    blocked = publish.load_blocked_fingerprints(root)
    assert blocked == {"animesalt": {"a" * 64}}, blocked

experiment = publish.sanitize_experiment(
    {}, strategy="search-detail-player-terminal-traversal"
)
fingerprint = publish.experiment_fingerprint(experiment)
proposal_rows = [{
    "ok": True,
    "provider": "animesalt",
    "failure_class": "route_proven_gap",
    "proposal": {
        "provider_id": "animesalt",
        "strategy": "search_detail_player_terminal_traversal",
        "target_layer": "provider",
        "confidence": 0.96,
        "experiment": {},
        "abstain": False,
    },
}]
out = publish.sanitize(
    proposal_rows,
    niakvio_sha="1" * 40,
    brain_llm_sha="2" * 40,
    blocked_fingerprints={"animesalt": {fingerprint}},
)
assert out["providerCount"] == 0, out
assert out["rows"] == [], out

print("advisor negative-memory ingestion/publication guard contract passed")

# The runtime selector and publisher must hash the same normalized experiment.
request = RepairRequest(provider_id="demo", failure_class="route_proven_gap", status="ROUTE PROVEN", advisor_only=True)
runtime_experiment = next_advisor_experiment(request, "search_detail_player_terminal_traversal")
assert runtime_fingerprint(runtime_experiment) == publish.experiment_fingerprint(
    publish.sanitize_experiment(runtime_experiment, strategy="search-detail-player-terminal-traversal")
)

blocked_fp = runtime_fingerprint(runtime_experiment)
rotated = next_advisor_experiment(
    RepairRequest(
        provider_id="demo",
        failure_class="route_proven_gap",
        status="ROUTE PROVEN",
        advisor_only=True,
        census_prior={"dominantIssue": "provider_waf_challenge"},
        provider_context={"advisor_experiment_history": [{
            "llmAdvisorExperimentFingerprint": blocked_fp,
            "consecutiveFailures": 1,
            "lastOutcome": "rejected",
            "lastReason": "provider_waf_challenge",
        }]},
    ),
    "search_detail_player_terminal_traversal",
)
assert runtime_fingerprint(rotated) != blocked_fp
assert rotated["session_bootstrap"] is True
