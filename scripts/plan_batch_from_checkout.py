#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
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
    parser.add_argument("--output", required=True)
    parser.add_argument("--strict", action="store_true")
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
        timeout_seconds=240,
        temperature=0.0,
    )
    store = ExperienceStore.from_jsonl_many(
        [args.experience, *args.extra_experience]
    )
    planner = BrainPlanner(
        backend,
        store,
        DocumentStore.from_jsonl_many([args.documents, *args.extra_documents]),
    )
    orchestrator = BrainOrchestrator(planner, store)

    rows = []
    routing_modes: Counter[str] = Counter()
    llm_calls = 0

    for position, census_row in enumerate(selected, start=1):
        provider = str(census_row["provider"])
        request = request_from_checkout(args.niakvio_root, provider)
        try:
            outcome = orchestrator.run(request)
            routing_modes[outcome.routing.mode] += 1
            llm_calls += int(outcome.routing.requires_llm)
            rows.append({
                "position": position,
                "provider": provider,
                "status": request.status,
                "failure_class": request.failure_class,
                "ok": True,
                "routing": outcome.routing.to_dict(),
                "proposal": outcome.proposal.to_dict() if outcome.proposal else None,
            })
        except Exception as exc:
            rows.append({
                "position": position,
                "provider": provider,
                "status": request.status,
                "failure_class": request.failure_class,
                "ok": False,
                "error": type(exc).__name__ + ": " + str(exc),
            })

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )

    summary = {
        "mode": args.mode,
        **batch_summary(selected),
        "planned": sum(1 for row in rows if row["ok"]),
        "errors": sum(1 for row in rows if not row["ok"]),
        "model_processes": 1,
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
