from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .contracts import RepairProposal, RepairRequest
from .advisor_experiments import next_advisor_experiment
from .planner import BrainPlanner
from .retrieval import ExperienceStore
from .routing import RoutingDecision, route_request


@dataclass(slots=True)
class BrainOutcome:
    routing: RoutingDecision
    proposal: RepairProposal | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "routing": self.routing.to_dict(),
            "proposal": self.proposal.to_dict() if self.proposal else None,
        }


class BrainOrchestrator:
    """Fast deterministic routing with LLM escalation only when useful."""

    def __init__(
        self,
        planner: BrainPlanner,
        store: ExperienceStore | None = None,
    ):
        self.planner = planner
        self.store = store or planner.store

    def run(self, request: RepairRequest, *, compact_force: bool = False) -> BrainOutcome:
        routing = route_request(request, self.store)

        if request.advisor_only and routing.mode == "deterministic_advisor":
            experiment = next_advisor_experiment(request, routing.strategy)
            if not experiment:
                raise RuntimeError("deterministic advisor routed without an available experiment")
            proposal = RepairProposal(
                provider_id=request.provider_id,
                diagnosis="high-confidence NiakVIO causal taxonomy prior with provider-local negative-memory rotation",
                strategy=routing.strategy,
                confidence=routing.prior_confidence,
                target_layer="provider",
                evidence=[],
                mutations=[],
                experiment=experiment,
                tests=[],
                abstain=False,
                abstain_reason="",
            )
            return BrainOutcome(routing=routing, proposal=proposal)

        if not routing.requires_llm:
            return BrainOutcome(routing=routing)

        effective = RepairRequest(**request.to_dict())

        if routing.mode == "llm_diagnose":
            # Diagnosis may classify causality, but cannot mutate anything.
            effective.allowed_mutations = []
        elif routing.mode == "llm_repair":
            effective.allowed_mutations = list(routing.allowed_mutations)

        proposal = self.planner.plan(effective, compact_force=compact_force)
        return BrainOutcome(routing=routing, proposal=proposal)
