#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from niakvio_brain_llm.mutation_guard import validate_mutations
from niakvio_brain_llm.niakvio_adapter import request_from_checkout

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


def fingerprint(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()

def _provider_override(root: Path, provider: str) -> Any:
    try:
        data=json.loads((root/"provider-overrides.json").read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):
        return None
    patches=data.get("provider_patches") if isinstance(data,dict) else None
    if not isinstance(patches,dict):
        return None
    wanted=canon(provider)
    for key,value in patches.items():
        if canon(key)==wanted:
            return value
    return None


def mutation_context_fingerprint(
    root: Path,
    provider: str,
    mutations: list[dict[str, Any]],
) -> str:
    surfaces: list[dict[str, Any]]=[]
    override_needed=False
    for mutation in mutations:
        scope=str(mutation.get("scope") or "")
        path=str(mutation.get("path") or "")
        if scope=="provider_data":
            override_needed=True
            continue
        if scope in {"provider_patch","provider_js"}:
            target=root/path
            if not target.is_file():
                raise ValueError(f"{provider}: mutation context path missing: {path}")
            surfaces.append({
                "scope":scope,
                "path":path,
                "sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
            })
    if override_needed:
        surfaces.append({
            "scope":"provider_data",
            "path":"provider-overrides.json:provider_patches",
            "value":_provider_override(root,provider),
        })
    return fingerprint(surfaces)


def load_force_memory(root: Path) -> set[tuple[str,str,str]]:
    path=root/"automation"/"brain-llm-force-memory.json"
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):
        return set()
    blocked:set[tuple[str,str,str]]=set()
    for row in data.get("entries") or []:
        if not isinstance(row,dict):
            continue
        provider=canon(row.get("providerId"))
        mutation_fp=str(row.get("mutationFingerprint") or "").strip().casefold()
        context_fp=str(row.get("mutationContextFingerprint") or "").strip().casefold()
        if (
            provider
            and re.fullmatch(r"[0-9a-f]{64}",mutation_fp)
            and re.fullmatch(r"[0-9a-f]{64}",context_fp)
            and (
                int(row.get("consecutiveFailures") or 0)>0
                or int(row.get("successes") or 0)>0
            )
        ):
            blocked.add((provider,mutation_fp,context_fp))
    return blocked


def sanitize(
    rows: list[dict[str, Any]],
    *,
    niakvio_root: Path,
    niakvio_sha: str,
    brain_llm_sha: str,
    min_confidence: float = 0.80,
) -> dict[str, Any]:
    niakvio_sha = str(niakvio_sha).strip().casefold()
    brain_llm_sha = str(brain_llm_sha).strip().casefold()
    if not SHA40.fullmatch(niakvio_sha) or not SHA40.fullmatch(brain_llm_sha):
        raise ValueError("exact 40-hex source SHAs are required")

    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    seen_providers: set[str] = set()
    blocked_force = load_force_memory(niakvio_root)

    for row in rows:
        if row.get("ok") is not True:
            continue
        provider = canon(row.get("provider"))
        proposal = row.get("proposal")
        if (
            not provider
            or not PROVIDER_ID.fullmatch(provider)
            or not isinstance(proposal, dict)
            or canon(proposal.get("provider_id")) != provider
        ):
            continue
        if canon(proposal.get("target_layer")) != "provider":
            continue
        if proposal.get("abstain") is True:
            continue
        try:
            confidence = max(0.0, min(1.0, float(proposal.get("confidence") or 0.0)))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < min_confidence:
            continue

        mutations = [
            dict(value)
            for value in (proposal.get("mutations") or [])
            if isinstance(value, dict)
        ][:8]
        if not mutations:
            continue

        request = request_from_checkout(niakvio_root, provider)
        registered = {
            str(value).strip()
            for value in (request.provider_context or {}).get("registered_patch_scripts") or []
            if str(value).strip()
        }
        validate_mutations(
            provider,
            mutations,
            allowed_patch_paths=registered,
        )

        # Defense in depth: the Force bridge is provider-local only.
        allowed = set(request.allowed_mutations or [])
        scopes = {str(value.get("scope") or "") for value in mutations}
        if not scopes or not scopes.issubset(allowed):
            continue
        if any(scope not in {"provider_data", "provider_patch", "provider_js"} for scope in scopes):
            continue

        mutation_fp = fingerprint(mutations)
        context_fp = mutation_context_fingerprint(niakvio_root, provider, mutations)
        if (provider, mutation_fp, context_fp) in blocked_force:
            continue
        if provider in seen_providers:
            raise ValueError(
                f"{provider}: multiple concrete Force candidates require isolated candidate sandboxing"
            )
        seen_providers.add(provider)
        key = (provider, mutation_fp)
        if key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "providerId": provider,
                "failureClass": canon(row.get("failure_class")),
                "targetLayer": "provider",
                "strategy": canon(proposal.get("strategy")),
                "confidence": round(confidence, 6),
                "mutations": mutations,
                "tests": [str(x)[:500] for x in (proposal.get("tests") or [])[:12]],
                "mutationFingerprint": mutation_fp,
                "mutationContextFingerprint": context_fp,
            }
        )

    return {
        "schemaVersion": 1,
        "sourceNiakvioSha": niakvio_sha,
        "brainLlmSha": brain_llm_sha,
        "sandboxMutationAuthority": True,
        "publicationAuthority": False,
        "proofAuthority": False,
        "providerMutationContentRetained": True,
        "privateContentRetained": False,
        "minConfidence": min_confidence,
        "providerCount": len({row["providerId"] for row in output}),
        "rows": output,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--niakvio-root", type=Path, required=True)
    parser.add_argument("--niakvio-sha", required=True)
    parser.add_argument("--brain-llm-sha", required=True)
    parser.add_argument("--min-confidence", type=float, default=0.80)
    args = parser.parse_args()

    output = sanitize(
        load_jsonl(args.input),
        niakvio_root=args.niakvio_root,
        niakvio_sha=args.niakvio_sha,
        brain_llm_sha=args.brain_llm_sha,
        min_confidence=args.min_confidence,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "provider_count": output["providerCount"],
                "rows": len(output["rows"]),
                "sandbox_mutation_authority": True,
                "publication_authority": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
