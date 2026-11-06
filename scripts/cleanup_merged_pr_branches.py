#!/usr/bin/env python3
"""Fail-closed, one-shot retirement of *merged* PR branches with exact SHA proof."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "cleanup" / "merged-pr-branches-2026-11-06.json"
REPO = "niakw/NiakVIO-Brain-LLM"
BRANCH_PATTERN = re.compile(r"^(?:codex|audit|fix)/[a-z0-9][a-z0-9_/-]{0,110}$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

def valid_entry(row: object) -> bool:
    if not isinstance(row, dict):
        return False
    name, sha, number = row.get("branch"), row.get("sha"), row.get("pr")
    return (isinstance(name, str) and BRANCH_PATTERN.fullmatch(name) is not None
            and ".." not in name and "//" not in name and not name.endswith("/")
            and isinstance(sha, str) and SHA_PATTERN.fullmatch(sha) is not None
            and type(number) is int and number > 0)

def validate_manifest(doc: object) -> list[dict]:
    if not isinstance(doc, dict) or doc.get("repository") != REPO or doc.get("schemaVersion") != 1:
        raise ValueError("Invalid repository or manifest schema")
    rows = doc.get("branches")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        raise ValueError("Merged branch cohort must be bounded")
    if doc.get("expectedCount") != len(rows) or not all(valid_entry(x) for x in rows):
        raise ValueError("Invalid or incomplete exact branch list")
    if len({x["branch"] for x in rows}) != len(rows) or len({x["pr"] for x in rows}) != len(rows):
        raise ValueError("Duplicate branch/PR in cleanup list")
    return rows

def api(path: str, method: str = "GET") -> dict | list | None:
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token or os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise RuntimeError("Expected exact target repository and GitHub token")
    request = Request("https://api.github.com/" + path, method=method, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(request, timeout=30) as response:
            contents = response.read(12_000_001)
            if len(contents) > 12_000_000:
                raise RuntimeError("GitHub API response exceeded bounded JSON size")
            return json.loads(contents.decode("utf-8")) if contents else None
    except HTTPError as err:
        if err.code == 404 and method == "GET":
            return None
        raise

def main() -> None:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = validate_manifest(doc)
    removed = []
    skipped = []
    for row in rows:
        name, sha, number = row["branch"], row["sha"], row["pr"]
        refpath = "repos/" + REPO + "/git/ref/heads/" + quote(name, safe="/")
        branchpath = "repos/" + REPO + "/branches/" + quote(name, safe="")
        current = api(refpath)
        if not current:
            skipped.append(name + ":already_absent")
            continue
        branch = api(branchpath)
        pr = api("repos/" + REPO + "/pulls/" + str(number))
        if (not isinstance(pr, dict) or pr.get("state") != "closed" or not pr.get("merged_at")
                or pr.get("head", {}).get("ref") != name
                or pr.get("head", {}).get("sha") != sha
                or (pr.get("head", {}).get("repo") or {}).get("full_name") != REPO
                or (current.get("object") or {}).get("sha") != sha
                or not isinstance(branch, dict) or branch.get("protected", True)):
            skipped.append(name + ":unverified_or_protected")
            continue
        # Skip branches used by *any* open PR, including an unrelated PR.
        active = api("repos/" + REPO + "/pulls?" + urlencode({"state":"open","head":"niakw:"+name,"per_page":100}))
        if not isinstance(active, list) or active:
            skipped.append(name + ":open_or_ambiguous_PR")
            continue
        # A last fetch narrows the unavoidable REST delete-reference race.
        last = api(refpath)
        if not last or (last.get("object") or {}).get("sha") != sha:
            skipped.append(name + ":head_moved")
            continue
        api("repos/" + REPO + "/git/refs/heads/" + quote(name, safe="/"), "DELETE")
        removed.append(name)
        print("FIELD_BRAIN_BRANCH_CLEANUP_DELETED " + name + " pr=" + str(number))
    print("FIELD_BRAIN_BRANCH_CLEANUP_SUMMARY " + json.dumps({
        "eligible": len(rows), "deleted": len(removed), "skipped": skipped,
        "preservedNonMerged": 8,
    }, sort_keys=True))
    if len(removed) + len(skipped) != len(rows):
        raise AssertionError("Cleanup accounting lost a branch")
    if skipped:
        raise RuntimeError("Not all merged branch references could be safely retired")

if __name__ == "__main__":
    main()
