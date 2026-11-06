#!/usr/bin/env python3
"""No main, unmerged or unexpected remote ref may be deleted."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("branch_cleanup", ROOT / "scripts" / "cleanup_merged_pr_branches.py")
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)
data = json.loads((ROOT / "cleanup/merged-pr-branches-2026-11-06.json").read_text())
rows = mod.validate_manifest(data)
assert len(rows) == 17
assert all(row["branch"] != "main" for row in rows)
assert all(row["branch"].startswith(("codex/", "audit/", "fix/")) for row in rows)
for path in ("main", "niakvio-guidance", "codex/../../main", "fix/foo//bar", "refs/heads/main", "branch with spaces"):
    assert not mod.valid_entry({"branch": path, "sha": "a"*40, "pr": 2}), path
for invalid in ({"branch":"codex/demo","sha":"notsha","pr":1},
                {"branch":"codex/demo","sha":"a"*40,"pr":True}):
    assert not mod.valid_entry(invalid)
assert not set(row["branch"] for row in rows) & ["codex/niakvio-brain-reliability","fix/brain-observed-media-bridge-contract","fix/force-selected-function-envelope","fix/force-skip-advisor-preflight-20261011","fix/force-skip-legacy-prompt-prefill","fix/private-chat-redaction-idempotence","fix/private-memory-homepath-redaction","niakvio-guidance"]
workflow = (ROOT / ".github/workflows/cleanup-merged-pr-branches.yml").read_text()
assert "contents: write" in workflow
assert "pull_request_target" not in workflow
assert "GH_TOKEN:" in workflow
assert "tests/cleanup_merged_pr_branches_test.py" in workflow
print("BRAIN_MERGED_BRANCH_CLEANUP_POLICY_OK count=" + str(len(rows)))
