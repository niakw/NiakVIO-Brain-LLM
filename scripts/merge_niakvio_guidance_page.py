#!/usr/bin/env python3
"""Merge one sanitized Brain-LLM guidance page into durable same-source coverage."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


def load(path: Path | None) -> dict[str,Any]:
    if path is None or not path.is_file():
        return {}
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError(f"{path}: expected object")
    return value


def canon(value: object)->str:
    return str(value or "").strip().casefold().replace("_","-")


def refreshed(path: Path)->set[str]:
    return {
        canon(line) for line in path.read_text(encoding="utf-8").splitlines()
        if canon(line)
    }


def _compatible(previous:dict[str,Any],candidate:dict[str,Any])->bool:
    return bool(previous) and (
        str(previous.get("sourceNiakvioSha") or "").casefold()
        == str(candidate.get("sourceNiakvioSha") or "").casefold()
        and str(previous.get("brainLlmSha") or "").casefold()
        == str(candidate.get("brainLlmSha") or "").casefold()
    )


def _identity(row:dict[str,Any],kind:str)->tuple[str,...]:
    provider=canon(row.get("providerId"))
    if kind=="advisor":
        return (
            provider,
            str(row.get("profile") or "").casefold(),
            str(row.get("experimentFingerprint") or "").casefold(),
        )
    return (
        provider,
        str(row.get("mutationFingerprint") or "").casefold(),
        str(row.get("mutationContextFingerprint") or "").casefold(),
    )


def merge(
    previous:dict[str,Any],
    candidate:dict[str,Any],
    refreshed_providers:set[str],
    *,
    kind:str,
)->dict[str,Any]:
    if kind not in {"advisor","force"}:
        raise ValueError("kind must be advisor|force")
    out=copy.deepcopy(candidate)
    prior_rows=previous.get("rows") if isinstance(previous.get("rows"),list) else []
    candidate_rows=candidate.get("rows") if isinstance(candidate.get("rows"),list) else []
    rows:list[dict[str,Any]]=[]
    if _compatible(previous,candidate):
        rows.extend(
            copy.deepcopy(row)
            for row in prior_rows
            if isinstance(row,dict)
            and canon(row.get("providerId")) not in refreshed_providers
        )
    rows.extend(
        copy.deepcopy(row)
        for row in candidate_rows
        if isinstance(row,dict)
        and canon(row.get("providerId")) in refreshed_providers
    )
    dedup:dict[tuple[str,...],dict[str,Any]]={}
    for row in rows:
        key=_identity(row,kind)
        if not key[0]:
            continue
        dedup[key]=row
    rows=sorted(
        dedup.values(),
        key=lambda row:(
            canon(row.get("providerId")),
            -float(row.get("confidence") or 0.0),
            _identity(row,kind),
        ),
    )
    out["rows"]=rows
    out["providerCount"]=len({canon(row.get("providerId")) for row in rows})
    return out


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--previous-advisor",type=Path)
    p.add_argument("--previous-force",type=Path)
    p.add_argument("--candidate-advisor",type=Path,required=True)
    p.add_argument("--candidate-force",type=Path,required=True)
    p.add_argument("--refreshed-providers",type=Path,required=True)
    p.add_argument("--advisor-output",type=Path,required=True)
    p.add_argument("--force-output",type=Path,required=True)
    a=p.parse_args()
    page=refreshed(a.refreshed_providers)
    advisor=merge(
        load(a.previous_advisor),load(a.candidate_advisor),page,kind="advisor"
    )
    force=merge(
        load(a.previous_force),load(a.candidate_force),page,kind="force"
    )
    a.advisor_output.parent.mkdir(parents=True,exist_ok=True)
    a.force_output.parent.mkdir(parents=True,exist_ok=True)
    a.advisor_output.write_text(json.dumps(advisor,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    a.force_output.write_text(json.dumps(force,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(
        "FIELD_NIAKVIO_GUIDANCE_PAGE_MERGE "
        f"refreshed={len(page)} advisor_providers={advisor.get('providerCount',0)} "
        f"force_providers={force.get('providerCount',0)}"
    )
    return 0


if __name__=="__main__":
    raise SystemExit(main())
