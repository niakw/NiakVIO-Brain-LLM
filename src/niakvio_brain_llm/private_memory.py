from __future__ import annotations

from typing import Any

ALLOWED_FIELDS = {
    "experience_id",
    "project",
    "source_kind",
    "source_ref",
    "providers",
    "failure_class",
    "symptom_families",
    "signals",
    "strategy",
    "avoid",
    "lesson",
    "result",
    "target_layer",
    "verified_lanes",
    "proof_authority",
}

FORBIDDEN_RAW_FIELDS = {
    "messages",
    "conversation",
    "raw_conversation",
    "raw_messages",
    "prompt",
    "transcript",
    "email",
    "user_profile",
    "personal_context",
}

def sanitize_private_record(value: dict[str, Any]) -> dict[str, Any]:
    project = str(value.get("project") or "").strip()
    if project.casefold() != "niakvio":
        raise ValueError("private memory record is not scoped to NiakVIO")

    forbidden = FORBIDDEN_RAW_FIELDS & set(value)
    if forbidden:
        raise ValueError(
            "raw/private conversation fields are forbidden: "
            + ", ".join(sorted(forbidden))
        )

    row = {
        key: value[key]
        for key in ALLOWED_FIELDS
        if key in value
    }

    row["project"] = "NiakVIO"
    row["source"] = "niakvio-private-sanitized"
    row["proof_authority"] = False

    failure = str(row.get("failure_class") or "").strip()
    strategy = str(row.get("strategy") or "").strip()
    if not failure:
        raise ValueError("private memory requires failure_class")
    if not strategy:
        raise ValueError("private memory requires strategy")

    row["providers"] = [str(x) for x in row.get("providers") or []][:16]
    row["symptom_families"] = [str(x) for x in row.get("symptom_families") or []][:16]
    row["signals"] = [str(x) for x in row.get("signals") or []][:24]
    row["avoid"] = [str(x) for x in row.get("avoid") or []][:16]
    row["verified_lanes"] = [str(x) for x in row.get("verified_lanes") or []][:8]
    row["lesson"] = str(row.get("lesson") or "")[:2000]
    row["experience_id"] = str(row.get("experience_id") or "")[:200]
    row["source_ref"] = str(row.get("source_ref") or "")[:300]

    return row
