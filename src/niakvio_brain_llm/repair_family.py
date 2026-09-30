from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any


def _canon(value: object) -> str:
    return "-".join(str(value or "").strip().casefold().replace("_", "-").split())


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {
        "failure_class": getattr(value, "failure_class", ""),
        "status": getattr(value, "status", ""),
        "supported_types": getattr(value, "supported_types", []),
        "observations": getattr(value, "observations", []),
        "allowed_mutations": getattr(value, "allowed_mutations", []),
    }


def _status_bucket(value: object) -> str:
    status = _canon(value)
    for token in (
        "full-ok", "partial-ok", "candidate-ok", "route-proven",
        "chain-reached", "no-proof", "provider-js-broken",
        "client-transport-gap", "harness-mismatch", "network-blocked",
    ):
        if token in status:
            return token
    return status or "unknown"


def _class_structure_signals(hints: list[str]) -> set[str]:
    signals: set[str] = set()
    for hint in hints[:16]:
        text = str(hint or "")
        classes_match = re.search(r"(?:^|[;:])classes=([^;]+)", text)
        classes = []
        if classes_match:
            classes = [
                raw.strip().casefold()
                for raw in classes_match.group(1).split(",")
                if raw.strip()
            ]
        if classes and any(
            other != token
            and (other.startswith(token + "-") or other.startswith(token + "_"))
            for token in classes
            for other in classes
        ):
            signals.add("class-prefix-family")

        if "classFacts=" not in text:
            continue
        facts_text = text.split("classFacts=", 1)[1]
        for fragment in facts_text.split("[")[1:]:
            raw_fact = fragment.split("]", 1)[0]
            fields: dict[str, str] = {}
            for raw_field in raw_fact.split(";"):
                key, sep, raw_value = raw_field.partition("=")
                if sep:
                    fields[key.strip()] = raw_value.strip()
                elif raw_field.strip() and "token" not in fields:
                    fields["token"] = raw_field.strip()
            try:
                count = int(fields.get("count") or 0)
                self_href = int(fields.get("selfHref") or 0)
                nested = int(fields.get("nestedAnchors") or 0)
            except ValueError:
                continue
            tags = {
                item.strip().casefold()
                for item in str(fields.get("tags") or "").split(",")
                if item.strip()
            }
            if count >= 2 and nested > 0:
                signals.add("nested-anchor-html")
            if count >= 2 and nested > 0 and len(tags) >= 2 and self_href < count:
                signals.add("mixed-tag-nested-container")
    return signals


def _observation_signals(observations: Any) -> tuple[list[str], list[str]]:
    signals: set[str] = set()
    stages: set[str] = set()
    for observation in observations or []:
        if not isinstance(observation, dict):
            continue
        source = _canon(observation.get("source"))
        if source not in {
            "targeted-regression-current",
            "census-sharded-current",
            "census-current",
            "waf-client-differential-current",
        }:
            continue
        value = observation.get("value")
        if not isinstance(value, dict):
            continue
        hints = [str(item) for item in value.get("structureHints") or [] if str(item)]
        signals.update(_class_structure_signals(hints))
        for stage in (value.get("debugStages") or {}).values():
            stage_key = _canon(stage)
            if stage_key:
                stages.add(stage_key)
        dominant = _canon(value.get("dominantIssue"))
        if dominant:
            stages.add(dominant)
        for rows in (value.get("network") or {}).values():
            if not isinstance(rows, list):
                continue
            for row in rows[:12]:
                if not isinstance(row, dict):
                    continue
                try:
                    status = int(row.get("status") or 0)
                except (TypeError, ValueError):
                    status = 0
                if 200 <= status < 300:
                    signals.add("provider-http-2xx")
                elif status in {401, 403, 429}:
                    signals.add("provider-http-auth-or-challenge")
                elif status >= 500:
                    signals.add("provider-http-5xx")
                shape = row.get("shape")
                if isinstance(shape, dict):
                    kind = _canon(shape.get("kind"))
                    if kind:
                        signals.add("response-" + kind)
    return sorted(signals), sorted(stages)


def repair_family_descriptor(value: Any) -> dict[str, Any]:
    raw = _mapping(value)
    existing = raw.get("repair_family") or raw.get("repairFamily")
    if isinstance(existing, dict) and existing.get("key"):
        return dict(existing)

    signals, stages = _observation_signals(raw.get("observations") or [])
    media_types = sorted({
        _canon(item)
        for item in raw.get("supported_types") or raw.get("supportedTypes") or []
        if _canon(item)
    })
    allowed = sorted({
        _canon(item)
        for item in raw.get("allowed_mutations") or raw.get("allowedMutations") or []
        if _canon(item)
    })
    failure = _canon(raw.get("failure_class") or raw.get("failureClass"))
    status = _status_bucket(raw.get("status") or raw.get("status_before") or raw.get("statusBefore"))

    structural = [
        signal for signal in signals
        if signal in {
            "class-prefix-family",
            "nested-anchor-html",
            "mixed-tag-nested-container",
            "response-html",
            "response-json",
        }
    ]
    archetype_parts = [failure or "unknown"]
    if structural:
        archetype_parts.extend(structural[:3])
    elif stages:
        archetype_parts.append(stages[0])
    archetype = ":".join(archetype_parts)

    payload = {
        "version": 1,
        "failure": failure or "unknown",
        "status": status,
        "mediaTypes": media_types,
        "signals": signals,
        "stages": stages[:8],
        "mutationSurfaces": allowed,
        "archetype": archetype,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return {**payload, "key": hashlib.sha256(encoded).hexdigest()}


def repair_family_key(value: Any) -> str:
    return str(repair_family_descriptor(value).get("key") or "")


def family_histogram(values: list[Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for value in values:
        family = repair_family_descriptor(value)
        key = str(family.get("archetype") or family.get("key") or "unknown")
        counts[key] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
