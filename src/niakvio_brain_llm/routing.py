from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .contracts import RepairRequest
from .advisor_experiments import next_advisor_experiment, strategy_profile_exhausted
from .native_hls_receipt_dedupe_experiments import native_hls_receipt_dedupe_experiment, native_hls_receipt_dedupe_positive_result
from .native_origin_experiments import (
    native_blocking_origin_priority_experiment,
    native_blocking_origin_priority_prior_attempt,
)
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



# Compatibility wrapper: the shared advisor contract is also consumed by the
# prompt/schema/planner boundary, so routing and execution cannot disagree.
def _exhausted_executed_advisor_family(request: RepairRequest, strategy: str) -> bool:
    return strategy_profile_exhausted(request, strategy)


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

    # A synthetic control executed through the same official QuickJS
    # PluginRuntime is a stronger *runtime* diagnostic than any one provider
    # count=0. It is not media proof and never authorizes a provider patch.
    official_tv = _official_android_tv_diagnostic(request)
    # A source-pinned native host/outcome sequence is more discriminating than
    # the generic awaited-Promise suspicion. Keep a genuinely broken immediate
    # baseline fail-closed, but do not let the older Promise prior hide an
    # independently observed player 5xx -> alternate 2xx -> HLS 2xx sequence.
    # An observed decoded V31 candidate changes the next frontier to
    # visual/audio/identity and sibling validation. Never fall back to the
    # old V29->V30 route or silently promote candidate bytes.
    dedupe_positive = native_hls_receipt_dedupe_positive_result(request)
    if dedupe_positive:
        return RoutingDecision(
            mode="deterministic_advisor",
            reason="source-pinned isolated V31 returned streams and native player reported decoded video; the published provider and visual/audio identity remain unverified",
            target_layer="core",
            strategy="verify_hls_receipt_dedupe_visual_audio_family_before_promotion",
            prior_confidence=0.95,
            requires_llm=False,
            allowed_mutations=[],
            next_actions=[
                "never regenerate V29/V30/V31 on the same evidence and unchanged source",
                "obtain a screenshot while the official player is still visible; verify correct episode rather than player telemetry alone",
                "verify offered and selectable French/Japanese audio tracks; do not infer them from signed HLS master tags or random UI fragments",
                "replay a bounded source-pinned native baseline and one causally compatible sibling before applying the shared Core mechanism",
                "require current production materialization and exact SHA-matched non-regression before publication",
            ],
        )
    dedupe_followup = native_hls_receipt_dedupe_experiment(request)
    if dedupe_followup:
        return RoutingDecision(
            mode="deterministic_advisor",
            reason="executed/restored V30 still returned zero streams after exact HLS 200->403; shared ProviderBase first-wins playback-key dedupe can discard a later verified master receipt",
            target_layer="core",
            strategy="preserve_hls_receipt_across_playback_key_dedupe",
            prior_confidence=0.91,
            requires_llm=False,
            allowed_mutations=[],
            next_actions=[
                "compile only the Brain-owned V31 generic same-key HLS receipt preservation experiment",
                "do not replay V29 or V30 on unchanged provider bytes",
                "preserve original stream metadata and language/readers when deduplicating",
                "retain strict independent child playlists/segments and terminal sanitizer",
                "test exact rematerialized bytes in official NuvioTV, require correct decoded episode and audio before any promotion",
            ],
        )
    # Source-pinned provider-family discriminator, independent of the V29-V31
    # signed-HLS case. "HTTP 200" is not source validity when episodes.js
    # returned HTML. This is diagnosis only: schema, slug, protection page and
    # transport still require independent evidence and no provider mutation.
    script_shapes = official_tv.get("nativeSourceScriptShapePatterns") or []
    if (
        official_tv.get("appSelected") is True
        and official_tv.get("readerEvidenceComplete") is True
        and official_tv.get("nativeExtractionZeroObserved") is True
        and "script_html_2xx" in script_shapes
    ):
        return RoutingDecision(
            mode="llm_diagnose",
            reason="official Android TV returned a 2xx HTML document at an expected JavaScript episode-source endpoint, with zero extracted streams; HTTP success is not source validity and WAF/slug/domain causes remain unresolved",
            target_layer="unknown",
            strategy="discriminate_catalogue_script_html_vs_missing_source_shape",
            prior_confidence=0.91,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=[
                "inspect the exact current catalogue family, canonical episode/season identity and source route before editing any provider",
                "distinguish expected episodes.js resource existence, genuine JavaScript payload, SPA HTML shell and challenge page; never treat 200 as sufficient",
                "compare announced primary and fallback domains, page referer and discovered content slug with read-only evidence",
                "propose a reusable Brain source-shape strategy or owned family Bloc only after an independent validated representative",
                "compile and rematerialize an isolated candidate; require official NuvioTV returned streams, correct decoded episode, language/audio and non-regression before promotion",
            ],
        )

    # A missing episodes.js resource is a separate causal family from a
    # successful HTTP response containing HTML. Neither proves a bad slug,
    # a domain move or anti-bot protection without independent source evidence.
    if (
        official_tv.get("appSelected") is True
        and official_tv.get("readerEvidenceComplete") is True
        and official_tv.get("nativeExtractionZeroObserved") is True
        and "script_http_missing" in script_shapes
    ):
        return RoutingDecision(
            mode="llm_diagnose",
            reason="official Android TV observed a 404/410 for an expected episode-source JavaScript resource and extracted zero streams; script absence alone does not identify a slug, domain, WAF or Core defect",
            target_layer="unknown",
            strategy="discriminate_missing_episode_script_resource",
            prior_confidence=0.89,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=[
                "verify the exact requested title, season, episode and source language against the canonical catalogue route",
                "compare read-only response shape and status on announced primary and fallback hosts using native client headers without inferring the cause",
                "distinguish a missing script from a redirect, page template, domain retirement or unimplemented source route before selecting a family Bloc",
                "never authorize a provider patch from a 404/410 alone; require an independently validated family representative",
                "only promote a generated Core or family candidate after exact-byte NuvioTV episode decode, audio tracks and sibling non-regression",
            ],
        )

    origin_priority_prior = native_blocking_origin_priority_prior_attempt(request)
    origin_priority_experiment = (
        {} if origin_priority_prior
        else native_blocking_origin_priority_experiment(request)
    )
    if (official_tv.get("appSelected") is True
            and official_tv.get("nativeExtractionZeroObserved") is True
            and official_tv.get("tvPromiseControl") == "promise_delivery_gap"
            and not origin_priority_experiment):
        return RoutingDecision(
            mode="llm_diagnose",
            reason="official Android TV synthetic immediate result succeeded but awaited Promise control did not; provider stream zero cannot be attributed to provider JS",
            target_layer="client",
            strategy="diagnose_android_tv_quickjs_promise_completion",
            prior_confidence=0.90,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=[
                "inspect official TV QuickJS async job lifecycle using the synthetic non-media control",
                "compare TV bridge with accepted Desktop runtime and published JS requirements",
                "fix owner-level client/Brain runtime compatibility without editing individual providers",
                "rerun synthetic immediate and awaited controls, then source-pinned official provider playback",
                "retain zero media publication authority until correct decoded content and audio are proven",
            ],
        )
    if (official_tv.get("appSelected") is True
            and official_tv.get("nativeExtractionZeroObserved") is True
            and official_tv.get("tvPromiseControl") == "baseline_failed"):
        return RoutingDecision(
            mode="probe",
            reason="official Android TV synthetic immediate JS control failed; async and provider attribution are unreliable",
            target_layer="client",
            strategy="isolate_android_tv_quickjs_baseline",
            prior_confidence=0.75,
            allowed_mutations=[],
            next_actions=[
                "inspect official test-only control compilation and LocalScraperResult parsing",
                "replay the same immediate control in NuvioTV without modifying provider JS",
                "do not infer provider failure from a broken baseline control",
            ],
        )

    # A current official TV trace can expose a stronger Core signature than
    # a generic zero-stream provider result: the exact same signed HLS root
    # succeeded once and then returned 403 when pre-player validation fetched
    # it again. The URL/token is deliberately absent from the sanitized ledger.
    # This is a Core/runtime ownership signal, never provider patch authority.
    if (
        official_tv.get("appSelected") is True
        and official_tv.get("sameMediaRootSuccessThenForbidden") is True
        and not origin_priority_prior
        and not origin_priority_experiment
    ):
        return RoutingDecision(
            mode="llm_diagnose",
            reason="official Android TV observed the same HLS root succeed then fail 403 before player delivery; duplicate pre-player media validation is a Core/runtime concern",
            target_layer="core",
            strategy="reuse_successful_hls_root_across_core_validation",
            prior_confidence=0.97,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=[
                "locate consecutive Core/media-validation owners that fetch the identical HLS root",
                "reuse only the ephemeral successful master response while still validating child playlists and media segments",
                "strip private proof bodies before provider output and retain fail-closed terminal sanitizer ownership",
                "rematerialize affected provider bundles from the shared Core pipeline instead of editing one provider",
                "replay exact official TV client and require returned stream, decoded correct content and audio before publication",
            ],
        )

    if origin_priority_prior:
        attempt = origin_priority_prior.get("attempt") or {}
        verdict = str(attempt.get("candidateVerdict") or "")
        if verdict == "candidate_terminal_decode_observed":
            return RoutingDecision(
                mode="deterministic_advisor",
                reason="the exact blocking-native origin-priority strategy already executed on the same provider bytes and reached terminal decoded video; repeating the same candidate would add no information",
                target_layer="core",
                strategy="validate_native_origin_priority_across_causal_family_before_promotion",
                prior_confidence=0.98,
                requires_llm=False,
                allowed_mutations=[],
                next_actions=[
                    "do not rerun the same provider/host-order candidate on unchanged bytes",
                    "select a sibling provider with the same blocking-native 5xx -> alternate 2xx -> HLS 2xx causal signature",
                    "run the same candidate-only mechanism on that representative and persist its verdict",
                    "promote the generic Core/ProviderBase mechanism only after representative family success",
                    "after promotion rematerialize production bytes and require fresh official TV decoded content, audio and non-regression before calling it repaired",
                ],
            )
        if verdict in {
            "candidate_extraction_improved_reader_unverified",
            "candidate_reader_healthy_decode_unverified",
        }:
            return RoutingDecision(
                mode="llm_diagnose",
                reason="the exact V29 candidate already executed and advanced extraction/reader state but did not prove decoded video; repeat origin ordering is exhausted and the remaining frontier is player delivery/decoding",
                target_layer="client",
                strategy="diagnose_post_origin_priority_reader_frontier",
                prior_confidence=0.94,
                requires_llm=True,
                allowed_mutations=[],
                next_actions=[
                    "do not rerun the same V29 candidate on unchanged provider bytes",
                    "inspect terminal media handoff, headers, audio tracks and player decode state from the executed candidate",
                    "separate Core extraction success from client/player decode failure",
                    "generate the next owner-level experiment only after the reader frontier is discriminated",
                ],
            )
        if (
            official_tv.get("sameMediaRootSuccessThenForbidden") is True
            and verdict in {
                "candidate_zero_stream",
                "candidate_runtime_nonempty_unconfirmed_extraction",
            }
        ):
            return RoutingDecision(
                mode="llm_diagnose",
                reason="V29 already executed without terminal decode, while the same source-pinned trace independently observed one HLS root succeed then fail 403; origin ordering is exhausted and duplicate pre-player Core validation is now the stronger unused discriminator",
                target_layer="core",
                strategy="reuse_successful_hls_root_across_core_validation",
                prior_confidence=0.98,
                requires_llm=True,
                allowed_mutations=[],
                next_actions=[
                    "do not rerun the same V29 host ordering on unchanged provider bytes",
                    "locate the consecutive Core/media-validation owners that fetch the identical HLS root",
                    "reuse only the ephemeral successful master response while still validating child playlists and media segments",
                    "strip private proof bodies and never persist signed media URLs or tokens",
                    "generate a candidate-only Core experiment, rematerialize exact bytes and replay the same official TV fixture",
                    "require terminal decoded correct content and French/multitrack audio before any promotion",
                ],
            )

        # Prefer an independent, source-pinned HLS replay signature when present.
        # Without that evidence, a nonempty runtime/empty extraction remains a
        # harness-observability issue; neither diagnosis grants mutation authority.
        if verdict == "candidate_runtime_nonempty_unconfirmed_extraction":
            return RoutingDecision(
                mode="probe",
                reason="the candidate runtime returned data but sanitized extraction evidence did not confirm it; fix observability before changing repair strategy",
                target_layer="harness",
                strategy="repair_native_candidate_extraction_observability",
                prior_confidence=0.93,
                requires_llm=False,
                allowed_mutations=[],
                next_actions=[
                    "do not rerun V29 until exact runtime result and sanitized extraction observation agree",
                    "repair the diagnostic bridge without weakening production validation",
                    "replay the same candidate once after observability is fixed",
                ],
            )

        if verdict in {"candidate_integrity_failure", "candidate_not_executed"}:
            return RoutingDecision(
                mode="probe",
                reason="the previous V29 attempt did not produce an authoritative exact-byte execution verdict; repair candidate execution integrity before any strategy retry",
                target_layer="harness",
                strategy="repair_native_candidate_execution_integrity",
                prior_confidence=0.95,
                requires_llm=False,
                allowed_mutations=[],
                next_actions=[
                    "inspect exact staged-byte attestation, PluginManager execution marker and restoration marker",
                    "fix runner/harness integrity without editing provider JS",
                    "retry only after the candidate oracle can prove exact execution",
                ],
            )
        return RoutingDecision(
            mode="llm_diagnose",
            reason="the exact V29 origin-priority candidate already executed on unchanged provider bytes without terminal decode; the deterministic strategy is exhausted and Brain must change causal strategy",
            target_layer="core",
            strategy="change_native_origin_strategy_after_executed_failure",
            prior_confidence=0.96,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=[
                "do not regenerate the same preferred/deprioritized host order on unchanged provider bytes",
                "use the persisted negative verdict to choose a different Core/client/network discriminator",
                "retain exact source/provider-byte provenance for the next candidate",
                "require terminal decoded content and audio before any promotion",
            ],
        )

    if origin_priority_experiment:
        return RoutingDecision(
            mode="deterministic_advisor",
            reason="official Android TV source-pinned ordering observed a player-page 5xx, a different player-page 2xx and subsequent HLS 2xx before a near-budget zero result; candidate-only native blocking origin ordering is causally testable",
            target_layer="core",
            strategy="prioritize_native_blocking_player_origin_from_observed_outcome",
            prior_confidence=0.96,
            requires_llm=False,
            allowed_mutations=[],
            next_actions=[
                "compile the Brain-generated host ordering into candidate ProviderBase data only",
                "scope ordering to blocking native fetch and leave Node/browser ordering unchanged",
                "rematerialize exact provider bytes and replay the same official Android TV fixture",
                "require returned terminal media, decoded correct episode and French audio before promotion",
                "persist negative result and do not promote this prior if the preferred host no longer reaches terminal media",
            ],
        )

    # A native reader can fetch an HLS playlist successfully and still return
    # zero near the shared ProviderBase/Core 25s budget. That timing does not
    # prove the responsible layer: a slow host, failed fallback, JS deadline,
    # native bridge or Core validation could all explain it. Route to a
    # source-pinned owner diagnosis, never a provider-local mutation.
    if (
        official_tv.get("appSelected") is True
        and official_tv.get("nativeExtractionZeroObserved") is True
        and official_tv.get("hlsPlaylist2xxNearProviderBudgetZeroObserved") is True
    ):
        return RoutingDecision(
            mode="llm_diagnose",
            reason="official Android TV reached an HLS playlist HTTP 2xx but returned zero streams near a 25s provider request budget; causal owner remains unproven",
            target_layer="unknown",
            strategy="discriminate_tv_hls_success_zero_near_js_budget_owner",
            prior_confidence=0.86,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=[
                "compare exact current Core and generated ProviderBase JS deadlines with the official TV harness and NuvioTV timeout independently",
                "pin a route-scoped trace of initial and alternate player start/end, HLS master proof handoff, child playlists and pre-player sanitizers without persisting signed URLs",
                "inspect the exact official NuvioTV PluginRuntime bridge: async JS fetch may call synchronous __native_fetch -> OkHttp Call.execute; Promise.all alone cannot race blocked HTTP calls",
                "if the host bridge is blocking, reject JS-only hedging as non-transferable; discriminate client-level asynchronous network support from evidence-backed route-origin ordering",
                "run a source-pinned alternate-host A/B without weakening playlist, segment or episode validation or increasing all production timeouts",
                "have Brain generate a reusable repair only after distinguishing Core, ProviderBase, client, provider and network responsibility",
                "rematerialize matching bytes and require returned media plus decoded correct episode, French/multitrack audio and non-regression on official TV before promotion",
            ],
        )

    # A native hard timeout is a completed official test *error* even if the
    # QuickJS console only emitted its call marker. It must never be silently
    # downgraded to a generic deterministic provider replay. This alone does
    # not tell us whether network, bridge, runtime or provider route owns it.
    if (official_tv.get("appSelected") is True
            and official_tv.get("nativeHardTimeoutObserved") is True
            and type(official_tv.get("nativeHardTimeoutMs")) is int
            and official_tv["nativeHardTimeoutMs"] >= 1000):
        return RoutingDecision(
            mode="llm_diagnose",
            reason="official Android TV app-selected provider hit native hard execution timeout; QuickJS call-only is not a completed empty result",
            target_layer="unknown",
            strategy="discriminate_tv_native_hard_timeout_owner",
            prior_confidence=0.80,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=[
                "measure official TV QuickJS Promise control on test-only immediate/awaited media-free fixture",
                "check native fetch completion, HTTP/WAF and DNS versus provider loop deadline on exact source",
                "compare Desktop/native bridge behavior without assuming the user ran the same bundle",
                "fix client/Core/Brain orchestration if shared owner confirmed, else give Brain provider-specific bounded repair tooling",
                "materialize then replay exact TV client for decoded correct title/episode/audio before publication",
            ],
        )

    # The native app DID return media, so do not repair search/extraction again.
    # An independent HLS 403 with no observable video format requires causal
    # investigation of headers, CDN/network and player decode; neither the
    # HTTP probe nor READY can grant current playback or provider mutation.
    if (official_tv.get("appSelected") is True
            and official_tv.get("nativeExtractionPositiveObserved") is True
            and type(official_tv.get("nativeExtractionReturnedCount")) is int
            and official_tv["nativeExtractionReturnedCount"] > 0
            and official_tv.get("playerVideoFormatUnverified") is True
            and 403 in (official_tv.get("independentTerminalHttpStatuses") or [])):
        return RoutingDecision(
            mode="llm_diagnose",
            reason="official Android TV returned media; independent terminal HLS probe got HTTP 403 while player READY lacks decoded video-format proof",
            target_layer="unknown",
            strategy="trace_tv_hls_403_headers_client_fetch_and_decoded_video",
            prior_confidence=0.87,
            requires_llm=True,
            allowed_mutations=[],
            next_actions=[
                "replay exact returned HLS endpoint with production client headers and compare independent probe",
                "discriminate CDN token expiry/WAF, missing Referer/cookie/origin, network egress and client playback path",
                "check actual video frame/audio tracks and correct season/episode identity before granting success",
                "repair Core/Brain/client only if causal owner is proven, never patch provider to hide network probe failure",
                "persist failed attempt and test one representative per topology before extending to provider cohort",
            ],
        )

    # An official native QuickJS call without a completed result, explicit
    # extraction count or classified timeout cannot be treated as a provider
    # candidate failure. The app test need not have a separate human Desktop
    # comparison for this source-pinned incomplete trace to be meaningful.
    if (
        official_tv.get("appSelected") is True
        and official_tv.get("nativeExtractionPositiveObserved") is not True
        and official_tv.get("nativeExtractionZeroObserved") is not True
        and official_tv.get("nativeHardTimeoutObserved") is not True
        and not official_tv.get("quickJsErrors")
        and isinstance(official_tv.get("quickJsPhases"), list)
        and "call" in official_tv["quickJsPhases"]
        and "result" not in official_tv["quickJsPhases"]
    ):
        return RoutingDecision(
            mode="probe",
            reason="official Android TV QuickJS invocation observed without result, extraction verdict, timeout or classified exception",
            target_layer="client",
            strategy="complete_android_tv_quickjs_execution_trace",
            prior_confidence=0.80,
            allowed_mutations=[],
            next_actions=[
                "capture official Android TV QuickJS completion or typed execution error",
                "check runtime cancellation and transport before attributing a provider fault",
                "do not generate provider patch or mark media playable from call-only evidence",
            ],
        )

    # TV is the primary executable client for Brain repair. A reported
    # macOS-positive/TV-missing provider must first have a source-pinned native
    # emulator oracle. Existing Bloc for Desktop/Mobile/iOS remains intact, but
    # no client is presumed to have validated playback merely from build status.
    if _user_client_visibility_differential(request):
        native_tv = _official_android_tv_diagnostic(request)
        if not native_tv:
            # A fresh source-pinned media/identity failure is already causal
            # evidence. Preserve that diagnosis while prioritizing native TV
            # discrimination; don't regress into an endless TV-only probe.
            if failure == "candidate-replay-gap" and current_candidate_identity_gap(request.observations):
                return RoutingDecision(
                    mode="llm_diagnose",
                    reason="current media identity unresolved with a user-reported Android TV visibility difference",
                    target_layer="unknown",
                    strategy="trace_independent_episode_and_hls_provenance",
                    prior_confidence=0.70,
                    requires_llm=True,
                    allowed_mutations=[],
                    next_actions=[
                        "compare provider-owned episode/API selection with returned source metadata",
                        "distinguish provider identity loss, Core projection and incomplete HLS duration",
                        "verify installed manifest projection and exact JS bytes on Android TV",
                        "trace native app media-type selection and QuickJS plugin invocation",
                        "run official Android TV emulator before any mutation or promotion",
                    ],
                )
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
        # A separate FIELD_NATIVE_RESULT count=0 is stronger than a partial
        # QuickJS console. It proves no media was returned in the official
        # app-selected native execution, but does not prove its causal owner.
        if (native_tv.get("appSelected") is True
                and native_tv.get("nativeExtractionZeroObserved") is True):
            return RoutingDecision(
                mode="llm_diagnose",
                reason="source-pinned official Android TV execution returned zero streams independently of incomplete QuickJS console; Mac client reported playable media",
                target_layer="unknown",
                strategy="discriminate_tv_runtime_network_core_vs_provider",
                prior_confidence=0.75,
                requires_llm=True,
                allowed_mutations=[],
                next_actions=[
                    "compare exact TV getStreams input, available metadata and QuickJS runtime capabilities to Desktop",
                    "observe provider-owned detail and episode API before assigning responsibility",
                    "discriminate TV HTTP/WAF and bridge responses from missing player result",
                    "only produce owner-specific Brain tooling/Core/Bloc fix after source-pinned cause",
                    "replay official TV emulator and require correct decoded episode/audio before publication",
                ],
            )
        # An invocation-only trace is not a 0-stream return. The official TV
        # job may have been killed, timed out or lost its completion marker.
        # Diagnose the harness/runtime first; never turn a missing result into
        # a fabricated provider-network or extractor failure.
        phases = native_tv.get("quickJsPhases") or []
        if (native_tv.get("appSelected") is True
                and "call" in phases and "result" not in phases
                and not native_tv.get("quickJsErrors")):
            return RoutingDecision(
                mode="probe",
                reason="official TV QuickJS call was observed but no completed result or classified exception followed",
                target_layer="client",
                strategy="complete_android_tv_quickjs_execution_trace",
                prior_confidence=0.80,
                allowed_mutations=[],
                next_actions=[
                    "inspect TV runner cancellation/timeout, QuickJS task lifecycle and missing completion event",
                    "verify TMDB metadata capability and native fetch bridge in the official emulator build",
                    "repeat source-pinned Android TV invocation and capture a terminal result or error",
                    "preserve Mac/Desktop positive as comparison only; do not patch provider or grant playback",
                ],
            )
        if native_tv.get("appSelected") is True and (
            ("result" in phases and native_tv.get("quickJsReturned") == 0)
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
                    "propose shared client/Core/Bloc correction, not a provider JS override",
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
