#!/usr/bin/env python3
"""Select one fair bounded page from an exact NiakVIO Repair cohort."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SHA40=re.compile(r"^[0-9a-f]{40}$")


def canon(value: object) -> str:
    return str(value or "").strip().casefold().replace("_","-")


def load(path: Path | None) -> dict[str,Any]:
    if path is None or not path.is_file():
        return {}
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):
        return {}
    return value if isinstance(value,dict) else {}


def target_list(path: Path) -> list[str]:
    out=[];seen=set()
    for line in path.read_text(encoding="utf-8").splitlines():
        provider=canon(line)
        if provider and provider not in seen:
            seen.add(provider);out.append(provider)
    return out


def select(
    requested:list[str],
    previous:dict[str,Any],
    *,
    source_sha:str,
    brain_sha:str,
    page_size:int,
)->tuple[list[str],dict[str,Any]]:
    source_sha=source_sha.strip().casefold()
    brain_sha=brain_sha.strip().casefold()
    if not SHA40.fullmatch(source_sha) or not SHA40.fullmatch(brain_sha):
        raise ValueError("exact source and Brain SHAs are required")
    requested=[canon(v) for v in requested if canon(v)]
    if not requested:
        raise ValueError("requested cohort is empty")

    compatible=(
        int(previous.get("schemaVersion") or 0)==1
        and str(previous.get("sourceNiakvioSha") or "").casefold()==source_sha
        and str(previous.get("brainLlmSha") or "").casefold()==brain_sha
        and [canon(v) for v in previous.get("requestedProviders") or []]==requested
    )
    previous_cycle=int(previous.get("cycle") or 1) if compatible else 0
    restart_cycle=bool(compatible and previous.get("complete") is True)
    completed={
        canon(v) for v in (previous.get("completedProviders") or [])
        if compatible and not restart_cycle and canon(v) in set(requested)
    }
    cycle=(previous_cycle+1) if restart_cycle else max(1,previous_cycle or 1)
    remaining=[v for v in requested if v not in completed]
    page=remaining[:max(1,min(int(page_size or 1),12))]
    completed.update(page)
    remaining_after=[v for v in requested if v not in completed]
    state={
        "schemaVersion":1,
        "sourceNiakvioSha":source_sha,
        "brainLlmSha":brain_sha,
        "requestedProviders":requested,
        "cycle":cycle,
        "completedProviders":[v for v in requested if v in completed],
        "remainingProviders":remaining_after,
        "pageProviders":page,
        "pageSize":max(1,min(int(page_size or 1),12)),
        "complete":not remaining_after,
        "processedCount":len(completed),
        "remainingCount":len(remaining_after),
        "publicationAuthority":False,
        "proofAuthority":False,
        "privateContentRetained":False,
    }
    return page,state


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--targets",type=Path,required=True)
    p.add_argument("--previous-state",type=Path)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--brain-sha",required=True)
    p.add_argument("--page-size",type=int,default=8)
    p.add_argument("--page-output",type=Path,required=True)
    p.add_argument("--state-output",type=Path,required=True)
    a=p.parse_args()
    page,state=select(
        target_list(a.targets),
        load(a.previous_state),
        source_sha=a.source_sha,
        brain_sha=a.brain_sha,
        page_size=a.page_size,
    )
    a.page_output.parent.mkdir(parents=True,exist_ok=True)
    a.state_output.parent.mkdir(parents=True,exist_ok=True)
    a.page_output.write_text("\n".join(page)+("\n" if page else ""),encoding="utf-8")
    a.state_output.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(
        "FIELD_NIAKVIO_GUIDANCE_PAGE "
        f"page={len(page)} processed={state['processedCount']} "
        f"remaining={state['remainingCount']} complete={str(state['complete']).lower()} "
        f"ids={','.join(page) or '-'}"
    )
    return 0


if __name__=="__main__":
    raise SystemExit(main())
