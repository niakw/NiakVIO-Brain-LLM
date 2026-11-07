"""Read-only provenance guard for candidate-replay targets.

A census CANDIDATE OK label is not the exact historical patch bytes and must
not silently count as a replayable, current-SHA repair. This module never
executes providers, publishes code or reconstructs missing mutation content.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

RUN = re.compile(r"run\s+([0-9]{8,14})(?:-post-repair)?\Z", re.I)
SHA = re.compile(r"[0-9a-f]{40}\Z")
PROVIDER = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")


def replay_inventory(census: dict[str, Any], root: Path, current_sha: str) -> dict[str, Any]:
    if not SHA.fullmatch(current_sha):
        raise ValueError("current NiakVIO SHA must be exact")
    if not isinstance(census.get("providers"), list) or not isinstance(census.get("repairQueue"), list):
        raise ValueError("missing current census replay authority")
    queue = set(census["repairQueue"])
    records: list[dict[str, Any]] = []
    for row in sorted((v for v in census["providers"] if isinstance(v, dict)),
                      key=lambda v: str(v.get("provider") or "")):
        provider = str(row.get("provider") or "").strip().casefold()
        if not PROVIDER.fullmatch(provider) or provider not in queue:
            continue
        if row.get("status") != "CANDIDATE OK":
            continue
        labels = row.get("candidateProof") or []
        run_ids = sorted({match.group(1)
                          for label in labels if isinstance(label, str)
                          for match in [RUN.fullmatch(label.strip())] if match})
        record = {
            "provider": provider,
            "historicalRunIds": run_ids,
            "status": "missing_exact_replay_program",
            "sourceMatched": False,
            "programFound": False,
            "proofAuthority": False,
            "publicationAuthority": False,
        }
        for run_id in run_ids:
            path = root / "automation" / "hosted-repair-evidence" / f"{run_id}-mutations.json"
            if not path.is_file():
                continue
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if (not isinstance(doc, dict) or doc.get("publicationAuthority") is not False
                    or doc.get("sandboxMutationAuthority") is not True
                    or doc.get("providerMutationContentRetained") is not True):
                continue
            rows = doc.get("rows") or []
            valid = any(
                isinstance(item, dict)
                and str(item.get("providerId") or "").casefold() == provider
                and isinstance(item.get("mutations"), list)
                and len(item["mutations"]) > 0
                and isinstance(item.get("mutationFingerprint"), str)
                and len(item["mutationFingerprint"]) >= 32
                for item in rows
            )
            if not valid:
                continue
            record["programFound"] = True
            source = str(doc.get("sourceNiakvioSha") or "")
            record["sourceMatched"] = bool(SHA.fullmatch(source) and source == current_sha)
            record["status"] = ("source_matched_program_needs_live_replay" if record["sourceMatched"]
                                else "historical_program_needs_safe_rematerialization")
            break
        records.append(record)
    return {
        "schemaVersion": 1,
        "sourceNiakvioSha": current_sha,
        "candidateReplayCount": len(records),
        "missingProgramCount": sum(not r["programFound"] for r in records),
        "currentProgramCount": sum(r["sourceMatched"] for r in records),
        "rows": records,
        "publicationAuthority": False,
    }
