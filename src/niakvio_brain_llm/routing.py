from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .contracts import RepairRequest
from .advisor_experiments import next_advisor_experiment
from .policy import NO_MUTATION_STRATEGIES, build_mutation_policy
from .priors import build_causal_prior
from .retrieval import ExperienceStore
from .repair_family import repair_family_descriptor
from .live_evidence import current_candidate_identity_gap


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


REPLAYABLE_FAMILY_MECHANISMS = {
    "balanced-class-container",
    "exact-class-text-token-boundary",
    "exact-class-token-boundary",
}


def _validated_family_mechanism(request: RepairRequest, experiences: list[dict[str, Any]]) -> str:
    family_key = str(repair_family_descriptor(request).get("key") or "")
    if not family_key:
        return ""
    candidates: list[tuple[int, int, str]] = []
    for row in experiences:
        if str(row.get("result") or "").strip().casefold() != "validated":
            continue
        repair_family = row.get("repair_family") or row.get("repairFamily")
        if not isinstance(repair_family, dict) or str(repair_family.get("key") or "") != family_key:
            continue
        mechanism = _canon(row.get("mechanismFamily") or row.get("mechanism_family") or row.get("strategy"))
        if mechanism not in REPLAYABLE_FAMILY_MECHANISMS:
            continue
        candidates.append((
            int(row.get("successCount") or 0),
            -int(row.get("failureCount") or 0),
            mechanism,
        ))
    if not candidates:
        return ""
    candidates.sort(reverse=True)
    return candidates[0][2]



# An executor that has failed three DISTINCT, observed advisor experiments
# needs new model reasoning, not another combinatorial knob rotation. Count
# only same-executor failed fingerprints: historical or unexecuted proposals
# have no authority to exhaust deterministic hypothesis space.
_ADVISOR_PROFILE_BY_STRATEGY = {
    "provider-owned-origin-header-and-domain-replay": "provider_origin_failover_v1",
    "search-detail-player-terminal-traversal": "proven_route_terminal_traversal_v1",
    "terminal-media-extractor-with-playback-validation": "chain_terminal_extractor_v1",
    "same-provider-candidate-program-replay": "retained_candidate_replay_v1",
    "proven-request-program-and-terminal-extraction": "player_media_extractor_v1",
    "discover-api-from-current-page-and-bundles": "search_contract_inference_v1",
    "bind-catalogue-result-to-requested-identity": "identity_alias_search_traversal_v1",
}


def _exhausted_executed_advisor_family(request: RepairRequest, strategy: str) -> bool:
    profile = _ADVISOR_PROFILE_BY_STRATEGY.get(_canon(strategy))
    history = (request.provider_context or {}).get("advisor_experiment_history")
    if not profile or not isinstance(history, list):
        return False
    fingerprints: set[str] = set()
    for row in history:
        if not isinstance(row, dict):
            continue
        if _canon(row.get("profile")) != profile.replace("_", "-"):
            continue
        if row.get("executionObserved") is not True:
            continue
        if int(row.get("consecutiveFailures") or 0) <= 0:
            continue
        if _canon(row.get("lastOutcome")) in {"accepted", "verified", "success"}:
            continue
        fingerprint = str(row.get("llmAdvisorExperimentFingerprint") or "").strip().casefold()
        if len(fingerprint) == 64 and all(c.isdigit() or c in "abcdef" for c in fingerprint):
            fingerprints.add(fingerprint)
            if len(fingerprints) >= 3:
                return True
    return False


