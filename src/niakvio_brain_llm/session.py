from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .contracts import RepairProposal, RepairRequest
from .planner import BrainPlanner

@dataclass(slots=True)
class VerificationOutcome:
    result: str
    failure_class_after: str = ""
    observations: list[str] = field(default_factory=list)
    verified_lanes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "failure_class_after": self.failure_class_after,
            "observations": self.observations[:12],
            "verified_lanes": self.verified_lanes[:8],
        }

def proposal_signature(proposal: RepairProposal) -> str:
    payload = {
        "strategy": proposal.strategy,
        "target_layer": proposal.target_layer,
        "mutations": proposal.mutations,
        "tests": proposal.tests,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:16]

class BrainSession:
    """Bounded propose -> verify -> replan loop.

    Verification is external by design: NiakVIO remains the only execution/proof authority.
    """

    def __init__(self, planner: BrainPlanner, *, max_attempts: int = 3):
        self.planner = planner
        self.max_attempts = max(1, max_attempts)
        self.history: list[dict[str, Any]] = []
        self._signatures: set[str] = set()

    @property
    def exhausted(self) -> bool:
        return len(self.history) >= self.max_attempts

    def propose(self, request: RepairRequest) -> RepairProposal:
        if self.exhausted:
            raise RuntimeError("brain session repair budget exhausted")

        enriched = RepairRequest(**request.to_dict())
        if self.history:
            enriched.observations = list(enriched.observations) + [{
                "source": "brain_session_previous_attempts",
                "value": self.history[-self.max_attempts:],
            }]

        proposal = self.planner.plan(enriched)
        signature = proposal_signature(proposal)
        if signature in self._signatures:
            raise RuntimeError("brain repeated an already-tested repair hypothesis")
        self._signatures.add(signature)
        return proposal

    def record(self, proposal: RepairProposal, outcome: VerificationOutcome) -> None:
        self.history.append({
            "attempt": len(self.history) + 1,
            "proposal_signature": proposal_signature(proposal),
            "strategy": proposal.strategy,
            "target_layer": proposal.target_layer,
            "confidence": proposal.confidence,
            "abstain": proposal.abstain,
            "outcome": outcome.to_dict(),
        })
