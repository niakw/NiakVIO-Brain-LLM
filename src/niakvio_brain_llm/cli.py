from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .backend import LocalOpenAICompatibleBackend
from .contracts import RepairRequest
from .document_memory import DocumentStore
from .orchestrator import BrainOrchestrator
from .planner import BrainPlanner
from .retrieval import ExperienceStore

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the standalone NiakVIO Brain on one bounded repair request."
    )
    parser.add_argument("--request", required=True)
    parser.add_argument("--experience", default="data/experience.jsonl")
    parser.add_argument("--documents", default="data/documents.jsonl")
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("NIAKVIO_LLM_ENDPOINT", "http://127.0.0.1:8080"),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("NIAKVIO_LLM_MODEL", "niakvio-local"),
    )
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    raw = json.loads(Path(args.request).read_text(encoding="utf-8"))
    request = RepairRequest(**raw)

    store = ExperienceStore.from_jsonl(args.experience)
    documents = DocumentStore.from_jsonl(args.documents)
    backend = LocalOpenAICompatibleBackend(
        base_url=args.endpoint,
        model=args.model,
        timeout_seconds=args.timeout,
        temperature=0.0,
    )
    planner = BrainPlanner(backend, store, documents)
    outcome = BrainOrchestrator(planner, store).run(request)

    print(json.dumps(outcome.to_dict(), indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
