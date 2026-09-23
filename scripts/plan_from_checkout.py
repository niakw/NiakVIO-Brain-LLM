#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os

from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.niakvio_adapter import request_from_checkout
from niakvio_brain_llm.orchestrator import BrainOrchestrator
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.retrieval import ExperienceStore

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--experience", required=True)
    parser.add_argument("--extra-experience", action="append", default=[])
    parser.add_argument("--documents", default="")
    parser.add_argument("--extra-documents", action="append", default=[])
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("NIAKVIO_LLM_ENDPOINT", "http://127.0.0.1:8080"),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("NIAKVIO_LLM_MODEL", "qwen2.5-coder-3b"),
    )
    args = parser.parse_args()

    request = request_from_checkout(args.niakvio_root, args.provider)
    store = ExperienceStore.from_jsonl_many(
        [args.experience, *args.extra_experience]
    )
    document_paths = ([args.documents] if args.documents else []) + list(args.extra_documents)
    documents = (
        DocumentStore.from_jsonl_many(document_paths)
        if document_paths
        else DocumentStore([])
    )
    planner = BrainPlanner(
        LocalOpenAICompatibleBackend(
            base_url=args.endpoint,
            model=args.model,
            timeout_seconds=240,
            temperature=0.0,
        ),
        store,
        documents,
    )
    outcome = BrainOrchestrator(planner, store).run(request)

    print(json.dumps({
        "request": {
            "provider_id": request.provider_id,
            "failure_class": request.failure_class,
            "status": request.status,
        },
        "routing": outcome.routing.to_dict(),
        "proposal": outcome.proposal.to_dict() if outcome.proposal else None,
        "authority": "proposal_only",
        "source_repo_mode": "read_only",
    }, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
