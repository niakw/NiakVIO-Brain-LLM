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



def observed_source_topologies(observations: Any) -> list[str]:
    """Classify actual 2xx response shapes, never provider names or WAF pages.

    This is sampling metadata, NOT a repaired-provider verdict. In particular,
    a challenged HTML page must not make an API or player topology seem proven.
    """
    topologies: set[str] = set()
    current_sources = {
        "targeted-regression-current", "census-sharded-current",
        "census-current", "waf-client-differential-current",
    }
    for observation in observations or []:
        if not isinstance(observation, dict) or _canon(observation.get("source")) not in current_sources:
            continue
        value = observation.get("value")
        if not isinstance(value, dict):
            continue
        network = value.get("network")
        if not isinstance(network, dict):
            continue
        for responses in network.values():
            if not isinstance(responses, list):
                continue
            for response in responses[:12]:
                if not isinstance(response, dict):
                    continue
                try:
                    status = int(response.get("status") or 0)
                except (ValueError, TypeError):
                    continue
                if not 200 <= status < 300:
                    continue
                # A TMDB lookup preceding a provider fetch is not provider
                # API evidence. Require an actual host and ignore metadata
                # infrastructure and HTML challenge pages.
                host = str(response.get("host") or "").strip().casefold()
                if not host or host in {
                    "api.themoviedb.org", "www.themoviedb.org",
                    "image.tmdb.org",
                } or str(response.get("challenge") or "").strip():
                    continue
                shape = response.get("shape")
                if not isinstance(shape, dict):
                    continue
                kind = _canon(shape.get("kind"))
                if kind == "html" and "turnstile" in {
                    _canon(marker) for marker in shape.get("markers") or []
                    if isinstance(marker, str)
                }:
                    continue
                if kind == "json":
                    topologies.add("json-api")
                elif kind == "javascript":
                    topologies.add("javascript-app")
                elif kind == "html":
                    markers = {
                        _canon(marker)
                        for marker in shape.get("markers") or []
                        if isinstance(marker, str)
                    }
                    if "download" in markers:
                        topologies.add("html-download")
                    if markers & {"player", "embed", "hls-literal", "mp4-literal"} or (
                        isinstance(shape.get("iframes"), int) and shape["iframes"] > 0
                    ):
                        topologies.add("html-player")
                    if not (markers & {"download", "player", "embed", "hls-literal", "mp4-literal"}) and not (
                        isinstance(shape.get("iframes"), int) and shape["iframes"] > 0
                    ):
                        topologies.add("html-catalogue")
    return sorted(topologies)


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

    structural = {
        signal for signal in signals
        if signal in {
            "class-prefix-family",
            "nested-anchor-html",
            "mixed-tag-nested-container",
        }
    }
    # Repair-family identity is intentionally coarser than evidence shape.
    # HTML/JSON response format and catalogue/status metadata help compile a
    # candidate but must not split one reusable causal mechanism into a family
    # per provider.
    if structural:
        mechanism_archetype = "dom-selector-container"
    elif failure == "variant-coverage-gap":
        mechanism_archetype = "variant-coverage"
    elif failure in {"chain-terminal-gap", "media-extraction-gap"}:
        mechanism_archetype = "terminal-extraction"
    elif failure == "content-identity-gap":
        mechanism_archetype = "content-identity"
    elif failure in {"route-proven-gap", "candidate-replay-gap"}:
        mechanism_archetype = "route-parser"
    elif failure in {"provider-transport-gap", "transport-environment-gap"}:
        mechanism_archetype = "provider-transport"
    elif stages:
        mechanism_archetype = stages[0]
    else:
        mechanism_archetype = failure or "unknown"
    archetype = f"{failure or 'unknown'}:{mechanism_archetype}"

    payload = {
        "version": 1,
        "failure": failure or "unknown",
        "status": status,
        "mediaTypes": media_types,
        "signals": signals,
        "stages": stages[:8],
        "mutationSurfaces": allowed,
        "sourceTopologies": observed_source_topologies(raw.get("observations") or []),
        "archetype": archetype,
    }
    # Family identity must describe causal repair shape, not product/catalogue
    # metadata. Status, media types, the complete stage list and available
    # mutation surfaces remain compatibility metadata, but must not fragment
    # one reusable mechanism into provider-specific families.
    identity = {
        "version": 2,
        "failure": payload["failure"],
        "archetype": payload["archetype"],
    }
    encoded = json.dumps(
        identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return {
        **payload,
        "version": 2,
        "key": hashlib.sha256(encoded).hexdigest(),
    }


def repair_family_key(value: Any) -> str:
    return str(repair_family_descriptor(value).get("key") or "")


def family_histogram(values: list[Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for value in values:
        family = repair_family_descriptor(value)
        key = str(family.get("archetype") or family.get("key") or "unknown")
        counts[key] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _family_evidence_score(row: dict[str, Any]) -> int:
    """Rank same-family witnesses by reusable causal evidence, not provider identity."""
    family = row.get("repair_family") or row.get("repairFamily")
    if not isinstance(family, dict):
        return 0
    signals = {
        _canon(value)
        for value in family.get("signals") or []
        if _canon(value)
    }
    score = 0
    weights = {
        "class-prefix-family": 8,
        "mixed-tag-nested-container": 6,
        "nested-anchor-html": 4,
        "provider-http-2xx": 3,
        "provider-http-auth-or-challenge": 1,
        "provider-http-5xx": 1,
    }
    for signal, weight in weights.items():
        if signal in signals:
            score += weight
    stages = {
        _canon(value)
        for value in family.get("stages") or []
        if _canon(value)
    }
    if stages:
        score += min(3, len(stages))
    return score


def select_family_wave(
    rows: list[dict[str, Any]],
    *,
    validated_family_keys: set[str] | None = None,
    provider_failure_burden: dict[str, int] | None = None,
    provider_execution_burden: dict[str, int] | None = None,
    ensure_topology_coverage: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select one rotating representative per unresolved repair family.

    Validated families may fan out because their mechanism can take the
    deterministic replay path. Unvalidated families spend novel synthesis
    budget on one representative at a time. Negative-memory burden rotates the
    representative across siblings instead of hammering one provider forever.

    Model/runtime execution failures are a separate concern from provider
    repair failure. A witness that only timed out is temporarily skipped when
    the same family still has an unblocked sibling; this prevents family-scale
    synthesis from repeatedly spending its budget on a witness that cannot
    produce a verdict. If every sibling is execution-blocked, the least-blocked
    witness is retried instead of suppressing the family.
    """
    validated = {
        str(value).strip().casefold()
        for value in (validated_family_keys or set())
        if str(value).strip()
    }
    burden = {
        str(key).strip().casefold(): max(0, int(value or 0))
        for key, value in (provider_failure_burden or {}).items()
    }
    execution_burden = {
        str(key).strip().casefold(): max(0, int(value or 0))
        for key, value in (provider_execution_burden or {}).items()
    }
    groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    order: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        provider = str(row.get("provider") or row.get("providerId") or "").strip().casefold()
        family = row.get("repair_family") or row.get("repairFamily")
        family_key = (
            str(family.get("key") or "").strip().casefold()
            if isinstance(family, dict)
            else ""
        )
        group_key = family_key or f"provider:{provider or index}"
        if group_key not in groups:
            groups[group_key] = []
            order.append(group_key)
        groups[group_key].append((index, row))

    selected_indexes: set[int] = set()
    for group_key in order:
        members = groups[group_key]
        if group_key in validated:
            selected_indexes.update(index for index, _ in members)
            continue
        unblocked_members = [
            item for item in members
            if execution_burden.get(
                str(item[1].get("provider") or item[1].get("providerId") or "").strip().casefold(),
                0,
            ) == 0
        ]
        candidate_members = unblocked_members or members

        def witness_key(item: tuple[int, dict[str, Any]]) -> tuple[int, int, int, int]:
            provider = str(
                item[1].get("provider") or item[1].get("providerId") or ""
            ).strip().casefold()
            execution = execution_burden.get(provider, 0)
            return (
                execution if not unblocked_members else 0,
                -_family_evidence_score(item[1]),
                burden.get(provider, 0),
                item[0],
            )

        representative = min(candidate_members, key=witness_key)
        selected_indexes.add(representative[0])
        if ensure_topology_coverage:
            # A family-level parser may transfer, but a download index, API,
            # and embedded player are not interchangeable reverse witnesses.
            # Add ONLY independently observed 2xx topologies, not inferred
            # provider types, historical status or HTTP challenge pages.
            def topologies(item: tuple[int, dict[str, Any]]) -> set[str]:
                family = item[1].get("repair_family") or item[1].get("repairFamily") or {}
                return {
                    str(x) for x in family.get("sourceTopologies") or []
                    if str(x) in {
                        "json-api", "javascript-app", "html-download",
                        "html-player", "html-catalogue",
                    }
                }

            # Independent witness diversity matters: one multi-format
            # website must not stand in for an unrelated streaming/API site.
            # Add at most one different provider for each *observed* topology.
            # No invented topology or automatic publication authority.
            representative_topologies = topologies(representative)
            available = set().union(*(topologies(item) for item in members))
            for topology in sorted(available):
                # Identical single-format siblings are redundant. A mixed
                # download+API witness needs independent, differently shaped
                # examples, not several copies of the same multi-format site.
                if topology in representative_topologies and len(representative_topologies) == 1:
                    continue
                witnesses = [
                    item for item in members
                    if item[0] not in selected_indexes
                    and topology in topologies(item)
                    and topologies(item) != representative_topologies
                ]
                if not witnesses:
                    continue
                extra = min(witnesses, key=witness_key)
                selected_indexes.add(extra[0])

    selected = [
        row for index, row in enumerate(rows)
        if index in selected_indexes
    ]
    deferred = [
        row for index, row in enumerate(rows)
        if index not in selected_indexes
    ]
    return selected, deferred
