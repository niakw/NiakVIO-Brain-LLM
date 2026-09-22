from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import RepairProposal, RepairRequest
from .session import VerificationOutcome

VALID_RESULTS = {"validated", "failed", "inconclusive", "abstained"}

def sanitized_experience(
    request: RepairRequest,
    proposal: RepairProposal,
    outcome: VerificationOutcome,
) -> dict[str, Any]:
    result = outcome.result if outcome.result in VALID_RESULTS else "inconclusive"
    return {
        "provider_id": request.provider_id,
        "failure_class": request.failure_class,
        "status_before": request.status,
        "supported_types": request.supported_types[:8],
        "diagnosis": proposal.diagnosis[:1000],
        "strategy": proposal.strategy[:200],
        "target_layer": proposal.target_layer,
        "mutation_scopes": sorted({
            str(item.get("scope") or "")
            for item in proposal.mutations
            if str(item.get("scope") or "")
        }),
        "requested_tests": proposal.tests[:12],
        "result": result,
        "failure_class_after": outcome.failure_class_after[:200],
        "verified_lanes": outcome.verified_lanes[:8],
        "lesson": "; ".join(outcome.observations[:6])[:1600],
        "proof_authority": False,
    }

def append_jsonl(path: str | Path, row: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
