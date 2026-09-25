#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
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
    )
    store = ExperienceStore.from_jsonl_many(
        [args.experience, *args.extra_experience]
    )
    documents = DocumentStore.from_jsonl_many([args.documents, *args.extra_documents])
    planner = BrainPlanner(backend, store, documents)
    orchestrator = BrainOrchestrator(planner, store)

    def _row(position: int, hypothesis_index: int, provider: str, request, outcome) -> dict:
        return {
            "position": position,
            "hypothesis_index": hypothesis_index,
            "provider": provider,
            "status": request.status,
            "failure_class": request.failure_class,
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
        try:
            compact_force = args.mode == "repair" and not args.advisor_only
            for hypothesis_index in range(1, max_hypotheses + 1):
                outcome = orchestrator.run(request, compact_force=compact_force)
                planned.append(_row(position, hypothesis_index, provider, request, outcome))
                if not args.advisor_only:
                    break
                if not _reserve_advisor_experiment(request, outcome):
                    break
            return planned
        except Exception as exc:
            retryable = (
                isinstance(exc, TimeoutError)
                or "timed out" in str(exc).casefold()
                or "unterminated string" in str(exc).casefold()
                or "jsondecodeerror" in type(exc).__name__.casefold()
            )
            if retryable and not args.advisor_only:
                retry_backend = LocalOpenAICompatibleBackend(
                    base_url=args.endpoint,
                    model=args.model,
                    timeout_seconds=120,
                    temperature=0.0,
                    max_tokens=max(128, min(int(args.max_tokens), 256)),
                )
                retry_request = request_from_checkout(args.niakvio_root, provider)
                retry_request.advisor_only = False
                try:
                    retry = BrainOrchestrator(
                        BrainPlanner(retry_backend, store, documents),
                        store,
                    ).run(retry_request, compact_force=True)
                    return [_row(position, 1, provider, retry_request, retry)]
                except Exception as retry_exc:
                    exc = retry_exc
            planned.append({
                "position": position,
                "hypothesis_index": len(planned) + 1,
                "provider": provider,
                "status": request.status,
                "failure_class": request.failure_class,
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
        "routing_modes": dict(sorted(routing_modes.items())),
        "ordered_by": "evidence_depth",
        "experience_sources": 1 + len(args.extra_experience),
        "document_sources": 1 + len(args.extra_documents),
    }
    print(json.dumps(summary, sort_keys=True))
    return 2 if args.strict and summary["errors"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
