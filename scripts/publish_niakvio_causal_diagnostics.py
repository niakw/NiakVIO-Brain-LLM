#!/usr/bin/env python3
"""Persist only source-pinned Brain *diagnosis* outcomes, never model raw text.

Private provider URLs, model prose, headers, patches and player artifacts must
not cross the guidance publication boundary. Diagnoses are hypotheses and
negative learning memory; even a selected causal owner is NOT repair authority.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_SHA40 = re.compile(r"[0-9a-f]{40}")
_SHA64 = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,95}")
_CODE = re.compile(r"[a-z0-9][a-z0-9_-]{0,95}")
_LAYERS = frozenset({
    "unknown", "core", "client", "runtime", "network", "provider",
    "pipeline", "harness", "environment", "brain",
})
_MAX_PER_PROVIDER = 10
_MAX_PROVIDERS = 140


def code(value: object, *, provider: bool = False) -> str:
    normalized = str(value or "").strip().casefold().replace(" ", "_")
    regex = _ID if provider else _CODE
    return normalized if regex.fullmatch(normalized) else ""


def clean(row: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    provider = code(row.get("providerId"), provider=True)
    digest = str(row.get("providerArtifactSha256") or "")
    source = str(row.get("sourceNiakvioSha") or "")
    brain = str(row.get("brainLlmSha") or "")
    strategy = code(row.get("strategy"))
    failure = code(row.get("failureClass"))
    if (
        not provider or not strategy or not failure
        or not _SHA64.fullmatch(digest) or not _SHA40.fullmatch(source)
        or not _SHA40.fullmatch(brain)
        or any(row.get(key) is not False for key in (
            "proofAuthority", "publicationAuthority",
            "providerMutationAuthority", "nativePlaybackAuthority",
        ))
    ):
        return None
    mode = str(row.get("modelStatus") or "")
    if mode not in {"completed", "abstained", "model_error", "route_only"}:
        return None
    layer = str(row.get("routingLayer") or "")
    hypothesis = str(row.get("hypothesisLayer") or "")
    return {
        "providerId": provider,
        "providerArtifactSha256": digest,
        "sourceNiakvioSha": source,
        "brainLlmSha": brain,
        "failureClass": failure,
        "strategy": strategy,
        "routingLayer": layer if layer in _LAYERS else "unknown",
        "hypothesisLayer": hypothesis if hypothesis in _LAYERS else "unknown",
        "modelStatus": mode,
        "historicalOnly": True,
        "proofAuthority": False,
        "publicationAuthority": False,
        "providerMutationAuthority": False,
        "nativePlaybackAuthority": False,
    }


def candidate(rows: list[dict[str, Any]], *, source_sha: str, brain_sha: str) -> list[dict[str, Any]]:
    if not _SHA40.fullmatch(source_sha) or not _SHA40.fullmatch(brain_sha):
        raise ValueError("exact source SHAs required")
    accepted = []
    for raw in rows[:128]:
        if not isinstance(raw, dict) or raw.get("diagnostic_only") is not True:
            continue
        if raw.get("provider_mutation_authority") is not False:
            continue
        route = raw.get("routing")
        if not isinstance(route, dict) or route.get("mode") != "llm_diagnose":
            continue
        if route.get("allowed_mutations"):
            continue
        proposal = raw.get("proposal")
        if proposal is not None and (
            not isinstance(proposal, dict) or proposal.get("mutations")
        ):
            continue
        if raw.get("ok") is False:
            status = "model_error"
        elif proposal is None:
            status = "route_only"
        elif proposal.get("abstain") is True:
            status = "abstained"
        else:
            status = "completed"
        value = clean({
            "providerId": raw.get("provider"),
            "providerArtifactSha256": raw.get("diagnostic_exact_bundle_sha256"),
            "sourceNiakvioSha": source_sha, "brainLlmSha": brain_sha,
            "failureClass": raw.get("failure_class"),
            "strategy": route.get("strategy"),
            "routingLayer": route.get("target_layer"),
            "hypothesisLayer": (proposal or {}).get("target_layer"),
            "modelStatus": status,
            "proofAuthority": False, "publicationAuthority": False,
            "providerMutationAuthority": False, "nativePlaybackAuthority": False,
        })
        if value:
            accepted.append(value)
    return accepted


def merge(previous: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    retained = []
    if (
        isinstance(previous, dict)
        and previous.get("schemaVersion") == 1
        and previous.get("authority") == "brain-source-pinned-causal-hypotheses-only"
        and all(previous.get(k) is False for k in (
            "proofAuthority", "publicationAuthority",
            "providerMutationAuthority", "nativePlaybackAuthority",
        ))
    ):
        retained = [clean(row) for row in (previous.get("rows") or [])[:1400]]
    combined = list(rows) + [x for x in retained if x]
    seen: set[tuple[str, str, str, str]] = set()
    per_provider: dict[str, int] = {}
    output = []
    for row in combined:
        key = (
            row["providerId"], row["providerArtifactSha256"],
            row["sourceNiakvioSha"], row["strategy"],
        )
        if key in seen or per_provider.get(row["providerId"], 0) >= _MAX_PER_PROVIDER:
            continue
        if row["providerId"] not in per_provider and len(per_provider) >= _MAX_PROVIDERS:
            continue
        seen.add(key)
        per_provider[row["providerId"]] = per_provider.get(row["providerId"], 0) + 1
        output.append(row)
    return {
        "schemaVersion": 1,
        "authority": "brain-source-pinned-causal-hypotheses-only",
        "providerCount": len(per_provider),
        "observationCount": len(output),
        "rows": output,
        "proofAuthority": False,
        "publicationAuthority": False,
        "providerMutationAuthority": False,
        "nativePlaybackAuthority": False,
        "privateContentRetained": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--niakvio-sha", required=True)
    parser.add_argument("--brain-llm-sha", required=True)
    args = parser.parse_args()
    rows = [
        json.loads(line) for line in args.input.read_text("utf-8").splitlines()
        if line.strip()
    ]
    previous = (
        json.loads(args.previous.read_text("utf-8"))
        if args.previous and args.previous.is_file() else {}
    )
    result = merge(previous, candidate(
        rows, source_sha=args.niakvio_sha, brain_sha=args.brain_llm_sha,
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "FIELD_BRAIN_CAUSAL_MEMORY "
        f"providers={result['providerCount']} observations={result['observationCount']} "
        "proof=false publication=false mutation=false private_content=false"
    )


if __name__ == "__main__":
    main()
