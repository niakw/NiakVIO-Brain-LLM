from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "select_guidance_publication",
    ROOT / "scripts" / "select_guidance_publication.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

def payload(source: str, providers: list[str]) -> dict:
    return {
        "schemaVersion": 2,
        "sourceNiakvioSha": source,
        "brainLlmSha": "b" * 40,
        "publicationAuthority": False,
        "directMutationAuthority": False,
        "proofAuthority": False,
        "rawMutationContentRetained": False,
        "privateContentRetained": False,
        "providerCount": len(providers),
        "rows": [{"providerId": provider} for provider in providers],
    }

previous = payload("a" * 40, ["a", "b"])
candidate_empty = payload("a" * 40, [])
selected, reason = mod.choose(previous, candidate_empty)
assert selected == previous
assert reason.startswith("coverage_regression:")

candidate_superset = payload("a" * 40, ["a", "b", "c"])
selected, reason = mod.choose(previous, candidate_superset)
assert selected == candidate_superset
assert reason == "coverage_non_regression"

candidate_new_source = payload("c" * 40, [])
selected, reason = mod.choose(previous, candidate_new_source)
assert selected == candidate_new_source
assert reason == "source_changed"

workflow = (ROOT / ".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")
assert "select_guidance_publication.py" in workflow
assert "FIELD_NIAKVIO_GUIDANCE_PUBLICATION" not in workflow
assert "refs/remotes/origin/$BRANCH:guidance/niakvio-guidance.json" in workflow
