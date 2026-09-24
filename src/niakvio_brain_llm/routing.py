from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .contracts import RepairRequest
from .advisor_experiments import next_advisor_experiment
from .policy import NO_MUTATION_STRATEGIES, build_mutation_policy
from .priors import build_causal_prior
from .retrieval import ExperienceStore


@dataclass(slots=True)
class RoutingDecision:
    mode: str
    reason: str
    target_layer: str = "unknown"
    strategy: str = ""
    prior_confidence: float = 0.0
    requires_llm: bool = False
    allowed_mutations: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canon(value: object) -> str:
    return "-".join(str(value or "").strip().casefold().replace("_", "-").split())




def route_request(
    request: RepairRequest,
    store: ExperienceStore | None = None,
) -> RoutingDecision:
    experiences = (store or ExperienceStore([])).search(request.to_dict(), limit=6)
    prior = build_causal_prior(request, experiences)
    policy = build_mutation_policy(request, prior)

    layer = str(prior.get("target_layer") or "unknown")
    confidence = float(prior.get("confidence") or 0.0)
    strategy = str(prior.get("strategy_prior") or "")
    status = _canon(request.status)
    failure = _canon(request.failure_class)
    transport_class = _canon((request.census_prior or {}).get("harnessTransportClass"))

    # A healthy provider should never pay LLM inference cost unless an explicit
    # regression/failure was attached to the request.
    if status in {"full-ok", "partial-ok"} and failure in {"", "healthy", "none"}:
        return RoutingDecision(
            mode="skip",
            reason="current provider state does not require repair reasoning",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
        )

    # Low-confidence/unknown causality is exactly where model reasoning helps.
    # Keep it diagnosis-only: no mutation authority until causality is resolved.
    if layer == "unknown" or confidence < 0.80:
        return RoutingDecision(
            mode="llm_diagnose",
            reason="causal layer is not established strongly enough",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=["classify causal layer", "request discriminating evidence"],
        )

    # Once the deterministic browser/native differential has already isolated
    # a Core/client transport gap, repeating the same harness probes adds no new
    # information. Ask the model for a bounded architecture diagnosis instead;
    # non-provider mutation remains forbidden by policy and planner guards.
    if layer == "harness" and (
        "client-transport-gap" in status
        or transport_class == "browser-profile-only-both-networks"
    ):
        return RoutingDecision(
            mode="llm_diagnose",
            reason="deterministic transport differential is complete; synthesize the bounded Core/client adaptation",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=[
                strategy or "design Core/client transport adaptation",
                "define discriminating native-client validation",
            ],
        )

    # Known non-provider failures that have not exhausted deterministic
    # diagnostics are cheaper and safer to route directly to their test path.
    if layer != "provider":
        return RoutingDecision(
            mode="deterministic",
            reason=f"high-confidence {layer} causal class",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            next_actions=[strategy or f"run {layer} diagnostic/retest"],
        )

    # External/private guidance is deterministic while the causal strategy is
    # already known. Rotate through bounded experiment knobs from current
    # provider-local negative memory; invoke Qwen only after that bounded
    # experiment space is exhausted or causality itself is ambiguous.
    if request.advisor_only and confidence >= 0.90 and strategy:
        experiment = next_advisor_experiment(request, strategy)
        if experiment:
            return RoutingDecision(
                mode="deterministic_advisor",
                reason="high-confidence provider taxonomy owns the strategy; execute the next untried bounded advisor experiment",
                target_layer=layer,
                strategy=strategy,
                prior_confidence=confidence,
                requires_llm=False,
                allowed_mutations=[],
                next_actions=["materialize next untried bounded experiment"],
            )
        return RoutingDecision(
            mode="llm_repair",
            reason="bounded deterministic advisor experiment space is exhausted",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=["keep causal layer", "synthesize a novel strategy-compatible experiment"],
        )

    # Replay/verification remains deterministic in normal repair execution.
    # Advisor-only mode is handled above so an exhausted replay profile can
    # receive a fresh bounded experiment without provider mutation authority.
    if strategy in NO_MUTATION_STRATEGIES:
        return RoutingDecision(
            mode="deterministic",
            reason="known provider strategy is replay/verification only",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            next_actions=[strategy],
        )
    if request.advisor_only:
        return RoutingDecision(
            mode="llm_repair",
            reason="advisor-only provider synthesis requires a novel or incomplete strategy",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=["propose bounded provider strategy and experiment"],
        )

    # Do not spend an LLM call asking it to invent evidence. Gather the missing
    # current proof first and call the model only after the request is enriched.
    if policy.get("force_abstain"):
        reason = str(policy.get("reason") or "missing current evidence")
        return RoutingDecision(
            mode="probe",
            reason=reason,
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            allowed_mutations=[],
            next_actions=[
                "gather fresh provider-local evidence",
                strategy or "rebuild current repair context",
            ],
        )

    if policy.get("allow_mutations"):
        return RoutingDecision(
            mode="llm_repair",
            reason="provider-local repair requires synthesis",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            requires_llm=True,
            allowed_mutations=list(policy.get("allowed_scopes") or []),
            next_actions=["propose smallest provider-local candidate patch"],
        )

    return RoutingDecision(
        mode="probe",
        reason=str(policy.get("reason") or "provider repair context is incomplete"),
        target_layer=layer,
        strategy=strategy,
        prior_confidence=confidence,
        next_actions=["gather provider-local repair context"],
    )
