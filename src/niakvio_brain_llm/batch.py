from __future__ import annotations

import json
from pathlib import Path
from typing import Any

def load_census(root: str | Path) -> list[dict[str, Any]]:
    path = Path(root) / "automation" / "provider-census-status.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        row for row in data.get("providers") or []
        if isinstance(row, dict) and row.get("provider")
    ]

def target_priority(row: dict[str, Any]) -> tuple[int, str]:
    """Prefer the cheapest/highest-evidence work, never provider identity."""
    status = str(row.get("status") or "").casefold()
    depths = " ".join(str(x) for x in row.get("evidenceDepth") or []).casefold()

    if row.get("candidateProof") or "candidate" in status:
        rank = 10
    elif "chain_reached" in depths or "chain reached" in status:
        rank = 20
    elif row.get("routeProof") or "route proven" in status:
        rank = 30
    elif "provider js broken" in status:
        rank = 40
    elif row.get("repairEligible"):
        rank = 50
    else:
        rank = 90

    return rank, str(row.get("provider") or "").casefold()

def select_batch_targets(
    rows: list[dict[str, Any]],
    *,
    mode: str,
    providers: set[str] | None = None,
) -> list[dict[str, Any]]:
    if mode not in {"repair", "diagnostic", "brain"}:
        raise ValueError("mode must be repair, diagnostic or brain")

    wanted = {item.casefold() for item in providers or set()}
    selected: list[dict[str, Any]] = []

    for row in rows:
        provider = str(row.get("provider") or "")
        if wanted and provider.casefold() not in wanted:
            continue

        brain_required = bool(row.get("brainCheckRequired"))
        repair_eligible = bool(row.get("repairEligible"))

        if mode == "repair" and repair_eligible:
            selected.append(row)
        elif mode == "diagnostic" and brain_required and not repair_eligible:
            selected.append(row)
        elif mode == "brain" and brain_required:
            selected.append(row)

    return sorted(selected, key=target_priority)

def batch_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "UNKNOWN")
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "targets": len(rows),
        "statuses": dict(sorted(statuses.items())),
    }
