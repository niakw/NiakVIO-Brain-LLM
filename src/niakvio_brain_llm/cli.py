from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .backend import LocalOpenAICompatibleBackend
from .contracts import RepairRequest
from .planner import BrainPlanner
from .retrieval import ExperienceStore

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--experience", default="data/experience.jsonl")
    parser.add_argument("--endpoint", default=os.environ.get("NIAKVIO_LLM_ENDPOINT", "http://127.0.0.1:8080"))
    parser.add_argument("--model", default=os.environ.get("NIAKVIO_LLM_MODEL", "niakvio-local"))
    args = parser.parse_args()

    raw = json.loads(Path(args.request).read_text(encoding="utf-8"))
    request = RepairRequest(**raw)
    store = ExperienceStore.from_jsonl(args.experience)
    backend = LocalOpenAICompatibleBackend(base_url=args.endpoint, model=args.model)
    proposal = BrainPlanner(backend, store).plan(request)
    print(json.dumps(proposal.to_dict(), indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
