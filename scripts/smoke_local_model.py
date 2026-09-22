#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend
from niakvio_brain_llm.contracts import RepairRequest, TARGET_LAYERS
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.retrieval import ExperienceStore


class RecordingBackend:
    def __init__(self, inner: LocalOpenAICompatibleBackend):
        self.inner = inner
        self.last_response = ""

    def complete(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        self.last_response = self.inner.complete(
            system=system,
            user=user,
            response_schema=response_schema,
        )
        return self.last_response


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="qwen")
    parser.add_argument("--experience", required=True)
    parser.add_argument("--documents", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    request = RepairRequest(
        provider_id="movix",
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

    backend = RecordingBackend(LocalOpenAICompatibleBackend(
        base_url=args.endpoint,
        model=args.model,
        timeout_seconds=180,
        temperature=0.0,
    ))
    planner = BrainPlanner(
        backend,
        ExperienceStore.from_jsonl(args.experience),
        DocumentStore.from_jsonl(args.documents),
    )

    report: dict[str, Any] = {
        "ok": False,
        "model": args.model,
        "request": {
            "provider_id": request.provider_id,
            "failure_class": request.failure_class,
        },
    }

    exit_code = 0
    try:
        proposal = planner.plan(request)
        assert proposal.provider_id == request.provider_id
        assert proposal.target_layer in TARGET_LAYERS
        assert proposal.strategy or proposal.abstain
        report["ok"] = True
        report["proposal"] = proposal.to_dict()
    except Exception as exc:
        exit_code = 1
        report["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if backend.last_response:
            try:
                report["raw_model_response"] = json.loads(backend.last_response)
            except json.JSONDecodeError:
                report["raw_model_response"] = backend.last_response[:12000]

    Path(args.output).write_text(
        json.dumps(report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
