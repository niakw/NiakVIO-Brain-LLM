#!/usr/bin/env python3
"""Skip a redundant advisor LLM call after authoritative *diagnostic-only* FORCE.

This only saves inference. It never copies a candidate into a mutation/promotion
artifact, cannot grant correctness and deliberately leaves guidance output empty.
The causal-diagnostics publisher still consumes the original FORCE rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ID = re.compile(r"[a-z0-9][a-z0-9-]{0,95}")
SHA256 = re.compile(r"[a-f0-9]{64}")


def exact_active_digest(root: Path, provider: str) -> str:
    """Bind diagnosis to the current, *enabled* canonical provider JS bytes."""
    base = root.resolve()
    for name in ("manifest.json", "vf/manifest.json"):
        manifest_path = base / name
        try:
            doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ""
        for entry in doc.get("scrapers") or []:
            if not isinstance(entry, dict) or str(entry.get("id") or "").lower() != provider:
                continue
            if entry.get("enabled") is not True:
                continue
            raw = str(entry.get("filename") or "")
            if not raw or raw.startswith(("http:", "https:")):
                return ""
            source = (manifest_path.parent / raw).resolve()
            try:
                relative = source.relative_to(base).parts
            except ValueError:
                return ""
            if not relative or relative[0] != "providers" or not source.is_file():
                return ""
            return hashlib.sha256(source.read_bytes()).hexdigest()
    return ""


def reusable(rows: list[dict[str, Any]], targets: list[str], root: Path) -> bool:
    """All exact requested providers must already have a safe model diagnosis."""
    if not targets or len(targets) > 8 or len(set(targets)) != len(targets):
        return False
    if any(not ID.fullmatch(provider) for provider in targets):
        return False
    if len(rows) != len(targets):
        return False
    observed: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("ok") is not True:
            return False
        provider = str(row.get("provider") or "").strip().lower()
        if provider not in targets or provider in observed:
            return False
        observed.add(provider)
        if row.get("diagnostic_only") is not True:
            return False
        if row.get("provider_mutation_authority") is not False:
            return False
        if row.get("probe_only") is True:
            return False
        route = row.get("routing")
        if not isinstance(route, dict) or route.get("mode") != "llm_diagnose":
            return False
        if route.get("allowed_mutations") != []:
            return False
        proposal = row.get("proposal")
        if proposal is not None:
            if not isinstance(proposal, dict) or proposal.get("mutations") != []:
                return False
        current_digest = exact_active_digest(root, provider)
        row_digest = str(row.get("diagnostic_exact_bundle_sha256") or "").lower()
        if not current_digest or not SHA256.fullmatch(row_digest) or row_digest != current_digest:
            return False
    return observed == set(targets)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-batch", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--niakvio-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        targets = [
            s.strip().lower() for s in args.targets.read_text("utf-8").splitlines()
            if s.strip()
        ]
        rows = [
            json.loads(line) for line in args.force_batch.read_text("utf-8").splitlines()
            if line.strip()
        ]
        result = reusable(rows, targets, args.niakvio_root)
    except (OSError, ValueError, TypeError, UnicodeError):
        result = False
    if result:
        print(f"FIELD_BRAIN_ADVISOR_REUSE eligible=true providers={len(targets)} "
              "basis=exact_current_js_force_diagnosis_only mutation_authority=false "
              "publication_authority=false")
        return 0
    print("FIELD_BRAIN_ADVISOR_REUSE eligible=false action=run_advisor_model")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
