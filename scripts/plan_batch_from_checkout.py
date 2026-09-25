#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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

    def plan_one(position: int, census_row: dict) -> dict:
        provider = str(census_row["provider"])
        request = request_from_checkout(args.niakvio_root, provider)
        request.advisor_only = bool(args.advisor_only)
        try:
            outcome = orchestrator.run(request)
            return {
                "position": position,
                "provider": provider,
                "status": request.status,
                "failure_class": request.failure_class,
                "ok": True,
                "routing": outcome.routing.to_dict(),
                "proposal": outcome.proposal.to_dict() if outcome.proposal else None,
            }
        except Exception as exc:
            timed_out = isinstance(exc, TimeoutError) or "timed out" in str(exc).casefold()
            if timed_out and not args.advisor_only:
                retry_backend = LocalOpenAICompatibleBackend(
                    base_url=args.endpoint,
                    model=args.model,
                    timeout_seconds=240,
                    temperature=0.0,
                    max_tokens=max(128, min(int(args.max_tokens), 160)),
                )
                retry_request = request_from_checkout(args.niakvio_root, provider)
                retry_request.advisor_only = False
                try:
                    retry = BrainOrchestrator(
                        BrainPlanner(retry_backend, store, documents),
                        store,
                    ).run(retry_request)
                    return {
                        "position": position,
                        "provider": provider,
                        "status": retry_request.status,
                        "failure_class": retry_request.failure_class,
                        "ok": True,
                        "routing": retry.routing.to_dict(),
                        "proposal": retry.proposal.to_dict() if retry.proposal else None,
                    }
                except Exception as retry_exc:
                    exc = retry_exc
            return {
                "position": position,
                "provider": provider,
                "status": request.status,
                "failure_class": request.failure_class,
                "ok": False,
                "error": type(exc).__name__ + ": " + str(exc),
            }

    workers = max(1, min(int(args.workers or 1), 8, len(selected) or 1))
    rows: list[dict] = []
    if workers == 1:
        rows = [
            plan_one(position, census_row)
            for position, census_row in enumerate(selected, start=1)
        ]
    else:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="niakvio-llm") as pool:
            futures = {
                pool.submit(plan_one, position, census_row): position
                for position, census_row in enumerate(selected, start=1)
            }
            for future in as_completed(futures):
                rows.append(future.result())
        rows.sort(key=lambda row: int(row["position"]))

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
