#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
workflow=(ROOT/".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")

for required in (
    "same_incomplete_cycle=false",
    "continuation_brain",
    "continuation_source",
    "continuation_complete",
    "FIELD_NIAKVIO_GUIDANCE_CONTINUATION_PIN allowed=true",
    'if [ "$same_incomplete_cycle" = "true" ]',
    "reason=brain_main_advanced",
    "newer_brain_already_published",
):
    assert required in workflow, required

assert '&& [ "$continuation_complete" != "true" ]' in workflow
print("NiakVIO guidance continuation publication contract passed")
