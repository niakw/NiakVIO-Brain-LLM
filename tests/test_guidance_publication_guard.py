from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


merge = load_module(
    "merge_niakvio_guidance_page",
    "scripts/merge_niakvio_guidance_page.py",
)


def advisor(source: str, brain: str, rows: list[dict]) -> dict:
    return {
        "schemaVersion": 2,
        "sourceNiakvioSha": source,
        "brainLlmSha": brain,
        "publicationAuthority": False,
        "directMutationAuthority": False,
        "proofAuthority": False,
        "rawMutationContentRetained": False,
        "privateContentRetained": False,
        "providerCount": len({row["providerId"] for row in rows}),
        "rows": rows,
    }


source = "a" * 40
brain = "b" * 40
previous = advisor(
    source,
    brain,
    [
        {
            "providerId": "a",
            "profile": "old-a",
            "experimentFingerprint": "1" * 64,
            "confidence": 0.9,
        },
        {
            "providerId": "b",
            "profile": "keep-b",
            "experimentFingerprint": "2" * 64,
            "confidence": 0.9,
        },
    ],
)
candidate = advisor(
    source,
    brain,
    [
        {
            "providerId": "a",
            "profile": "new-a",
            "experimentFingerprint": "3" * 64,
            "confidence": 0.95,
        }
    ],
)
selected = merge.merge(previous, candidate, {"a"}, kind="advisor")
assert {row["profile"] for row in selected["rows"]} == {"new-a", "keep-b"}
assert selected["providerCount"] == 2

new_brain = advisor(
    source,
    "c" * 40,
    [
        {
            "providerId": "a",
            "profile": "new-brain-a",
            "experimentFingerprint": "4" * 64,
            "confidence": 0.96,
        }
    ],
)
selected = merge.merge(previous, new_brain, {"a"}, kind="advisor")
assert [row["profile"] for row in selected["rows"]] == ["new-brain-a"]

workflow = (
    ROOT / ".github/workflows/niakvio-private-guidance.yml"
).read_text(encoding="utf-8")

for marker in (
    "select_niakvio_guidance_page.py",
    "merge_niakvio_guidance_page.py",
    "niakvio-guidance-state.json",
    "niakvio-guidance-page.txt",
    "Continue remaining guidance page",
    "steps.page.outputs.complete",
    "steps.source.outputs.sha",
    "steps.cohort.outputs.csv",
    "actions: write",
):
    assert marker in workflow, marker

# Publication is now page-aware. The old whole-payload coverage guard must not
# be the authority for a paged run, otherwise page 2 could be rejected merely
# because it does not repeat page 1.
assert "select_guidance_publication.py" not in workflow
assert "FIELD_NIAKVIO_GUIDANCE_PUBLICATION" not in workflow

# The public branch is deliberately tiny and complete-state aware.
assert "guidance/niakvio-guidance.json" in workflow
assert "guidance/niakvio-force-mutations.json" in workflow
assert "guidance/niakvio-guidance-state.json" in workflow
assert "files=3" in workflow

print("paged guidance publication guard contract passed")
