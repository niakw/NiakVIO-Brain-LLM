#!/usr/bin/env python3
"""Retire only SHA-frozen branches proven ancestors of current protected main."""
from __future__ import annotations
import json
import os
from pathlib import Path
from urllib.parse import quote, urlencode
from cleanup_merged_pr_branches import api, REPO, BRANCH_PATTERN, SHA_PATTERN

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"cleanup/ancestor-branches-2026-11-06.json"
KEEP={"main","niakvio-guidance","fix/brain-observed-media-bridge-contract"}

def verify(doc: dict) -> list[dict]:
    if doc.get("schemaVersion")!=1 or doc.get("repository")!=REPO:
        raise ValueError("wrong repo/scheme")
    rows=doc.get("branches")
    if not isinstance(rows,list) or not rows or len(rows)>12 or doc.get("expectedCount")!=len(rows):
        raise ValueError("unexpected cleanup cohort")
    seen=set()
    for row in rows:
        name,sha=row.get("branch"),row.get("sha")
        if (not isinstance(name,str) or name in KEEP or not BRANCH_PATTERN.fullmatch(name)
                or name in seen or not isinstance(sha,str) or not SHA_PATTERN.fullmatch(sha)
                or row.get("provenAncestorOf")!=doc.get("sourceMainSha")):
            raise ValueError("unsafe ancestry cleanup entry")
        seen.add(name)
    return rows

def main() -> None:
    doc=json.loads(FILE.read_text(encoding="utf-8"))
    rows=verify(doc)
    results=[]
    for row in rows:
        name,sha=row["branch"],row["sha"]
        ref="repos/"+REPO+"/git/ref/heads/"+quote(name,safe="/")
        current=api(ref)
        if not current:
            results.append(name+":already_absent")
            continue
        details=api("repos/"+REPO+"/branches/"+quote(name,safe=""))
        active=api("repos/"+REPO+"/pulls?"+urlencode({"state":"open","head":"niakw:"+name,"per_page":100}))
        main=api("repos/"+REPO+"/branches/main")
        head=(main or {}).get("commit",{}).get("sha")
        if (not head or not SHA_PATTERN.fullmatch(head) or not isinstance(details,dict)
                or details.get("protected",True) or not isinstance(active,list) or active
                or (current.get("object") or {}).get("sha")!=sha):
            raise RuntimeError("Ancestry branch preflight failed: "+name)
        compare=api("repos/"+REPO+"/compare/"+sha+"..."+head+"?per_page=1")
        if (not isinstance(compare,dict) or compare.get("status") not in ("ahead","identical")
                or compare.get("behind_by")!=0):
            raise RuntimeError("Unique commits or divergent history; refusing "+name)
        final=api(ref)
        if not final or (final.get("object") or {}).get("sha")!=sha:
            raise RuntimeError("Branch moved while pruning: "+name)
        api("repos/"+REPO+"/git/refs/heads/"+quote(name,safe="/"),"DELETE")
        results.append(name+":deleted")
        print("FIELD_BRAIN_ANCESTOR_BRANCH_DELETED "+name+" sha="+sha)
    if len(results)!=len(rows):
        raise AssertionError("Incomplete ancestry accounting")
    print("FIELD_BRAIN_ANCESTOR_CLEANUP "+json.dumps({"attempted":len(rows),"results":results}))

if __name__=="__main__":
    main()
