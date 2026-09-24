#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SAFE_FALSE_KEYS = (
    "publicationAuthority",
    "directMutationAuthority",
    "proofAuthority",
    "rawMutationContentRetained",
    "privateContentRetained",
)

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("guidance payload must be an object")
    return value

def provider_ids(payload: dict[str, Any]) -> set[str]:
    return {
        str(row.get("providerId") or "").strip().casefold().replace("_", "-")
        for row in payload.get("rows") or []
        if isinstance(row, dict) and str(row.get("providerId") or "").strip()
    }

def safe(payload: dict[str, Any]) -> bool:
    return all(payload.get(key) is False for key in SAFE_FALSE_KEYS)

def choose(previous: dict[str, Any], candidate: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if not safe(candidate):
        raise ValueError("candidate guidance safety flags are invalid")
    if not safe(previous):
        return candidate, "previous_unsafe"
    previous_source = str(previous.get("sourceNiakvioSha") or "")
    candidate_source = str(candidate.get("sourceNiakvioSha") or "")
    if not previous_source or previous_source != candidate_source:
        return candidate, "source_changed"
    previous_ids = provider_ids(previous)
    candidate_ids = provider_ids(candidate)
    lost = sorted(previous_ids - candidate_ids)
    if lost:
        return previous, "coverage_regression:" + ",".join(lost)
    return candidate, "coverage_non_regression"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    previous = load(args.previous)
    candidate = load(args.candidate)
    selected, reason = choose(previous, candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(selected, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "FIELD_NIAKVIO_GUIDANCE_PUBLICATION "
        f"reason={reason} previous={len(provider_ids(previous))} "
        f"candidate={len(provider_ids(candidate))} selected={len(provider_ids(selected))}"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
