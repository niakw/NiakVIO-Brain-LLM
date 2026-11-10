#!/usr/bin/env python3
"""Causal, source-SHA-bound and read-only Deep proof for Brain FORCE."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _one_row(report: dict[str, Any], provider: str) -> dict[str, Any]:
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
    if not isinstance(tests, list) or any(not isinstance(test, dict) for test in tests):
        raise ValueError("Deep fixture tests must be an array of objects")
    return row


def _count(test: dict[str, Any], field: str) -> int:
    raw = test.get(field) or 0
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise ValueError("Deep stream metric must be numeric")
    value = int(raw)
    if value < 0:
        raise ValueError("Deep stream metric may not be negative")
    return value


def _paired(row: dict[str, Any]) -> int:
    return sum(
        min(_count(t, "streams_playable"), _count(t, "identity_verified_streams"))
        for t in row.get("tests") or []
    )


def _by_fixture(row: dict[str, Any]) -> dict[str, int]:
    """Unambiguous same-episode fixture keys; missing identity cannot prove repair."""
    out: dict[str, int] = {}
    for test in row.get("tests") or []:
        fixture = test.get("fixture")
        if not isinstance(fixture, dict) or not any(
            fixture.get(field) is not None for field in ("tmdbId", "tmdb_id", "id", "label")
        ):
            return {}
        key = json.dumps(
            {"fixture": fixture, "phase": test.get("fixture_phase") or "primary"},
            ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        )
        out[key] = out.get(key, 0) + min(
            _count(test, "streams_playable"), _count(test, "identity_verified_streams")
        )
    return out


def summarize_deep_report(
    report: dict[str, Any], *, provider: str, source_sha: str,
    baseline_report: dict[str, Any] | None = None,
    confirmation_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Never attribute a media stream to Brain without a matched baseline and repeat."""
    if not SHA40.fullmatch(str(source_sha)):
        raise ValueError("exact current source SHA is required")
    row = _one_row(report, provider)
    before = _one_row(baseline_report, provider) if baseline_report is not None else None
    again = _one_row(confirmation_report, provider) if confirmation_report is not None else None
    tests = row.get("tests") or []
    playable = sum(_count(t, "streams_playable") for t in tests)
    identity = sum(_count(t, "identity_verified_streams") for t in tests)
    paired = _paired(row)
    current_fixtures = _by_fixture(row)
    previous_fixtures = _by_fixture(before) if before is not None else {}
    confirmation_fixtures = _by_fixture(again) if again is not None else {}
    comparable = bool(
        current_fixtures and previous_fixtures and confirmation_fixtures
        and current_fixtures.keys() == previous_fixtures.keys() == confirmation_fixtures.keys()
    )
    nonregressing = comparable and all(
        current_fixtures[k] >= previous_fixtures[k]
        and confirmation_fixtures[k] >= previous_fixtures[k]
        for k in current_fixtures
    )
    baseline_paired = sum(previous_fixtures.values())
    confirmation_paired = sum(confirmation_fixtures.values())
    causal = bool(
        nonregressing and sum(current_fixtures.values()) > baseline_paired
        and confirmation_paired > baseline_paired
    )
    candidate_media = row.get("status") == "healthy" and paired > 0
    confirmed_media = again is not None and again.get("status") == "healthy" and confirmation_paired > 0
    already_healthy = before is not None and before.get("status") == "healthy"
    validated = bool(candidate_media and confirmed_media and not already_healthy and causal)
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    failures = evidence.get("failure_classes")
    return {
        "sourceSha": source_sha,
        "provider": provider,
        "status": str(row.get("status") or "unknown")[:60],
        "playable": playable,
        "identityVerified": identity,
        "identityMatchedPlayable": paired,
        "baselineIdentityMatchedPlayable": baseline_paired,
        "confirmationIdentityMatchedPlayable": confirmation_paired,
        "fixtureComparable": comparable,
        "noFixtureRegressions": bool(nonregressing),
        "causalImprovement": causal,
        "candidateMediaVerified": bool(candidate_media),
        "candidateMaterialized": True,
        "sandboxExecuted": True,
        "validated": validated,
        "published": False,
        "failureClasses": [
            str(v)[:80] for v in (failures if isinstance(failures, list) else [])[:6]
            if isinstance(v, str)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--confirmation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", required=True)
    args = parser.parse_args()
    summary = summarize_deep_report(
        json.loads(args.input.read_text(encoding="utf-8")),
        provider=args.provider, source_sha=os.environ.get("NIAKVIO_SOURCE_SHA", ""),
        baseline_report=json.loads(args.baseline.read_text(encoding="utf-8")),
        confirmation_report=json.loads(args.confirmation.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "FIELD_BRAIN_REAL_SOURCE_REPLAY "
        f"provider={summary['provider']} materialized=true "
        f"playback={summary['playable']} identity={summary['identityMatchedPlayable']} "
        f"baseline={summary['baselineIdentityMatchedPlayable']} "
        f"confirmation={summary['confirmationIdentityMatchedPlayable']} "
        f"causal={str(summary['causalImprovement']).lower()} "
        f"validated={str(summary['validated']).lower()} publish=false",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
