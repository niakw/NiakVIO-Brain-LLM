#!/usr/bin/env python3
"""Sanitized, strictly non-publishing deep replay verdict for Brain CPU challenger."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

SHA40 = re.compile(r"^[0-9a-f]{40}$")


def summarize_deep_report(report: dict[str, Any], *, provider: str, source_sha: str) -> dict[str, Any]:
    """Use the actual sandbox checkout SHA, never the health report environment string.

    A single fixture must carry both playable and matching-content evidence;
    pooling unrelated fixture counts can falsely validate incorrect episodes.
    """
    if not SHA40.fullmatch(str(source_sha)):
        raise ValueError("exact current source SHA is required")
    if not isinstance(report, dict):
        raise ValueError("Deep report must be an object")
    results = report.get("results")
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        raise ValueError("Deep report must contain exactly one provider result")
    row = results[0]
    key = str(row.get("key") or "")
    if key.rsplit(":", 1)[-1].casefold() != provider.casefold():
        raise ValueError("Deep result provider identity does not match requested provider")
    tests = row.get("tests")
    if not isinstance(tests, list):
        raise ValueError("Deep result fixture tests must be an array")
    if any(not isinstance(test, dict) for test in tests):
        raise ValueError("Deep fixture tests must be objects")
    def count(test: dict[str, Any], field: str) -> int:
        raw = test.get(field) or 0
        if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
            raise ValueError("Deep stream metric must be numeric")
        n = int(raw)
        if n < 0:
            raise ValueError("Deep stream metric may not be negative")
        return n
    playable = sum(count(test, "streams_playable") for test in tests)
    identity = sum(count(test, "identity_verified_streams") for test in tests)
    paired = sum(min(count(test, "streams_playable"), count(test, "identity_verified_streams"))
                 for test in tests)
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    failures = evidence.get("failure_classes")
    return {
        "sourceSha": source_sha,
        "provider": provider,
        "status": str(row.get("status") or "unknown")[:60],
        "playable": playable,
        "identityVerified": identity,
        "identityMatchedPlayable": paired,
        "candidateMaterialized": True,
        "sandboxExecuted": True,
        "validated": paired > 0 and str(row.get("status") or "") == "healthy",
        "published": False,
        "failureClasses": [
            str(v)[:80] for v in (failures if isinstance(failures, list) else [])[:6]
            if isinstance(v, str)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", required=True)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    summary = summarize_deep_report(
        report, provider=args.provider,
        source_sha=os.environ.get("NIAKVIO_SOURCE_SHA", ""),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(
        "FIELD_BRAIN_REAL_SOURCE_REPLAY "
        f"provider={summary['provider']} materialized=true "
        f"playback={summary['playable']} identity={summary['identityMatchedPlayable']} "
        f"validated={str(summary['validated']).lower()} publish=false",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