def _has_current_executed_player_frontier(request: RepairRequest) -> bool:
    """Recognize a current/exact-byte sandbox traversal to provider player logic."""
    expected_run = str((request.census_prior or {}).get("sourceCensusRunId") or "")
    expected_failure = _canon(request.failure_class)
    if expected_failure not in {"media-extraction-gap", "chain-terminal-gap", "route-proven-gap"}:
        return False
    for row in request.observations or []:
        if not isinstance(row, dict) or _canon(row.get("source")) != "fast-repair-current":
            continue
        value = row.get("value")
        if not isinstance(value, dict):
            continue
        current_run = str(value.get("currentCensusRunId") or value.get("sourceCensusRunId") or "")
        if expected_run and current_run != expected_run:
            continue
        if value.get("executionObserved") is not True or value.get("explorationProgress") is not True:
            continue
        if _canon(value.get("failureClass")) != expected_failure:
            continue
        if str(value.get("reuseAuthority") or "") not in {"same-census", "exact-byte-current-evidence"}:
            continue
        if "player" in {_canon(stage) for stage in value.get("observedPipelineStages") or []}:
            return True
    return False


def _user_client_visibility_differential(request: RepairRequest) -> bool:
    """A field report is a probe target, never current-source proof."""
    for item in request.observations or []:
        if not isinstance(item, dict) or _canon(item.get("source")) != "user-client-field-report":
            continue
        row = item.get("value")
        if (
            isinstance(row, dict)
            and row.get("authority") == "historical-user-report-only"
            and row.get("crossClientVisibilityDiscrepancy") is True
            and row.get("proofAuthority") is False
            and row.get("publicationAuthority") is False
            and row.get("mutationAuthority") is False
            and row.get("executedJsKnown") is False
        ):
            return True
    return False


