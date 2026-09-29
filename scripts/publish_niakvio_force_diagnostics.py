#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SAFE = re.compile(r"[^a-zA-Z0-9._:-]+")

def clean(value: object, limit: int = 120) -> str:
    return SAFE.sub("_", str(value or "").strip())[:limit].strip("_")

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--niakvio-sha", required=True)
    p.add_argument("--brain-llm-sha", required=True)
    a = p.parse_args()

    rows: list[dict[str, Any]] = []
    for raw in a.input.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        item = json.loads(raw)
        if not isinstance(item, dict):
            continue
        provider = clean(item.get("provider"), 80).casefold().replace("_", "-")
        if not provider:
            continue
        proposal = item.get("proposal") if isinstance(item.get("proposal"), dict) else {}
        trace = []
        for event in item.get("force_scope_trace") or []:
            if not isinstance(event, dict):
                continue
            trace.append({
                "scope": clean(event.get("scope"), 40),
                "outcome": clean(event.get("outcome"), 40),
                "reason": clean(event.get("reason"), 120),
                **({"errorType": clean(event.get("errorType"), 60)} if event.get("errorType") else {}),
            })
        mutations = proposal.get("mutations") if isinstance(proposal.get("mutations"), list) else []
        rows.append({
            "providerId": provider,
            "status": clean(item.get("status"), 60),
            "failureClass": clean(item.get("failure_class"), 80),
            "ok": item.get("ok") is True,
            "scopeTrace": trace,
            "mutationScopes": sorted({
                clean(m.get("scope"), 40)
                for m in mutations if isinstance(m, dict) and clean(m.get("scope"), 40)
            }),
            "abstain": proposal.get("abstain") is True or not mutations,
        })

    payload = {
        "schemaVersion": 1,
        "brainLlmSha": a.brain_llm_sha.strip().casefold(),
        "sourceNiakvioSha": a.niakvio_sha.strip().casefold(),
        "privateContentRetained": False,
        "proofAuthority": False,
        "publicationAuthority": False,
        "providerCount": len({row["providerId"] for row in rows}),
        "rows": sorted(rows, key=lambda row: row["providerId"]),
    }
    serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    if re.search(r"https?://|authorization[=:]|cookie[=:]|token[=:]", serialized, re.I):
        raise SystemExit("unsafe content in FORCE diagnostics")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FIELD_NIAKVIO_FORCE_DIAGNOSTICS providers=" + str(payload["providerCount"]) + " private_content=false")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
