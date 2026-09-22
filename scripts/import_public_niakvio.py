#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

def normalize_case(case: dict[str, Any], *, source: str) -> dict[str, Any] | None:
    failure = str(case.get("failureClass") or "").strip()
    solution = str(case.get("solutionClass") or "").strip()
    if not failure or not solution:
        return None
    return {
        "experience_id": str(case.get("id") or ""),
        "source": source,
        "providers": [str(x) for x in case.get("providers") or []][:16],
        "failure_class": failure,
        "symptom_families": [str(x) for x in case.get("symptomFamilies") or []][:16],
        "signals": [str(x) for x in case.get("transferableSignals") or []][:24],
        "strategy": solution,
        "avoid": [str(x) for x in case.get("avoid") or []][:16],
        "lesson": str(case.get("lesson") or ""),
        "result": "validated",
        "proof_authority": False,
    }

def collect(root: Path) -> list[dict[str, Any]]:
    sources = [
        ("brain-repair-experience", root / "automation" / "brain-repair-experience.json"),
        ("historical-seed", root / "automation" / "brain-historical-experience-seed.json"),
    ]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source_name, path in sources:
        data = load_json(path, {})
        for case in data.get("historicalCases") or data.get("cases") or []:
            if not isinstance(case, dict):
                continue
            row = normalize_case(case, source=source_name)
            if not row:
                continue
            identity = row["experience_id"] or json.dumps(
                [row["failure_class"], row["strategy"], row["providers"]],
                sort_keys=True,
            )
            if identity in seen:
                continue
            seen.add(identity)
            rows.append(row)

    return rows

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = collect(Path(args.niakvio_root))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )
    print(json.dumps({
        "experiences": len(rows),
        "failure_classes": len({row["failure_class"] for row in rows}),
        "strategies": len({row["strategy"] for row in rows}),
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
