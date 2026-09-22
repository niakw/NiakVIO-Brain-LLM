#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from niakvio_brain_llm.niakvio_adapter import request_from_checkout
from niakvio_brain_llm.retrieval import ExperienceStore
from niakvio_brain_llm.routing import route_request


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _provider_ids(root: Path) -> list[str]:
    census = _load(root / "automation" / "provider-census-status.json")
    ids = []
    for row in census.get("providers") or []:
        if not isinstance(row, dict):
            continue
        provider = row.get("provider")
        if provider:
            ids.append(str(provider))
    return ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", required=True)
    parser.add_argument("--experience", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument(
        "--include-healthy",
        action="store_true",
        help="Include FULL OK / PARTIAL OK providers in detailed output.",
    )
    args = parser.parse_args()

    root = Path(args.niakvio_root)
    store = ExperienceStore.from_jsonl(args.experience)
    rows = []

    for provider_id in _provider_ids(root):
        request = request_from_checkout(root, provider_id)
        decision = route_request(request, store)
        detail = {
            "provider_id": provider_id,
            "status": request.status,
            "failure_class": request.failure_class,
            **decision.to_dict(),
        }
        if args.include_healthy or decision.mode != "skip":
            rows.append(detail)

    counts = Counter(row["mode"] for row in rows)
    llm_count = sum(1 for row in rows if row["requires_llm"])
    result = {
        "providers_considered": len(_provider_ids(root)),
        "reported": len(rows),
        "requires_llm": llm_count,
        "llm_share_of_reported": round(llm_count / len(rows), 4) if rows else 0.0,
        "modes": dict(sorted(counts.items())),
        "rows": rows,
    }

    encoded = json.dumps(result, indent=2, ensure_ascii=True) + "\n"
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
