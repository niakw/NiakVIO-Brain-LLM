#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend
from niakvio_brain_llm.contracts import RepairRequest, TARGET_LAYERS
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.retrieval import ExperienceStore

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="qwen")
    parser.add_argument("--experience", required=True)
    args = parser.parse_args()

    request = RepairRequest(
        provider_id="movix-smoke",
        failure_class="api_discovery_gap",
        status="NO PROOF",
        supported_types=["movie", "tv"],
        observations=[
            {"signal": "fixed endpoint returns 403"},
            {"signal": "provider frontend remains reachable"},
            {"signal": "current JS bundle may expose a replacement API"},
        ],
        provider_context={"read_only": True, "purpose": "model-contract-smoke"},
    )

    planner = BrainPlanner(
        LocalOpenAICompatibleBackend(
            base_url=args.endpoint,
            model=args.model,
            timeout_seconds=180,
            temperature=0.0,
        ),
        ExperienceStore.from_jsonl(args.experience),
    )
    proposal = planner.plan(request)

    assert proposal.provider_id == request.provider_id
    assert proposal.target_layer in TARGET_LAYERS
    assert proposal.strategy or proposal.abstain
    print(json.dumps(proposal.to_dict(), indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
