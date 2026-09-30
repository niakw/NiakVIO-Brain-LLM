#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from niakvio_brain_llm.niakvio_adapter import request_from_checkout
from niakvio_brain_llm.repair_family import repair_family_descriptor, select_family_wave
from niakvio_brain_llm.routing import REPLAYABLE_FAMILY_MECHANISMS


def canon(value: object) -> str:
    return str(value or "").strip().casefold().replace("_", "-")


def read_targets(path: Path) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        provider = canon(line)
        if provider and provider not in seen:
            seen.add(provider)
            out.append(provider)
    return out


def load_memory(root: Path) -> dict[str, Any]:
    path = root / "automation" / "brain-llm-force-memory.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def select_wave(providers: list[str], niakvio_root: Path) -> tuple[list[str], dict[str, Any]]:
    memory = load_memory(niakvio_root)
    validated_keys: set[str] = set()
    for raw in memory.get("validatedFamilies") or []:
        if not isinstance(raw, dict) or int(raw.get("successCount") or 0) <= 0:
            continue
        family = raw.get("repairFamily") if isinstance(raw.get("repairFamily"), dict) else {}
        key = str(family.get("key") or "").strip().casefold()
        mechanism = canon(raw.get("mechanismFamily"))
        if re.fullmatch(r"[0-9a-f]{64}", key) and mechanism in REPLAYABLE_FAMILY_MECHANISMS:
            validated_keys.add(key)

    burden: dict[str, int] = {}
    for raw in memory.get("entries") or []:
        if not isinstance(raw, dict):
            continue
        provider = canon(raw.get("providerId"))
        if provider:
            burden[provider] = burden.get(provider, 0) + max(
                0, int(raw.get("consecutiveFailures") or 0)
            )

    rows: list[dict[str, Any]] = []
    for provider in providers:
        request = request_from_checkout(niakvio_root, provider)
        rows.append({
            "provider": provider,
            "repair_family": repair_family_descriptor(request),
        })

    selected, deferred = select_family_wave(
        rows,
        validated_family_keys=validated_keys,
        provider_failure_burden=burden,
    )
    selected_ids = [str(row["provider"]) for row in selected]
    deferred_ids = [str(row["provider"]) for row in deferred]
    families = {
        str((row.get("repair_family") or {}).get("key") or "")
        for row in rows
        if isinstance(row.get("repair_family"), dict)
        and str((row.get("repair_family") or {}).get("key") or "")
    }
    report = {
        "schemaVersion": 1,
        "inputProviders": providers,
        "selectedProviders": selected_ids,
        "deferredProviders": deferred_ids,
        "inputProviderCount": len(providers),
        "selectedProviderCount": len(selected_ids),
        "deferredProviderCount": len(deferred_ids),
        "repairFamilyCount": len(families),
        "validatedReplayableFamilyCount": len(validated_keys),
        "policy": "one rotating representative per unresolved family; validated replayable families may fan out",
        "publicationAuthority": False,
        "proofAuthority": False,
    }
    return selected_ids, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--niakvio-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    selected, report = select_wave(read_targets(args.targets), args.niakvio_root)
    if not selected:
        raise SystemExit("repair family wave unexpectedly empty")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(selected) + "\n", encoding="utf-8")
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "FIELD_NIAKVIO_REPAIR_FAMILY_WAVE "
        f"input={report['inputProviderCount']} selected={report['selectedProviderCount']} "
        f"deferred={report['deferredProviderCount']} families={report['repairFamilyCount']} "
        f"validated={report['validatedReplayableFamilyCount']} "
        f"ids={','.join(selected)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
