"""Bound live diagnostics to structural facts, never response scalar values."""
import re

IDENTIFIER = re.compile(r"[A-Za-z_$][\w$-]{0,47}")
SENSITIVE = re.compile(r"key|token|auth|signature|secret|password|cookie|session|nonce", re.I)

def rows(value, limit):
    return value[:limit] if isinstance(value, list) else []


def count(value, maximum=100000):
    return max(0, min(maximum, value)) if type(value) is int else 0


def identifiers(values, limit=16):
    return [name for name in values if isinstance(name, str) and IDENTIFIER.fullmatch(name)
            and not SENSITIVE.search(name)][:limit] if isinstance(values, list) else []


def response_structure(value):
    if not isinstance(value, dict):
        return {}
    kind = value.get("kind")
    if kind == "json":
        fields = []
        for row in rows(value.get("fields"), 16):
            if not isinstance(row, dict):
                continue
            path = str(row.get("path") or "")[:160]
            parts = path.replace("[]", "").split(".")
            if not all(IDENTIFIER.fullmatch(part) and not SENSITIVE.search(part) for part in parts):
                continue
            if row.get("type") in {"string", "number", "boolean", "null", "object", "array"}:
                fields.append({"path": path, "type": row["type"]})
        return {"kind": kind, "fields": fields}
    if kind == "html":
        return {"kind": kind, "tags": [
            {"tag": row["tag"], "attributes": identifiers(row.get("attributes"))}
            for row in rows(value.get("tags"), 8) if isinstance(row, dict)
            and row.get("tag") in {"iframe", "script", "video", "source", "a", "button", "select", "option"}
        ], "variables": identifiers(value.get("variables"))}
    return {"kind": kind} if kind in {"text", "binary"} else {}


def network_evidence(values):
    result = []
    for row in rows(values, 8):
        if not isinstance(row, dict):
            continue
        host = str(row.get("host") or "").lower()
        stage = str(row.get("stage") or "")
        status = row.get("status")
        result.append({
            "host": host if re.fullmatch(r"[a-z0-9.-]{1,160}", host) else "",
            "stage": stage if re.fullmatch(r"[a-z_]{1,40}", stage) else "",
            "status": status if type(status) is int and 100 <= status <= 599 else None,
            "functions": identifiers(row.get("functions"), 8),
            "response_structure": response_structure(row.get("response_structure")),
            "announced_players": count(row.get("announced_players"), 256),
        })
    return result


def verification_feedback(value):
    if not isinstance(value, dict):
        return {}
    result = {"reason": re.sub(r"[^a-zA-Z0-9._:-]", "_", str(value.get("reason") or ""))[:160]}
    for phase in ("baseline", "candidate"):
        row = value.get(phase) if isinstance(value.get(phase), dict) else {}
        result[phase] = {key: count(row.get(key))
                         for key in ("streamsPlayable", "streamsReturned", "identityContradictions")}
    result["candidate_network"] = network_evidence(value.get("candidate_network"))
    return result
