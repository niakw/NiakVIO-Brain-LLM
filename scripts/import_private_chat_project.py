#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from niakvio_brain_llm.private_chat_memory import import_private_chat_project


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    rows = import_private_chat_project(project_root)
    source_index = json.loads((project_root / "index.json").read_text(encoding="utf-8"))
    source_conversations = len(source_index.get("conversations") or {})
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )

    conversations = {str(row.get("conversation_id") or "") for row in rows}
    signal_rows = sum(1 for row in rows if row.get("role") == "private_chat_signal")
    transcript_rows = len(rows) - signal_rows
    print(json.dumps({
        "project": "NiakVIO",
        "documents": len(rows),
        "source_conversations": source_conversations,
        "indexed_conversations": len(conversations),
        "signal_documents": signal_rows,
        "transcript_documents": transcript_rows,
        "raw_tool_messages_indexed": False,
        "proof_authority": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
