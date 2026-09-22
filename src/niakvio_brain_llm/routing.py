from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .contracts import RepairRequest
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

    # Known non-provider failures are cheaper and safer to route directly to
    # the relevant diagnostic/test path than to ask a model to rediscover it.
    if layer != "provider":
        return RoutingDecision(
            mode="deterministic",
            reason=f"high-confidence {layer} causal class",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            next_actions=[strategy or f"run {layer} diagnostic/retest"],
        )

    # Replay/verification strategies do not need a patch-generating LLM.
    if strategy in NO_MUTATION_STRATEGIES:
        return RoutingDecision(
            mode="deterministic",
            reason="known provider strategy is replay/verification only",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            next_actions=[strategy],
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
