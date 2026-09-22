#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from niakvio_brain_llm.batch import batch_summary, load_census, select_batch_targets
from niakvio_brain_llm.niakvio_adapter import request_from_checkout
from niakvio_brain_llm.retrieval import ExperienceStore
from niakvio_brain_llm.routing import route_request

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", required=True)
    parser.add_argument("--experience", required=True)
    parser.add_argument("--mode", choices=("repair", "diagnostic", "brain"), default="repair")
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    selected = select_batch_targets(
        load_census(args.niakvio_root),
        mode=args.mode,
        providers=set(args.provider) or None,
    )
    if args.limit > 0:
        selected = selected[: args.limit]

    store = ExperienceStore.from_jsonl(args.experience)
    rows = []
    modes: Counter[str] = Counter()

    for position, census_row in enumerate(selected, start=1):
        provider = str(census_row["provider"])
        request = request_from_checkout(args.niakvio_root, provider)
        routing = route_request(request, store)
        modes[routing.mode] += 1
        rows.append({
            "position": position,
            "provider": provider,
            "status": request.status,
            "failure_class": request.failure_class,
            "routing": routing.to_dict(),
        })

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )

    llm_targets = sum(
        count for mode, count in modes.items()
        if mode in {"llm_diagnose", "llm_repair"}
    )
    summary = {
        "mode": args.mode,
        **batch_summary(selected),
        "routing_modes": dict(sorted(modes.items())),
        "llm_targets": llm_targets,
        "llm_needed": llm_targets > 0,
    }
    Path(args.summary).write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