def _official_android_tv_diagnostic(request: RepairRequest) -> dict[str, Any]:
    """Same-current-provider-JS native observation, historical-only, no authority."""
    for observation in request.observations or []:
        if not isinstance(observation, dict) or _canon(observation.get("source")) != "official-android-tv-emulator":
            continue
        row = observation.get("value")
        if (
            isinstance(row, dict)
            and row.get("source") == "official-android-tv-emulator"
            and row.get("client") == "tv"
            and row.get("historicalOnly") is True
            and all(row.get(flag) is False for flag in (
                "proofAuthority", "publicationAuthority",
                "nativePlaybackAuthority", "providerMutationAuthority",
            ))
        ):
            return row
    return {}


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

    # TV is the primary executable client for Brain repair. A reported
    # macOS-positive/TV-missing provider must first have a source-pinned native
    # emulator oracle. Existing Lego for Desktop/Mobile/iOS remains intact, but
    # no client is presumed to have validated playback merely from build status.
    if _user_client_visibility_differential(request):
        native_tv = _official_android_tv_diagnostic(request)
        if not native_tv:
            return RoutingDecision(
                mode="probe",
                reason="Android TV is primary; cross-client visibility lacks a source-pinned official emulator trace",
                target_layer="client",
                strategy="run_official_android_tv_emulator_first",
                prior_confidence=0.90,
                allowed_mutations=[],
                next_actions=[
                    "execute official Android TV emulator with exact provider JS and selected canonical manifest",
                    "record installed app selection, QuickJS phases, network route and terminal player evidence",
                    "ingest sanitized artifact by source SHA; do not mutate the provider from user report alone",
                ],
            )
        if native_tv.get("appSelected") is True and (
            native_tv.get("quickJsReturned") == 0
            or bool(native_tv.get("quickJsErrors"))
        ):
            return RoutingDecision(
                mode="llm_diagnose",
                reason="official Android TV emulator invoked the exact JS but returned no media or a QuickJS exception; user reports macOS playback",
                target_layer="client",
                strategy="trace_tv_quickjs_media_context_and_transport",
                prior_confidence=0.80,
                requires_llm=True,
                allowed_mutations=[],
                next_actions=[
                    "inspect official TV QuickJS exception category and metadata/BuildConfig capability",
                    "compare Desktop vs Android TV provider input, manifest scope and fetch bridge",
                    "propose shared client/Core/Lego correction, not a provider JS override",
                    "re-run exact TV emulator after materialization; validate terminal media and audio",
                ],
            )
        return RoutingDecision(
            mode="probe",
            reason="official Android TV emulator evidence does not yet explain the cross-client visibility differential",
            target_layer="client",
            strategy="complete_official_android_tv_player_probe",
            prior_confidence=0.88,
            allowed_mutations=[],
            next_actions=[
                "verify installed TV stream list and real decoding on the same fixture",
                "compare exact JS and manifest version with the macOS observation",
                "retain evidence as diagnostic-only until verified playback",
            ],
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

    route_contract = (
        request.provider_context.get("route_contract")
        if isinstance(request.provider_context, dict)
        and isinstance(request.provider_context.get("route_contract"), dict)
        else {}
    )
    route_policy = (
        route_contract.get("synthesisPolicy")
        if isinstance(route_contract.get("synthesisPolicy"), dict)
        else {}
    )
    route_mode = _canon(route_policy.get("mode"))

    # NO PROOF normally requires Recognition. Avoid repeating that probe only
    # when the sandbox already executed player logic on same-census or exact
    # current bytes. This does not promote route/playback/publication proof.
    executed_player_frontier = _has_current_executed_player_frontier(request)
    if (status == "no-proof" or route_mode == "rediscover-by-traversal") and not executed_player_frontier:
        return RoutingDecision(
            mode="probe",
            reason="current provider route is not proven; recognition traversal must precede runtime synthesis",
            target_layer=layer,
            strategy="rediscover_current_provider_route_by_traversal",
            prior_confidence=max(confidence, 0.96),
            requires_llm=False,
            allowed_mutations=[],
            next_actions=[
                "run current provider authority/hub -> search/lookup -> detail -> player/embed -> terminal traversal",
                "persist newly proven route DATA",
                "rebuild Brain request on the refreshed current bytes",
            ],
        )

    if failure == "candidate-replay-gap" and current_candidate_identity_gap(request.observations):
        # Evidence now distinguishes "URL unavailable" from "URL exists but
        # content identity unproven". Do NOT promote or guess a provider fix:
        # model must first locate whether source provenance was dropped by
        # provider extraction, Core projection or incomplete HLS introspection.
        return RoutingDecision(
            mode="llm_diagnose",
            reason="current exact JS returned media but content identity/duration remains unproven; prior-only candidate replay is exhausted",
            target_layer="unknown",
            strategy="trace_independent_episode_and_hls_provenance",
            prior_confidence=0.70,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=[
                "compare provider-owned episode/API selection with returned source metadata",
                "distinguish provider identity loss, Core projection and incomplete HLS duration",
                "produce reusable source-pinned evidence plan before mutation or promotion",
                *(
                    [
                        "verify installed manifest projection, local enabled state and exact JS hash on each Nuvio client",
                        "trace native app media-type selection, plugin invocation and stream UI independently",
                    ]
                    if _user_client_visibility_differential(request) else []
                ),
            ],
        )

    # External/private guidance is deterministic while the causal strategy is
    # already known. Rotate through bounded experiment knobs from current
    # provider-local negative memory; invoke Qwen only after that bounded
    # experiment space is exhausted or causality itself is ambiguous.
    if request.advisor_only and confidence >= 0.90 and strategy:
        if _exhausted_executed_advisor_family(request, strategy):
            return RoutingDecision(
                mode="llm_repair",
                reason="three distinct current-executor experiments failed in real replay; generate a new causal hypothesis",
                target_layer=layer,
                strategy=strategy,
                prior_confidence=confidence,
                requires_llm=True,
                allowed_mutations=[],
                next_actions=["synthesize new evidence-driven advisor experiment", "retain exact failed fingerprints"],
            )
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

    family_mechanism = _validated_family_mechanism(request, experiences)
    if policy.get("allow_mutations") and family_mechanism:
        return RoutingDecision(
            mode="family_replay",
            reason="validated repair-family mechanism can be recompiled on current provider bytes before any LLM call",
            target_layer=layer,
            strategy=family_mechanism,
            prior_confidence=confidence,
            requires_llm=False,
            allowed_mutations=list(policy.get("allowed_scopes") or []),
            next_actions=[
                "recompile validated family mechanism on exact current bytes",
                "sandbox current provider independently",
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
