#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("cleanup_ancestor",ROOT/"scripts/cleanup_ancestor_branches.py")
assert spec and spec.loader
# Import the reusable GitHub client using the same scripts directory.
import sys
sys.path.insert(0,str(ROOT/"scripts"))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
data=json.loads((ROOT/"cleanup/ancestor-branches-2026-11-06.json").read_text())
rows=mod.verify(data)
assert len(rows)==6
assert len(set(r["sha"] for r in rows))<len(rows), "shared ancestor must be handled per exact branch ref"
for row in rows:
    assert row["branch"] not in mod.KEEP
for candidate in ("main","niakvio-guidance","fix/brain-observed-media-bridge-contract"):
    altered={**data,"branches":[{"branch":candidate,"sha":"a"*40,"provenAncestorOf":data["sourceMainSha"]}],"expectedCount":1}
    try:mod.verify(altered)
    except ValueError:pass
    else:raise AssertionError("Protected/unmerged branch accepted: "+candidate)
print("BRAIN_ANCESTOR_CLEANUP_POLICY_OK")
