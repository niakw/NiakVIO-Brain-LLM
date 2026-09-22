#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_ROLES = ["system", "user", "assistant"]

def validate_row(row: dict) -> None:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) != 3:
        raise ValueError("SFT row must contain exactly system/user/assistant messages")
    roles = [str(message.get("role") or "") for message in messages if isinstance(message, dict)]
    if roles != ALLOWED_ROLES:
        raise ValueError("SFT roles must be system,user,assistant")
    assistant = json.loads(str(messages[2].get("content") or ""))
    if assistant.get("abstain") is not False:
        raise ValueError("abstention is not positive SFT truth")
    if str(assistant.get("target_layer") or "") not in {"provider","core","harness","network"}:
        raise ValueError("invalid target layer")
    if not str(assistant.get("strategy") or "").strip():
        raise ValueError("missing strategy")
    metadata = row.get("metadata") or {}
    if metadata.get("source") != "niakvio-verified-learning":
        raise ValueError("SFT row is not from verified NiakVIO learning")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--minimum", type=int, default=100)
    args = parser.parse_args()

    rows=[]
    for line_no,line in enumerate(Path(args.input).read_text(encoding="utf-8").splitlines(),start=1):
        if not line.strip():
            continue
        value=json.loads(line)
        if not isinstance(value,dict):
            raise SystemExit(f"line {line_no}: object required")
        try:
            validate_row(value)
        except Exception as exc:
            raise SystemExit(f"line {line_no}: {exc}")
        rows.append(value)

    result={
        "examples":len(rows),
        "minimum":args.minimum,
        "ready_for_lora":len(rows)>=args.minimum,
        "verified_only":True
    }
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
