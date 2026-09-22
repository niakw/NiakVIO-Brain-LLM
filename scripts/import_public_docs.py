#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from niakvio_brain_llm.document_memory import chunk_markdown

def _resolved_sources(root: Path, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen: dict[str, dict[str, Any]] = {}

    for spec in specs:
        authority = int(spec.get("authority") or 0)
        role = str(spec.get("role") or "")

        candidates: list[Path] = []
        if spec.get("path"):
            candidates = [root / str(spec["path"])]
        elif spec.get("glob"):
            candidates = sorted(root.glob(str(spec["glob"])))

        for path in candidates:
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            previous = chosen.get(relative)
            if previous and int(previous["authority"]) >= authority:
                continue
            chosen[relative] = {
                "path": path,
                "relative": relative,
                "authority": authority,
                "role": role,
            }

    return sorted(chosen.values(), key=lambda item: (-item["authority"], item["relative"]))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", required=True)
    parser.add_argument("--config", default="config/document_sources.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.niakvio_root)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    specs = [x for x in config.get("sources") or [] if isinstance(x, dict)]

    rows = []
    imported = []
    for source in _resolved_sources(root, specs):
        path: Path = source["path"]
        relative = source["relative"]
        text = path.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_markdown(
            text,
            path=relative,
            authority=int(source["authority"]),
            role=str(source["role"]),
        )
        rows.extend(chunks)
        imported.append({
            "path": relative,
            "chunks": len(chunks),
            "authority": source["authority"],
            "role": source["role"],
        })

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )
    print(json.dumps({
        "documents": len(imported),
        "chunks": len(rows),
        "imported": imported,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
