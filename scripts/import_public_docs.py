#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from niakvio_brain_llm.document_memory import chunk_markdown

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", required=True)
    parser.add_argument("--config", default="config/document_sources.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.niakvio_root)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    rows = []
    imported = []
    missing = []

    for spec in config.get("sources") or []:
        relative = str(spec.get("path") or "")
        path = root / relative
        if not path.exists():
            missing.append(relative)
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_markdown(
            text,
            path=relative,
            authority=int(spec.get("authority") or 0),
            role=str(spec.get("role") or ""),
        )
        rows.extend(chunks)
        imported.append({"path": relative, "chunks": len(chunks)})

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
        "missing_optional": missing,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
