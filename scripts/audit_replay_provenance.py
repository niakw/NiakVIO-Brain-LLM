#!/usr/bin/env python3
"""Offline exact-program replay inventory; no external URLs or private data."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from niakvio_brain_llm.replay_inventory import replay_inventory


def main() -> int:
    cli=argparse.ArgumentParser()
    cli.add_argument("--niakvio-root",required=True,type=Path)
    cli.add_argument("--output",required=True,type=Path)
    args=cli.parse_args()
    root=args.niakvio_root.resolve()
    state=json.loads((root/"automation/provider-census-status.json").read_text(encoding="utf-8"))
    source=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    report=replay_inventory(state,root,source)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("FIELD_BRAIN_REPLAY_PROGRAM_INVENTORY candidates={} missing_exact_program={} current_source_program={}".format(
        report["candidateReplayCount"],report["missingProgramCount"],report["currentProgramCount"]))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
