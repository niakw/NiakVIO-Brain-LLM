#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from niakvio_brain_llm.advisor_experiments import experiment_fingerprint
from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend
from niakvio_brain_llm.batch import batch_summary, load_census, select_batch_targets
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.niakvio_adapter import request_from_checkout
from niakvio_brain_llm.orchestrator import BrainOrchestrator
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.retrieval import ExperienceStore
from niakvio_brain_llm.repair_family import repair_family_descriptor

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", required=True)
    parser.add_argument("--experience", required=True)
    parser.add_argument("--extra-experience", action="append", default=[])
    parser.add_argument("--documents", required=True)
    parser.add_argument("--extra-documents", action="append", default=[])
    parser.add_argument("--mode", choices=("repair", "diagnostic", "brain"), default="repair")
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--max-hypotheses",
        type=int,
        default=3,
        help="Advisor-only hypotheses per provider. Force remains one concrete edit per provider.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("NIAKVIO_LLM_WORKERS", "2")),
        help="Bounded provider planning concurrency; output order remains deterministic.",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument(
        "--force-provider-budget-seconds",
        type=int,
        default=int(os.environ.get("NIAKVIO_FORCE_PROVIDER_BUDGET_SECONDS", "300")),
        help="Maximum wall-clock budget per provider across all Force scopes and retries.",
    )
    parser.add_argument(
        "--advisor-only",
        action="store_true",
        help="Ask the LLM only for sanitized strategy/experiment guidance; deterministic NiakVIO owns mutations and proof.",
    )
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("NIAKVIO_LLM_ENDPOINT", "http://127.0.0.1:8080"),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("NIAKVIO_LLM_MODEL", "niakvio-local"),
    )
    args = parser.parse_args()

    census = load_census(args.niakvio_root)
    selected = select_batch_targets(
        census,
        mode=args.mode,
        providers=set(args.provider) or None,
    )
    if args.limit > 0:
        selected = selected[: args.limit]

    backend = LocalOpenAICompatibleBackend(
        base_url=args.endpoint,
        model=args.model,
        timeout_seconds=max(30, min(int(args.timeout_seconds), 240)),
        temperature=0.0,
        max_tokens=max(128, min(int(args.max_tokens), 2048)),
        prefill_prompt=(args.mode == "repair" and not args.advisor_only),
    )
    base_store = ExperienceStore.from_jsonl_many(
        [args.experience, *args.extra_experience]
    )
    family_memory_path = Path(args.niakvio_root) / "automation" / "brain-llm-force-memory.json"
    family_experiences: list[dict] = []
    try:
        family_memory = json.loads(family_memory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        family_memory = {}
    if isinstance(family_memory, dict):
        for raw in family_memory.get("validatedFamilies") or []:
            if not isinstance(raw, dict) or int(raw.get("successCount") or 0) <= 0:
                continue
            repair_family = raw.get("repairFamily") if isinstance(raw.get("repairFamily"), dict) else {}
            family_key = str(repair_family.get("key") or "").strip().casefold()
            mechanism = str(raw.get("mechanismFamily") or "").strip().casefold()
            if not re.fullmatch(r"[0-9a-f]{64}", family_key) or not mechanism:
                continue
            family_experiences.append({
                "experience_id": f"validated-family:{family_key}:{mechanism}",
                "failure_class": str(repair_family.get("failure") or ""),
                "strategy": mechanism,
                "mechanismFamily": mechanism,
                "repair_family": repair_family,
                "result": "validated",
                "providers": [str(x) for x in (raw.get("providers") or [])[:96]],
                "successCount": int(raw.get("successCount") or 0),
                "failureCount": int(raw.get("failureCount") or 0),
                "memoryRole": "sandbox-validated-repair-family",
            })
    store = ExperienceStore([*base_store.rows, *family_experiences])
    documents = DocumentStore.from_jsonl_many([args.documents, *args.extra_documents])
    planner = BrainPlanner(backend, store, documents)
    orchestrator = BrainOrchestrator(planner, store)

    def _row(position: int, hypothesis_index: int, provider: str, request, outcome) -> dict:
        family = repair_family_descriptor(request)
        return {
            "position": position,
            "hypothesis_index": hypothesis_index,
            "provider": provider,
            "status": request.status,
            "failure_class": request.failure_class,
            "repair_family": family,
            "ok": True,
            "routing": outcome.routing.to_dict(),
            "proposal": outcome.proposal.to_dict() if outcome.proposal else None,
        }

    def _reserve_advisor_experiment(request, outcome) -> bool:
        proposal = outcome.proposal
        if proposal is None or not isinstance(proposal.experiment, dict) or not proposal.experiment:
            return False
        try:
            fp = experiment_fingerprint(proposal.experiment)
        except Exception:
            return False
        context = copy.deepcopy(request.provider_context or {})
        history = [
            copy.deepcopy(value)
            for value in context.get("advisor_experiment_history") or []
            if isinstance(value, dict)
        ]
        if any(
            str(value.get("llmAdvisorExperimentFingerprint") or "").strip().casefold() == fp
            for value in history
        ):
            return False
        history.append({
            "llmAdvisorExperimentFingerprint": fp,
            "consecutiveFailures": 1,
            "failures": 1,
            "successes": 0,
            "lastOutcome": "candidate_reserved",
            "lastReason": "reserve distinct hypothesis inside current advisor batch",
            "failureClass": request.failure_class,
        })
        context["advisor_experiment_history"] = history[-32:]
        request.provider_context = context
        return True

    def _retryable_force_error(exc: Exception) -> bool:
        return (
            isinstance(exc, TimeoutError)
            or "timed out" in str(exc).casefold()
            or "unterminated string" in str(exc).casefold()
            or "jsondecodeerror" in type(exc).__name__.casefold()
        )

    def _force_rejection_reason(exc: Exception) -> str:
        message = str(exc).casefold()
        for needle, code in (
            ("missing or oversized", "missing_or_oversized"),
            ("placeholder or synthetic", "placeholder_or_synthetic"),
            ("synthetic or non-provider network endpoint", "placeholder_or_synthetic"),
            ("exactly once", "non_unique_anchor"),
            ("no-op", "no_op"),
            ("truncated source fragment", "truncated_fragment"),
            ("function anchor is structurally incomplete", "truncated_fragment"),
            ("javascript syntax validation failed", "syntax_error"),
            ("python syntax validation failed", "syntax_error"),
            ("duplicated javascript control tokens", "duplicated_tokens"),
            ("may not absorb a neighboring helper", "neighbor_absorption"),
            ("helper name collides with current runtime", "helper_collision"),
            ("removes live binding still referenced nearby", "removed_live_binding"),
            ("pure deletion of existing logic", "causally_empty_deletion"),
            ("helper function declaration", "helper_declaration_removed"),
            ("forbidden runtime capability", "forbidden_capability"),
            ("remains ambiguous after causal-focus resolution", "ambiguous_window_occurrence"),
            ("remains ambiguous across causal source windows", "ambiguous_window_occurrence"),
            ("does not occur in any current causal source window", "window_mismatch"),
            ("does not occur in selected source window", "window_mismatch"),
            ("outside request scope", "wrong_scope"),
            ("exact source is unavailable", "missing_source"),
        ):
            if needle in message:
                return code
        return type(exc).__name__.casefold()

    def _force_scope_order(request) -> list[str]:
        context = request.provider_context or {}
        allowed = set(request.allowed_mutations or [])
        scopes: list[str] = []
        failure_key = str(request.failure_class or "").strip().casefold().replace("-", "_")
        bloc_ready = (
            "provider_bloc" in allowed
            and bool(context.get("runtimeMutationSource"))
        )
        registered_patch_sources = (
            context.get("registered_patch_sources")
            if isinstance(context.get("registered_patch_sources"), dict)
            else {}
        )
        patch_ready = "provider_patch" in allowed and bool(registered_patch_sources)
        runtime_patch_ready = patch_ready and any(
            "NIAKVIO_PROVIDER_RUNTIME_RESOLVER_V1" in str(source)
            or "__niakvioProviderRuntimeResolverV1" in str(source)
            or (
                "MANAGED_FIX_ID" in str(source)
                and "PROVIDER." in str(source)
                and ".RUNTIME." in str(source)
            )
            for source in registered_patch_sources.values()
        )

        structural_gap = (
            failure_key in {"route_proven_gap", "chain_terminal_gap", "media_extraction_gap"}
            or str(request.status or "").strip().upper() in {"ROUTE PROVEN", "CHAIN REACHED"}
        )

        # A registered provider-local runtime resolver is more causally specific
        # than the generic generated runtime. Repair that authored surface first.
        # Bloc-first remains the fallback for structural gaps without a dedicated
        # runtime resolver, or after the dedicated surface abstains/rejects.
        if runtime_patch_ready and structural_gap:
            scopes.append("provider_patch")
        if bloc_ready and structural_gap:
            scopes.append("provider_bloc")

        if patch_ready and "provider_patch" not in scopes:
            scopes.append("provider_patch")
        elif not patch_ready and "provider_js" in allowed and context.get("authored_module"):
            scopes.append("provider_js")
        elif (
            not patch_ready
            and not ("provider_js" in allowed and context.get("authored_module"))
            and "provider_data" in allowed
            and (context.get("override") or context.get("hub"))
        ):
            scopes.append("provider_data")

        if bloc_ready and "provider_bloc" not in scopes:
            scopes.append("provider_bloc")
        return list(dict.fromkeys(scopes))

    def _run_force_scope(
        position: int,
        provider: str,
        base_request,
        scope: str,
        force_deadline: float,
    ):
        scoped_request = copy.deepcopy(base_request)
        scoped_request.advisor_only = False
        scoped_request.allowed_mutations = [scope]

        scope_token_cap = {
            "provider_data": 192,
            "provider_patch": 640,
            "provider_js": 640,
            "provider_bloc": 448,
        }.get(scope, 320)
        recovery_token_cap = {
            "provider_data": 256,
            "provider_patch": 768,
            "provider_js": 768,
            "provider_bloc": 768,
        }.get(scope, 384)
        primary_tokens = max(128, min(int(args.max_tokens), scope_token_cap))
        retry_tokens = max(primary_tokens, min(int(args.max_tokens), recovery_token_cap))
        validation_timeout = max(
            60,
            min(int(args.timeout_seconds), 120 if scope == "provider_bloc" else 90),
        )
        primary_timeout = max(
            45,
            min(int(args.timeout_seconds), 180),
        )
        transport_timeout = max(
            90,
            min(int(args.timeout_seconds), 180),
        )
        max_validation_corrections = 3 if scope == "provider_bloc" else 1

        def _remaining_timeout(desired: int) -> int:
            remaining = force_deadline - time.monotonic()
            if remaining < 5:
                raise TimeoutError("force provider budget exhausted")
            return max(5, min(int(desired), int(remaining)))

        def _run_once(request, *, timeout_seconds: int, max_tokens: int):
            bounded_timeout = _remaining_timeout(timeout_seconds)
            retry_backend = LocalOpenAICompatibleBackend(
                base_url=args.endpoint,
                model=args.model,
                timeout_seconds=bounded_timeout,
                temperature=0.0,
                max_tokens=max_tokens,
                # cache_prompt on the real constrained request already persists
                # the evaluated prefix for identical retries. An explicit
                # one-token prefill only adds another request on CPU runners.
                prefill_prompt=False,
            )
            return BrainOrchestrator(
                BrainPlanner(retry_backend, store, documents),
                store,
            ).run(request, compact_force=True)

        def _run_retry(request, *, timeout_seconds: int):
            return _run_once(
                request,
                timeout_seconds=timeout_seconds,
                max_tokens=retry_tokens,
            )

        def _validation_feedback(request, exc: ValueError, correction_index: int):
            reason = _force_rejection_reason(exc)
            retry_request = copy.deepcopy(request)
            instructions = {
                "syntax_error": (
                    "previous edit broke syntax; change only one complete expression "
                    "or statement copied from the selected window, preserve surrounding "
                    "quotes/braces/parentheses and never emit a partial function declaration"
                ),
                "window_mismatch": (
                    "previous find was not present in the chosen causal window; copy the "
                    "smallest exact current-byte find from one provided window and keep the "
                    "same causal intent, or abstain"
                ),
                "ambiguous_window_occurrence": (
                    "previous anchor remained structurally ambiguous; choose a smaller exact "
                    "current-byte expression nearest the causal operation, or abstain"
                ),
                "placeholder_or_synthetic": (
                    "never invent a URL, host, route, token, header value or placeholder; "
                    "use only concrete current-source facts, otherwise abstain"
                ),
                "truncated_fragment": (
                    "previous edit used a truncated function fragment; choose one complete "
                    "expression or statement and preserve helper/function boundaries"
                ),
                "neighbor_absorption": (
                    "previous replacement absorbed neighboring helper code; edit only the "
                    "minimal expression or statement inside the intended helper"
                ),
                "helper_collision": (
                    "previous Bloc redeclared a helper that already exists in the current runtime; "
                    "reuse/call the existing helper instead of declaring it again, and change only "
                    "the selected statement or add a uniquely named helper if genuinely required"
                ),
                "helper_declaration_removed": (
                    "the selected unit is a complete existing function; preserve its exact original "
                    "function name/signature and change only its body/logic. Brain will preserve the "
                    "declaration envelope when you return only the new body"
                ),
                "removed_live_binding": (
                    "previous edit removed a local variable that later code still uses; preserve or "
                    "replace that binding and make the repair behavior explicit instead of deleting it"
                ),
                "causally_empty_deletion": (
                    "previous traversal repair only deleted existing logic; add or replace concrete "
                    "route/player/terminal traversal behavior on the selected unit, or abstain"
                ),
            }
            feedback = {
                "stage": "force_validation_feedback",
                "reason": reason,
                "correction_index": correction_index,
                "instruction": instructions.get(
                    reason,
                    "previous edit rejected; choose a materially different minimal exact "
                    "window-local edit in the same scope or abstain",
                ),
            }
            existing_observations = [
                row for row in list(retry_request.observations or [])
                if isinstance(row, dict)
            ]
            prior_feedback = [
                row for row in existing_observations
                if str(row.get("stage") or "") == "force_validation_feedback"
            ][:1]
            required_evidence = [
                row for row in existing_observations
                if str(row.get("source") or "").strip().casefold()
                in {"census_current", "targeted-regression-current"}
            ]
            retained = [feedback, *prior_feedback, *required_evidence]
            seen = set()
            retry_request.observations = []
            for row in retained:
                fingerprint = (
                    str(row.get("stage") or ""),
                    str(row.get("source") or ""),
                    str(row.get("reason") or ""),
                )
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                retry_request.observations.append(row)
            print(
                "FIELD_BRAIN_FORCE_SCOPE_FEEDBACK "
                f"provider={provider} scope={scope} reason={reason} "
                f"correction={correction_index}/{max_validation_corrections}",
                flush=True,
            )
            return retry_request

        def _run_validation_chain(request, first_exc: ValueError):
            current_request = request
            current_exc = first_exc
            for correction_index in range(1, max_validation_corrections + 1):
                retry_request = _validation_feedback(
                    current_request,
                    current_exc,
                    correction_index,
                )
                try:
                    corrected = _run_retry(
                        retry_request,
                        timeout_seconds=validation_timeout,
                    )
                    return _row(position, 1, provider, retry_request, corrected), None
                except ValueError as validation_exc:
                    current_request = retry_request
                    current_exc = validation_exc
                    if correction_index >= max_validation_corrections:
                        return None, validation_exc
                    continue
                except Exception as retry_exc:
                    return None, retry_exc
            return None, current_exc

        try:
            outcome = _run_once(
                scoped_request,
                timeout_seconds=primary_timeout,
                max_tokens=primary_tokens,
            )
            return _row(position, 1, provider, scoped_request, outcome), None
        except ValueError as validation_exc:
            return _run_validation_chain(scoped_request, validation_exc)
        except Exception as exc:
            if not _retryable_force_error(exc):
                return None, exc
            transport_request = copy.deepcopy(scoped_request)
            try:
                retry = _run_once(
                    transport_request,
                    timeout_seconds=transport_timeout,
                    max_tokens=primary_tokens,
                )
                return _row(position, 1, provider, transport_request, retry), None
            except ValueError as validation_exc:
                # A transport retry can finally return parseable code that is
                # structurally invalid. Preserve the same bounded validation
                # correction chain instead of dropping that useful progress.
                return _run_validation_chain(transport_request, validation_exc)
            except Exception as retry_exc:
                return None, retry_exc

    def plan_one(position: int, census_row: dict) -> list[dict]:
        provider = str(census_row["provider"])
        request = request_from_checkout(args.niakvio_root, provider)
        request.advisor_only = bool(args.advisor_only)
        max_hypotheses = (
            max(1, min(int(args.max_hypotheses or request.max_hypotheses or 1), 3))
            if args.advisor_only
            else 1
        )
        planned: list[dict] = []

        if args.mode == "repair" and not args.advisor_only:
            scopes = _force_scope_order(request)
            last_error: Exception | None = None
            last_row: dict | None = None
            scope_trace: list[dict[str, object]] = []
            budget_cap = max(60, min(int(args.force_provider_budget_seconds), 900))
            failure_key = str(request.failure_class or "").strip().casefold().replace("-", "_")
            status_key = str(request.status or "").strip().upper()
            if failure_key in {"chain_terminal_gap", "media_extraction_gap"} or status_key == "CHAIN REACHED":
                budget_seconds = budget_cap
            elif failure_key == "route_proven_gap" or status_key == "ROUTE PROVEN":
                budget_seconds = min(budget_cap, 600)
            elif failure_key == "provider_transport_gap":
                budget_seconds = min(budget_cap, 300)
            elif failure_key == "transport_environment_gap":
                budget_seconds = min(budget_cap, 180)
            else:
                budget_seconds = min(budget_cap, 150)
            budget_seconds = max(60, budget_seconds)
            print(
                "FIELD_BRAIN_FORCE_PROVIDER_BUDGET "
                f"provider={provider} failure={failure_key or 'unknown'} status={status_key or 'unknown'} "
                f"budget_seconds={budget_seconds} cap_seconds={budget_cap}",
                flush=True,
            )
            force_deadline = time.monotonic() + budget_seconds
            for scope in scopes:
                if time.monotonic() >= force_deadline:
                    last_error = TimeoutError("force provider budget exhausted")
                    scope_trace.append({
                        "scope": scope,
                        "outcome": "budget_exhausted",
                        "reason": "provider_budget_exhausted",
                    })
                    print(
                        "FIELD_BRAIN_FORCE_PROVIDER_BUDGET_EXHAUSTED "
                        f"provider={provider} budget_seconds={budget_seconds}",
                        flush=True,
                    )
                    break
                row, error = _run_force_scope(
                    position,
                    provider,
                    request,
                    scope,
                    force_deadline,
                )
                if error is not None:
                    last_error = error
                    rejection_reason = _force_rejection_reason(error)
                    scope_trace.append({
                        "scope": scope,
                        "outcome": "rejected",
                        "reason": rejection_reason,
                        "errorType": type(error).__name__,
                    })
                    error_detail = re.sub(r"[^a-zA-Z0-9._:/ -]+", "_", str(error).strip())[:240] or "unspecified"
                    print(
                        "FIELD_BRAIN_FORCE_SCOPE_REJECTED "
                        f"provider={provider} scope={scope} error={type(error).__name__} "
                        f"reason={rejection_reason} detail={error_detail}",
                        flush=True,
                    )
                    continue
                if row is None:
                    continue
                last_row = row
                proposal = row.get("proposal") if isinstance(row, dict) else None
                mutations = proposal.get("mutations") if isinstance(proposal, dict) else None
                if isinstance(mutations, list) and mutations:
                    scope_trace.append({
                        "scope": scope,
                        "outcome": "selected",
                        "reason": "executable_mutation",
                    })
                    row["force_scope_trace"] = copy.deepcopy(scope_trace)
                    print(
                        "FIELD_BRAIN_FORCE_SCOPE_SELECTED "
                        f"provider={provider} scope={scope}",
                        flush=True,
                    )
                    return [row]
                abstain_reason = ""
                if isinstance(proposal, dict):
                    abstain_reason = str(proposal.get("abstain_reason") or "")
                safe_reason = re.sub(r"[^a-zA-Z0-9._:-]+", "_", abstain_reason.strip())[:160] or "unspecified"
                scope_trace.append({
                    "scope": scope,
                    "outcome": "abstain",
                    "reason": safe_reason,
                })
                print(
                    "FIELD_BRAIN_FORCE_SCOPE_ABSTAIN "
                    f"provider={provider} scope={scope} reason={safe_reason}",
                    flush=True,
                )
            if last_row is not None:
                last_row["force_scope_trace"] = copy.deepcopy(scope_trace)
                return [last_row]
            exc = last_error or RuntimeError("no bounded Force mutation scope is available")
            return [{
                "position": position,
                "hypothesis_index": 1,
                "provider": provider,
                "status": request.status,
                "failure_class": request.failure_class,
                "repair_family": repair_family_descriptor(request),
                "ok": False,
                "error": type(exc).__name__ + ": " + str(exc),
                "force_scope_trace": copy.deepcopy(scope_trace),
            }]

        try:
            for hypothesis_index in range(1, max_hypotheses + 1):
                outcome = orchestrator.run(request, compact_force=False)
                planned.append(_row(position, hypothesis_index, provider, request, outcome))
                if not args.advisor_only:
                    break
                if not _reserve_advisor_experiment(request, outcome):
                    break
            return planned
        except Exception as exc:
            planned.append({
                "position": position,
                "hypothesis_index": len(planned) + 1,
                "provider": provider,
                "status": request.status,
                "failure_class": request.failure_class,
                "repair_family": repair_family_descriptor(request),
                "ok": False,
                "error": type(exc).__name__ + ": " + str(exc),
            })
            return planned

    workers = max(1, min(int(args.workers or 1), 8, len(selected) or 1))
    rows: list[dict] = []
    if workers == 1:
        for position, census_row in enumerate(selected, start=1):
            rows.extend(plan_one(position, census_row))
    else:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="niakvio-llm") as pool:
            futures = {
                pool.submit(plan_one, position, census_row): position
                for position, census_row in enumerate(selected, start=1)
            }
            for future in as_completed(futures):
                rows.extend(future.result())
        rows.sort(key=lambda row: (int(row["position"]), int(row.get("hypothesis_index") or 1)))

    routing_modes: Counter[str] = Counter()
    llm_calls = 0
    for row in rows:
        routing = row.get("routing")
        if not isinstance(routing, dict):
            continue
        mode = str(routing.get("mode") or "")
        if mode:
            routing_modes[mode] += 1
        llm_calls += int(bool(routing.get("requires_llm")))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )

    safe_errors = []
    for row in rows:
        if row.get("ok") is not False:
            continue
        message = str(row.get("error") or "")
        message = __import__("re").sub(r"https?://[^\\s]+", "<url>", message)
        message = __import__("re").sub(
            r"(?i)(?:authorization|cookie|token|secret|password|api[_-]?key)\\s*[:=]\\s*[^\\s,;]+",
            "<credential-omitted>",
            message,
        )
        safe_errors.append({
            "provider": str(row.get("provider") or ""),
            "error": message[:600],
        })
    if safe_errors:
        print("FIELD_BRAIN_FORCE_PLAN_ERRORS " + json.dumps(safe_errors, ensure_ascii=True))

    repair_family_counts: Counter[str] = Counter()
    repair_family_keys: set[str] = set()
    for row in rows:
        family = row.get("repair_family")
        if not isinstance(family, dict):
            continue
        key = str(family.get("key") or "")
        archetype = str(family.get("archetype") or key or "unknown")
        if key:
            repair_family_keys.add(key)
        repair_family_counts[archetype] += 1

    summary = {
        "mode": args.mode,
        **batch_summary(selected),
        "planned": sum(1 for row in rows if row["ok"]),
        "plannedProviders": len({str(row.get("provider") or "") for row in rows if row.get("ok") is True}),
        "plannedHypotheses": sum(1 for row in rows if row.get("ok") is True),
        "maxHypothesesPerProvider": max(1, min(int(args.max_hypotheses or 1), 3)) if args.advisor_only else 1,
        "errors": sum(1 for row in rows if not row["ok"]),
        "model_processes": 1,
        "parallel_workers": workers,
        "llm_calls": llm_calls,
        "llm_call_rate": (llm_calls / len(selected)) if selected else 0.0,
        "repairFamilyCount": len(repair_family_keys),
        "repairFamilies": dict(sorted(repair_family_counts.items(), key=lambda item: (-item[1], item[0]))),
        "providersPerRepairFamily": (len(selected) / len(repair_family_keys)) if repair_family_keys else 0.0,
        "routing_modes": dict(sorted(routing_modes.items())),
        "ordered_by": "evidence_depth",
        "experience_sources": 1 + len(args.extra_experience),
        "validatedFamilyExperiences": len(family_experiences),
        "document_sources": 1 + len(args.extra_documents),
    }
    print(json.dumps(summary, sort_keys=True))
    return 2 if args.strict and summary["errors"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
