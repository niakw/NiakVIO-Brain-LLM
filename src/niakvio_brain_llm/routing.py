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



ADVISOR_STRATEGY_PROFILES = {
    "provider-owned-origin-header-and-domain-replay": "provider_origin_failover_v1",
    "search-detail-player-terminal-traversal": "proven_route_terminal_traversal_v1",
    "terminal-media-extractor-with-playback-validation": "chain_terminal_extractor_v1",
    "same-provider-candidate-program-replay": "retained_candidate_replay_v1",
    "proven-request-program-and-terminal-extraction": "player_media_extractor_v1",
    "discover-api-from-current-page-and-bundles": "search_contract_inference_v1",
}


def _advisor_strategy_exhausted(request: RepairRequest, strategy: str) -> bool:
    profile = ADVISOR_STRATEGY_PROFILES.get(_canon(strategy), "")
    if not profile:
        return False
    history = (request.provider_context or {}).get("advisor_experiment_history")
    if not isinstance(history, list):
        return False
    for row in history:
        if not isinstance(row, dict):
            continue
        if str(row.get("profile") or "").strip().casefold() != profile:
            continue
        fingerprint = str(row.get("llmAdvisorExperimentFingerprint") or "").strip().casefold()
        if not fingerprint:
            continue
        if int(row.get("consecutiveFailures") or 0) <= 0:
            continue
        if str(row.get("lastOutcome") or "").strip().casefold() in {"accepted", "verified", "success"}:
            continue
        return True
    return False

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

    # External/private guidance needs only a bounded strategy+experiment prior.
    # When the current taxonomy already owns both causal layer and canonical
    # strategy at high confidence, asking the model to repeat that strategy is
    # wasted inference. Synthesize the default executable experiment
    # deterministically and reserve the LLM for genuinely ambiguous/novel cases.
    if request.advisor_only and confidence >= 0.90 and strategy:
        if _advisor_strategy_exhausted(request, strategy):
            return RoutingDecision(
                mode="llm_repair",
                reason="canonical advisor experiment already failed on current provider state; synthesize a materially new bounded experiment",
                target_layer=layer,
                strategy=strategy,
                prior_confidence=confidence,
                requires_llm=True,
                allowed_mutations=[],
                next_actions=["keep causal strategy", "propose a novel bounded experiment"],
            )
        return RoutingDecision(
            mode="deterministic_advisor",
            reason="high-confidence provider taxonomy already owns the advisor strategy",
            target_layer=layer,
            strategy=strategy,
            prior_confidence=confidence,
            requires_llm=False,
            allowed_mutations=[],
            next_actions=["materialize bounded default experiment"],
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
