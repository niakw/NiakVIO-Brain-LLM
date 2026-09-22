#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os

from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend
from niakvio_brain_llm.niakvio_adapter import request_from_checkout
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.retrieval import ExperienceStore

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--experience", required=True)
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("NIAKVIO_LLM_ENDPOINT", "http://127.0.0.1:8080"),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("NIAKVIO_LLM_MODEL", "niakvio-local"),
    )
    args = parser.parse_args()

    request = request_from_checkout(args.niakvio_root, args.provider)
    planner = BrainPlanner(
        LocalOpenAICompatibleBackend(
            base_url=args.endpoint,
            model=args.model,
            timeout_seconds=240,
            temperature=0.0,
        ),
        ExperienceStore.from_jsonl(args.experience),
    )
    proposal = planner.plan(request)
    print(json.dumps({
        "request": {
            "provider_id": request.provider_id,
            "failure_class": request.failure_class,
            "status": request.status,
        },
        "proposal": proposal.to_dict(),
        "authority": "proposal_only",
    }, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
