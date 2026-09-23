#!/usr/bin/env python3
"""Publish a minimal, non-sensitive NiakVIO advisor surface.

Raw private documents and model explanations never leave the workflow.  Only a
provider-local, allowlisted hypothesis-ordering prior is retained.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

STRATEGY_TO_PROFILE = {
    "provider-owned-origin-header-and-domain-replay": "provider_origin_failover_v1",
    "search-detail-player-terminal-traversal": "proven_route_terminal_traversal_v1",
    "terminal-media-extractor-with-playback-validation": "chain_terminal_extractor_v1",
    "same-provider-candidate-program-replay": "retained_candidate_replay_v1",
    "proven-request-program-and-terminal-extraction": "player_media_extractor_v1",
    "discover-api-from-current-page-and-bundles": "search_contract_inference_v1",
}
ALLOWED_PROFILES = frozenset(STRATEGY_TO_PROFILE.values())
PROVIDER_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,159}$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def canon(value: object) -> str:
    return str(value or "").strip().casefold().replace("_", "-")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            rows.append(value)
    return rows


def sanitize(
    rows: list[dict[str, Any]],
    *,
    niakvio_sha: str,
    brain_llm_sha: str,
    min_confidence: float = 0.80,
) -> dict[str, Any]:
    niakvio_sha = str(niakvio_sha or "").strip().casefold()
    brain_llm_sha = str(brain_llm_sha or "").strip().casefold()
    if not SHA40.fullmatch(niakvio_sha) or not SHA40.fullmatch(brain_llm_sha):
        raise ValueError("exact 40-hex source SHAs are required")
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min confidence must be between 0 and 1")

    guidance: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if row.get("ok") is not True:
            continue
        provider = canon(row.get("provider"))
        proposal = row.get("proposal")
        if not provider or not PROVIDER_ID.fullmatch(provider) or not isinstance(proposal, dict):
            continue
        if canon(proposal.get("provider_id")) != provider:
            continue
        strategy = canon(proposal.get("strategy"))
        target_layer = canon(proposal.get("target_layer"))
        failure = canon(row.get("failure_class"))
        try:
            confidence = max(0.0, min(1.0, float(proposal.get("confidence") or 0.0)))
        except (TypeError, ValueError):
            confidence = 0.0
        profile = STRATEGY_TO_PROFILE.get(strategy, "")
        if (
            proposal.get("abstain") is True
            or target_layer != "provider"
            or confidence < min_confidence
            or profile not in ALLOWED_PROFILES
        ):
            continue
        key = (provider, profile)
        if key in seen:
            continue
        seen.add(key)
        guidance.append({
            "providerId": provider,
            "failureClass": failure,
            "targetLayer": "provider",
            "strategy": strategy,
            "profile": profile,
            "confidence": round(confidence, 6),
            "priorOnly": True,
        })

    return {
        "schemaVersion": 1,
        "sourceNiakvioSha": niakvio_sha,
        "brainLlmSha": brain_llm_sha,
        "publicationAuthority": False,
        "directMutationAuthority": False,
        "proofAuthority": False,
        "rawMutationContentRetained": False,
        "privateContentRetained": False,
        "minConfidence": min_confidence,
        "providerCount": len({row["providerId"] for row in guidance}),
        "rows": guidance,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--niakvio-sha", required=True)
    parser.add_argument("--brain-llm-sha", required=True)
    parser.add_argument("--min-confidence", type=float, default=0.80)
    args = parser.parse_args()
    payload = sanitize(
        load_jsonl(args.input),
        niakvio_sha=args.niakvio_sha,
        brain_llm_sha=args.brain_llm_sha,
        min_confidence=args.min_confidence,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "source_niakvio_sha": payload["sourceNiakvioSha"],
        "provider_count": payload["providerCount"],
        "rows": len(payload["rows"]),
        "private_content_retained": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
