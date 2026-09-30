from __future__ import annotations

import re

from typing import Any

from .contracts import RepairRequest

def _clip(value: Any, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + "...<clipped>"

def _compact(value: Any, *, depth: int = 0, string_limit: int = 500) -> Any:
    if depth >= 4:
        return _clip(value, min(string_limit, 350))
    if isinstance(value, dict):
        return {
            str(key)[:80]: _compact(
                item,
                depth=depth + 1,
                string_limit=string_limit,
            )
            for key, item in list(value.items())[:20]
        }
    if isinstance(value, list):
        return [
            _compact(item, depth=depth + 1, string_limit=string_limit)
            for item in value[:10]
        ]
    if isinstance(value, str):
        return _clip(value, string_limit)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _clip(value, string_limit)

def _compact_force_observation(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("source") or "").strip()
    if source != "targeted-regression-current":
        return _compact(row, string_limit=260)
    value = row.get("value") if isinstance(row.get("value"), dict) else {}
    network_summary: list[str] = []
    network = value.get("network") if isinstance(value.get("network"), dict) else {}
    for lane, rows in list(network.items())[:6]:
        if not isinstance(rows, list):
            continue
        for item in rows[:4]:
            if not isinstance(item, dict):
                continue
            shape = item.get("shape") if isinstance(item.get("shape"), dict) else {}
            network_summary.append(
                ":".join([
                    str(lane)[:32],
                    str(item.get("host") or "")[:80],
                    str(item.get("status") or "")[:8],
                    str(shape.get("kind") or "")[:16],
                ])
            )
    return {
        "source": source,
        "value": {
            "debugStages": _compact(value.get("debugStages") or {}, string_limit=120),
            "statuses": _compact(value.get("statuses") or {}, string_limit=120),
            "verifiedLanes": [str(x)[:32] for x in (value.get("verifiedLanes") or [])[:6]],
            "playableLanes": [str(x)[:32] for x in (value.get("playableLanes") or [])[:6]],
            "sampleTitles": _compact(value.get("sampleTitles") or {}, string_limit=100),
            "structureHints": [str(x)[:240] for x in (value.get("structureHints") or [])[:6]],
            "networkSummary": network_summary[:12],
        },
    }


def compact_request(
    request: RepairRequest,
    *,
    high_confidence: bool,
    mutation_allowed: bool,
) -> dict[str, Any]:
    data = request.to_dict()
    context = dict(data.get("provider_context") or {})

    if "published_bundle" in context and isinstance(context["published_bundle"], dict):
        published = dict(context["published_bundle"])
        blocks = published.get("providerBlocks")
        if isinstance(blocks, list):
            published["providerBlocks"] = [
                {
                    "id": str(row.get("id") or "")[:180],
                    "source": _clip(str(row.get("source") or ""), 3400 if mutation_allowed else 2200),
                }
                for row in blocks[:2]
                if isinstance(row, dict)
            ]
        context["published_bundle"] = published
    if "registered_patch_sources" in context and isinstance(context["registered_patch_sources"], dict):
        sources = list(context["registered_patch_sources"].items())
        source_limit = 2200 if mutation_allowed else 1800
        max_sources = 2 if mutation_allowed else 1
        context["registered_patch_sources"] = {
            str(path)[:180]: _clip(source, source_limit)
            for path, source in sources[:max_sources]
        }
    if "authored_module" in context:
        # Force mutation planning should spend context on the registered provider
        # Bloc first. Keep only a small authored-module fallback for providers
        # whose registered Bloc does not expose the needed contract.
        source_limit = 1200 if mutation_allowed else (2200 if not high_confidence else 1200)
        context["authored_module"] = _clip(context["authored_module"], source_limit)
    if "override" in context:
        context["override"] = _clip(
            context["override"],
            900 if mutation_allowed else 700,
        )
    if "hub" in context:
        context["hub"] = _clip(context["hub"], 450 if mutation_allowed else 700)

    # The checkout context is richer than what the advisor model may need.
    # Keep an explicit bounded view; exact source remains available to compact
    # Force and deterministic validation outside this advisor payload.
    bounded_context: dict[str, Any] = {
        "source_repo": _clip(context.get("source_repo"), 80),
        "read_only": bool(context.get("read_only", True)),
        "provider_id": _clip(context.get("provider_id"), 120),
    }
    scripts = context.get("registered_patch_scripts")
    if isinstance(scripts, list):
        bounded_context["registered_patch_scripts"] = [
            _clip(value, 180) for value in scripts[:4]
        ]
    published = context.get("published_bundle")
    if isinstance(published, dict):
        compact_published = {
            "filename": _clip(published.get("filename"), 180),
            "version": _clip(published.get("version"), 80),
            "supportedTypes": list(published.get("supportedTypes") or [])[:6],
            "formats": list(published.get("formats") or [])[:6],
        }
        blocks = published.get("providerBlocks")
        if isinstance(blocks, list):
            compact_published["providerBlocks"] = [
                {
                    "id": _clip(row.get("id"), 160),
                    "source": _clip(row.get("source"), 1100 if mutation_allowed else 320),
                }
                for row in blocks[:1]
                if isinstance(row, dict)
            ]
        bounded_context["published_bundle"] = compact_published
    sources = context.get("registered_patch_sources")
    if isinstance(sources, dict):
        source_limit = 1400 if mutation_allowed else 280
        bounded_context["registered_patch_sources"] = {
            _clip(path, 180): _clip(value, source_limit)
            for path, value in list(sources.items())[:1]
        }
    if context.get("authored_module"):
        bounded_context["authored_module"] = _clip(
            context.get("authored_module"), 900 if mutation_allowed else 260
        )
    if context.get("override"):
        bounded_context["override"] = _clip(context.get("override"), 600)
    if context.get("hub"):
        bounded_context["hub"] = _clip(context.get("hub"), 420)
    history = context.get("advisor_experiment_history")
    if isinstance(history, list):
        bounded_context["advisor_experiment_history"] = [
            _compact(row, string_limit=220)
            for row in history[-6:]
            if isinstance(row, dict)
        ]
    context = bounded_context

    data["provider_context"] = context
    observation_limit = 500 if high_confidence else 650
    observation_count = 5 if high_confidence else 7
    data["observations"] = [
        _compact(item, string_limit=observation_limit)
        for item in data.get("observations", [])[:observation_count]
    ]
    data["census_prior"] = _compact(
        data.get("census_prior") or {},
        string_limit=450 if high_confidence else 600,
    )
    return data

def compact_experience(
    row: dict[str, Any],
    *,
    text_limit: int,
) -> dict[str, Any]:
    keep = (
        "experience_id",
        "providers",
        "failure_class",
        "symptom_families",
        "signals",
        "strategy",
        "avoid",
        "lesson",
        "_retrieval_score",
        "_structural_score",
    )
    return {
        key: _compact(row.get(key), string_limit=text_limit)
        for key in keep
        if key in row
    }

def compact_document(
    row: dict[str, Any],
    *,
    text_limit: int,
) -> dict[str, Any]:
    return {
        "source": _clip(row.get("source"), 80),
        "private_memory": bool(row.get("private_memory")),
        "proof_authority": bool(row.get("proof_authority")),
        "path": _clip(row.get("path"), 160),
        "heading": _clip(row.get("heading"), 180),
        "role": _clip(row.get("role"), 80),
        "authority": row.get("authority"),
        "text": _clip(row.get("text"), text_limit),
        "_document_score": row.get("_document_score"),
    }

def build_prompt_payload(
    request: RepairRequest,
    experiences: list[dict[str, Any]],
    documents: list[dict[str, Any]] | None = None,
    causal_prior: dict[str, Any] | None = None,
    mutation_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prior = causal_prior or {}
    policy = mutation_policy or {}
    # Verification tests are deterministic Brain policy. Do not spend LLM
    # context on re-sending a protocol the model is not allowed to weaken.
    model_policy = {
        key: value
        for key, value in policy.items()
        if key != "required_tests"
    }
    high_confidence = float(prior.get("confidence") or 0.0) >= 0.90
    mutation_allowed = bool(policy.get("allow_mutations"))

    if mutation_allowed:
        # Force is a code/data synthesis phase, not a research pass. Current
        # provider bytes + current failure evidence + one nearest experience are
        # enough; broad docs/private history only increase prefill latency and
        # were causing every 4-slot CPU request to time out.
        experience_limit = 1
        document_limit = 0
        experience_text_limit = 320
        document_text_limit = 0
    else:
        experience_limit = 2 if high_confidence else 4
        document_limit = 1 if high_confidence else 2
        experience_text_limit = 420 if high_confidence else 600
        document_text_limit = 650 if high_confidence else 900

    payload = {
        "request": compact_request(
            request,
            high_confidence=high_confidence,
            mutation_allowed=mutation_allowed,
        ),
        "causal_prior": _compact(prior, string_limit=500),
        "mutation_policy": _compact(model_policy, string_limit=500),
        "verification_owned_by_brain": True,
        "retrieved_experiences": [
            compact_experience(row, text_limit=experience_text_limit)
            for row in experiences[:experience_limit]
        ],
        "retrieved_documents": [
            compact_document(row, text_limit=document_text_limit)
            for row in (documents or [])[:document_limit]
        ],
        "context_budget": {
            "mode": "focused" if high_confidence else "exploratory",
            "experience_limit": experience_limit,
            "document_limit": document_limit,
        },
    }

    # Leave room inside a 4096-token llama.cpp context for the system prompt,
    # schema grammar and completion. Optional retrieval prose is dropped before
    # current provider evidence if the bounded payload is still oversized.
    import json
    def encoded_size() -> int:
        return len(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))

    if encoded_size() > 7600:
        payload["retrieved_documents"] = []
        payload["context_budget"]["document_limit"] = 0
    if encoded_size() > 7600:
        payload["retrieved_experiences"] = payload["retrieved_experiences"][:1]
        payload["context_budget"]["experience_limit"] = min(
            1, int(payload["context_budget"]["experience_limit"])
        )
    if encoded_size() > 7600:
        ctx = payload["request"].get("provider_context") or {}
        if isinstance(ctx, dict):
            ctx.pop("registered_patch_sources", None)
            ctx.pop("authored_module", None)
            published = ctx.get("published_bundle")
            if isinstance(published, dict):
                published.pop("providerBlocks", None)
    if encoded_size() > 7600:
        request_payload = payload["request"]
        request_payload["observations"] = [
            _compact(row, string_limit=180)
            for row in (request_payload.get("observations") or [])[:2]
        ]
        request_payload["census_prior"] = _compact(
            request_payload.get("census_prior") or {}, string_limit=180
        )
        ctx = request_payload.get("provider_context") or {}
        if isinstance(ctx, dict):
            request_payload["provider_context"] = {
                key: value
                for key, value in ctx.items()
                if key in {
                    "source_repo", "read_only", "provider_id",
                    "registered_patch_scripts", "advisor_experiment_history",
                }
            }
            history = request_payload["provider_context"].get("advisor_experiment_history")
            if isinstance(history, list):
                request_payload["provider_context"]["advisor_experiment_history"] = history[-2:]
        payload["causal_prior"] = _compact(payload["causal_prior"], string_limit=220)
        payload["mutation_policy"] = _compact(payload["mutation_policy"], string_limit=220)
    if encoded_size() > 7600:
        # This is a programming-contract failure, not a model/runtime failure.
        # Refuse to create an oversized request rather than let llama.cpp reject it.
        raise ValueError("advisor prompt payload exceeded bounded context budget")
    payload["context_budget"]["serialized_user_chars"] = encoded_size()
    payload["context_budget"]["max_serialized_user_chars"] = 7600
    return payload


def _force_structural_focus_keywords(request: RepairRequest) -> tuple[str, ...]:
    """Derive bounded source-focus tokens from current structural evidence.

    If an exact HTML class token is also the prefix of sibling class tokens,
    word-boundary based selectors can accidentally match the whole prefix
    family. Surface that collision to Force without retaining HTML or URLs.
    """
    class_tokens: list[str] = []

    def record_token(raw: object) -> None:
        token = str(raw or "").strip().casefold()
        if (
            2 <= len(token) <= 48
            and token[0].isalpha()
            and all(ch.isalnum() or ch in "_-" for ch in token)
            and token not in class_tokens
        ):
            class_tokens.append(token)

    for row in request.observations or []:
        if not isinstance(row, dict) or str(row.get("source") or "") not in {"targeted-regression-current", "census-sharded-current"}:
            continue
        value = row.get("value") if isinstance(row.get("value"), dict) else {}
        for hint in (value.get("structureHints") or [])[:8]:
            text = str(hint or "")
            match = re.search(r"(?:^|[;:])classes=([^;]+)", text)
            if match:
                for raw in match.group(1).split(","):
                    record_token(raw)

            # Current targeted evidence may expose the richer privacy-safe
            # classFacts form without duplicating a legacy classes= list.
            # The first field inside each bounded fact is the exact CSS token.
            if "classFacts=" in text:
                facts_text = text.split("classFacts=", 1)[1]
                for fragment in facts_text.split("[")[1:]:
                    raw_fact = fragment.split("]", 1)[0]
                    record_token(raw_fact.split(";", 1)[0])
    collisions = [
        token for token in class_tokens
        if any(
            other != token
            and (other.startswith(token + "-") or other.startswith(token + "_"))
            for other in class_tokens
        )
    ]
    if not collisions:
        return ()
    return ("classblocks", "classtext", "selector", "class=", *collisions[:2])

_FORCE_SOURCE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "provider_transport_gap": (
        "fetch(", "headers", "user-agent", "referer", "cookie", "origin", "request", "timeout",
    ),
    "route_proven_gap": (
        "resolve", "detail", "player", "embed", "episode", "watch", "search", "route", "fetch(",
    ),
    "chain_terminal_gap": (
        "confirm", "internal", "resolve", "m3u8", "iframe", "terminal", "crawl", "source",
    ),
}

def _force_source_windows(
    value: Any,
    failure_class: str,
    *,
    max_chars: int = 4000,
    max_windows: int = 4,
    focus_keywords: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Return exact current-byte slices around family-relevant runtime code.

    Windows never contain synthetic clipping markers. Each window carries a
    deterministic focus offset for the causal keyword that selected it. The
    model only has to choose a window and exact local bytes; deterministic Brain
    code may disambiguate repeated local snippets against this focus and the
    complete unabridged source.
    """
    text = str(value or "")
    if not text.strip():
        return []

    lowered = text.casefold()
    base_keywords = _FORCE_SOURCE_KEYWORDS.get(
        str(failure_class or "").strip().casefold(),
        ("resolve", "fetch(", "search", "player", "embed", "source"),
    )
    keywords = tuple(dict.fromkeys([
        *(str(x).casefold() for x in focus_keywords if str(x).strip()),
        *base_keywords,
    ]))
    minimum_code_offset = min(1000, max(0, len(text) // 8))

    def _focus_position() -> tuple[int, str]:
        for keyword in keywords:
            positions: list[int] = []
            cursor = 0
            while len(positions) < 12:
                position = lowered.find(keyword.casefold(), cursor)
                if position < 0:
                    break
                positions.append(position)
                cursor = position + max(1, len(keyword))
            if not positions:
                continue
            chosen = next(
                (candidate for candidate in positions if candidate >= minimum_code_offset),
                positions[-1],
            )
            return chosen, keyword
        return min(len(text) // 2, max(0, len(text) - 1)), "fallback_center"

    if len(text) <= max_chars:
        focus, reason = _focus_position()
        return [{
            "id": "w1",
            "offset": 0,
            "end_offset": len(text),
            "reason": reason if reason != "fallback_center" else "full_source",
            "focus_offset": focus,
            "source": text,
        }]

    intervals: list[tuple[int, int, str, int]] = []
    for keyword in keywords:
        positions: list[int] = []
        cursor = 0
        while len(positions) < 12:
            position = lowered.find(keyword.casefold(), cursor)
            if position < 0:
                break
            positions.append(position)
            cursor = position + max(1, len(keyword))
        if not positions:
            continue
        position = next(
            (candidate for candidate in positions if candidate >= minimum_code_offset),
            positions[-1],
        )
        start = max(0, position - 380)
        end = min(len(text), position + len(keyword) + 620)
        if any(
            start < existing_end and end > existing_start
            for existing_start, existing_end, _, _ in intervals
        ):
            continue
        intervals.append((start, end, keyword, position))
        if len(intervals) >= max_windows:
            break

    if not intervals:
        head = min(2000, max_chars // 2)
        tail = min(2000, max_chars - head)
        intervals = [
            (0, head, "fallback_head", min(head // 2, max(0, head - 1))),
            (
                max(0, len(text) - tail),
                len(text),
                "fallback_tail",
                max(0, len(text) - max(1, tail // 2)),
            ),
        ]

    windows: list[dict[str, Any]] = []
    used = 0
    for start, end, reason, focus in intervals:
        remaining = max_chars - used
        if remaining <= 0:
            break
        end = min(end, start + remaining)
        source = text[start:end]
        if not source:
            continue
        local_focus = max(0, min(len(source) - 1, focus - start))
        windows.append({
            "id": f"w{len(windows) + 1}",
            "offset": start,
            "end_offset": end,
            "reason": reason,
            "focus_offset": local_focus,
            "source": source,
        })
        used += len(source)
    return windows


def _force_window_kwargs_for_request(request: RepairRequest) -> dict[str, int]:
    feedback = any(
        isinstance(row, dict)
        and str(row.get("stage") or "") == "force_validation_feedback"
        for row in (request.observations or [])
    )
    failure = str(request.failure_class or "").strip().casefold()
    # Route-proven gaps are dominated by one route/search dispatcher plus
    # its strongest selector/parser callee. Keep exactly that causal pair on
    # both initial and validation attempts. Chain/media gaps retain the wider
    # graph because their terminal parser is frequently two calls downstream.
    if failure == "route_proven_gap":
        return {"max_chars": 1100 if feedback else 1250, "max_windows": 1, "max_units": 2}
    return (
        {"max_chars": 1600, "max_windows": 2, "max_units": 3}
        if feedback
        else {"max_chars": 2000, "max_windows": 2, "max_units": 4}
    )


def _force_edit_units(
    value: Any,
    failure_class: str,
    *,
    max_chars: int = 2600,
    max_windows: int = 3,
    max_units: int = 9,
    focus_keywords: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Return exact, bounded, structurally safe edit units with causal diversity."""
    text = str(value or "")
    windows = _force_source_windows(
        text,
        failure_class,
        max_chars=max_chars,
        max_windows=max_windows,
        focus_keywords=focus_keywords,
    )
    ranked = []
    seen = set()
    family_key = str(failure_class or "").strip().casefold()
    family_keywords = tuple(dict.fromkeys([
        *(
            str(keyword or "").strip().casefold()
            for keyword in focus_keywords
            if str(keyword or "").strip()
        ),
        *(
            str(keyword or "").strip().casefold()
            for keyword in _FORCE_SOURCE_KEYWORDS.get(family_key, ())
            if str(keyword or "").strip()
        ),
    ]))

    def safe(
        fragment: str,
        absolute: int,
        *,
        max_len: int = 320,
        allow_function: bool = False,
    ) -> bool:
        stripped = fragment.strip()
        if len(stripped) < 6 or len(stripped) > max_len:
            return False
        if not allow_function and stripped.startswith(("function ", "async function ", "class ", "else", "catch", "finally")):
            return False
        if (not allow_function and "function " in stripped) or stripped.count("{") != stripped.count("}"):
            return False
        if absolute > 0 and text[absolute - 1:absolute].isalnum() and text[absolute:absolute + 1].isalnum():
            return False
        end = absolute + len(fragment)
        if end < len(text) and text[end - 1:end].isalnum() and text[end:end + 1].isalnum():
            return False
        return True

    for window_index, window in enumerate(windows):
        source = str(window.get("source") or "")
        if not source:
            continue
        base = int(window.get("offset") or 0)
        focus = int(window.get("focus_offset") or 0)
        quote = ""
        escaped = False
        paren_depth = bracket_depth = 0
        statement_start = 0
        candidates = []
        for index, char in enumerate(source):
            if quote:
                if escaped:
                    escaped = False
                    continue
                if char == "\\":
                    escaped = True
                    continue
                if char == quote:
                    quote = ""
                continue
            if char in {'"', "'", "`"}:
                quote = char
                continue
            if char == "(":
                paren_depth += 1
                continue
            if char == ")":
                paren_depth = max(0, paren_depth - 1)
                continue
            if char == "[":
                bracket_depth += 1
                continue
            if char == "]":
                bracket_depth = max(0, bracket_depth - 1)
                continue
            if paren_depth or bracket_depth:
                continue
            if char in "{}\n":
                statement_start = index + 1
                continue
            if char != ";":
                continue
            left, right = statement_start, index + 1
            while left < right and source[left].isspace():
                left += 1
            while right > left and source[right - 1].isspace():
                right -= 1
            if right > left:
                candidates.append((left, right))
            statement_start = index + 1

        candidates.sort()

        # Causally named functions are available as exact bounded units when a
        # repair cannot be expressed by one or a few adjacent statements. The
        # model still selects a stable unit id; Brain owns current bytes.
        function_units: list[tuple[int, int, str]] = []
        function_pattern = re.compile(
            r"\b(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\([^)]*\)\s*\{"
        )
        for match in function_pattern.finditer(source):
            name = str(match.group(1) or "").casefold()
            # Do not hide generic provider functions from FORCE. Provider-owned
            # functions such as getStreams/extract/resolve are often the safest
            # place to invent a new bounded Bloc even when their names do not
            # contain the failure taxonomy keywords. Keyword matches still rank
            # higher below; generic complete functions remain a fallback.
            brace = source.find("{", match.start(), match.end() + 1)
            if brace < 0:
                continue
            quote = ""
            escaped = False
            depth = 0
            end = -1
            for cursor in range(brace, len(source)):
                char = source[cursor]
                if quote:
                    if escaped:
                        escaped = False
                        continue
                    if char == "\\":
                        escaped = True
                        continue
                    if char == quote:
                        quote = ""
                    continue
                if char in {'"', "'", "`"}:
                    quote = char
                    continue
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        end = cursor + 1
                        break
            if end < 0:
                continue
            fragment = source[match.start():end]
            if 24 <= len(fragment.strip()) <= 1800:
                function_units.append((match.start(), end, "function_unit"))

        expanded: list[tuple[int, int, str]] = [(left, right, "statement") for left, right in candidates]
        # Add bounded adjacent statement sequences. Gaps must be whitespace only,
        # so a sequence never crosses a brace or another structural delimiter.
        for start_index, (left, right) in enumerate(candidates):
            end = right
            for width in range(2, 5):
                next_index = start_index + width - 1
                if next_index >= len(candidates):
                    break
                next_left, next_right = candidates[next_index]
                if source[end:next_left].strip():
                    break
                end = next_right
                fragment = source[left:end]
                if len(fragment.strip()) > 700:
                    break
                expanded.append((left, end, "statement_sequence"))

        expanded.extend(function_units[:3])

        for left, right, kind in expanded:
            fragment = source[left:right]
            absolute = base + left
            key = (absolute, absolute + len(fragment))
            max_len = 1800 if kind == "function_unit" else 700 if kind == "statement_sequence" else 320
            if key in seen or not safe(
                fragment,
                absolute,
                max_len=max_len,
                allow_function=kind == "function_unit",
            ):
                continue
            seen.add(key)
            center = left + max(1, len(fragment)) // 2
            contains_focus = left <= focus < right
            distance = 0 if contains_focus else abs(center - focus)
            kind_rank = 0 if kind == "function_unit" else 1 if kind == "statement_sequence" else 2
            ranked.append(((0 if contains_focus else 1, kind_rank, distance, window_index, absolute), {
                "window_id": str(window.get("id") or ""),
                "offset": absolute,
                "end_offset": absolute + len(fragment),
                "reason": str(window.get("reason") or ""),
                "kind": kind,
                "source": fragment,
            }))

    # Compact windows can land inside a useful function and hide its declaration
    # or closing brace. Scan the complete exact provider-owned source for bounded
    # causal functions too. This expands choice, not authority: the selected bytes
    # are still exact current bytes and the deterministic sandbox remains proof.
    function_pattern = re.compile(
        r"\b(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*\s*\([^)]*\)\s*\{"
    )
    absolute_focuses = [
        int(window.get("offset") or 0) + int(window.get("focus_offset") or 0)
        for window in windows
    ]
    for match in function_pattern.finditer(text):
        brace = text.find("{", match.start(), match.end() + 1)
        if brace < 0:
            continue
        quote = ""
        escaped = False
        depth = 0
        end = -1
        for cursor in range(brace, len(text)):
            char = text[cursor]
            if quote:
                if escaped:
                    escaped = False
                    continue
                if char == "\\":
                    escaped = True
                    continue
                if char == quote:
                    quote = ""
                continue
            if char in {'"', "\'", "`"}:
                quote = char
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = cursor + 1
                    break
        if end < 0:
            continue
        fragment = text[match.start():end]
        lowered_fragment = fragment.casefold()
        if not (24 <= len(fragment.strip()) <= 1800):
            continue
        key = (match.start(), end)
        if key in seen or not safe(fragment, match.start(), max_len=1800, allow_function=True):
            continue
        seen.add(key)
        center = match.start() + max(1, len(fragment)) // 2
        nearest_index = (
            min(range(len(windows)), key=lambda index: abs(center - absolute_focuses[index]))
            if windows else 0
        )
        nearest = windows[nearest_index] if windows else {}
        focus = absolute_focuses[nearest_index] if absolute_focuses else center
        contains_focus = match.start() <= focus < end
        distance = 0 if contains_focus else abs(center - focus)
        causal_hits = sum(1 for keyword in family_keywords if keyword in lowered_fragment)
        ranked.append((
            (0 if contains_focus else 1, 0, -causal_hits, distance, nearest_index, match.start()),
            {
                "window_id": str(nearest.get("id") or "w1"),
                "offset": match.start(),
                "end_offset": end,
                "reason": "causal_function_body" if causal_hits else "generic_function_fallback",
                "kind": "function_unit",
                "source": fragment,
            },
        ))

    ranked.sort(key=lambda item: item[0])

    # Reserve the two strongest whole functions, then follow a bounded two-level
    # exact local call graph before spending remaining slots on micro-units.
    # Structural provider runtimes are commonly split as
    # resolve -> search/find/current -> player/link/parser/terminal helper.
    # One-hop traversal can expose the dispatcher while still hiding the parser
    # or terminal helper that actually owns the failing response shape.
    selected = []
    selected_keys = set()
    function_rows = []
    function_by_name: dict[str, dict[str, Any]] = {}
    function_rank: dict[tuple[int, int], int] = {}
    for _, row in ranked:
        if row.get("kind") != "function_unit":
            continue
        key = (int(row.get("offset") or 0), int(row.get("end_offset") or 0))
        if key in function_rank:
            continue
        function_rank[key] = len(function_rows)
        function_rows.append(row)
        match = re.match(
            r"\s*(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(",
            str(row.get("source") or ""),
        )
        if match and match.group(1) not in function_by_name:
            function_by_name[match.group(1)] = row

    # When current evidence identifies a concrete structural selector/parser
    # collision, keep the editable surface on the named structural helpers.
    # Otherwise the generic route ranking may still offer resolve/detail and a
    # small model can paste parser logic into the dispatcher. This narrows choice,
    # not authority: exact bytes and downstream sandbox proof remain unchanged.
    structural_focus_name_tokens = [
        re.sub(r"[^a-z0-9_$]+", "", str(token or "").casefold())
        for token in focus_keywords
        if re.sub(r"[^a-z0-9_$]+", "", str(token or "").casefold())
        not in {"selector", "class"}
    ][:4]
    if structural_focus_name_tokens:
        focused_rows = []
        for row in function_rows:
            match = re.match(
                r"\s*(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(",
                str(row.get("source") or ""),
            )
            if not match:
                continue
            normalized_name = re.sub(r"[^a-z0-9_$]+", "", match.group(1).casefold())
            if any(token in normalized_name for token in structural_focus_name_tokens):
                focused_rows.append(row)
        if focused_rows:
            function_rows = focused_rows
            function_by_name = {}
            function_rank = {}
            for row in function_rows:
                key = (int(row.get("offset") or 0), int(row.get("end_offset") or 0))
                function_rank[key] = len(function_rank)
                match = re.match(
                    r"\s*(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(",
                    str(row.get("source") or ""),
                )
                if match and match.group(1) not in function_by_name:
                    function_by_name[match.group(1)] = row

    structural_gap = family_key in {"route_proven_gap", "chain_terminal_gap", "media_extraction_gap"}
    # On structural gaps, reserve one strongest causal root and spend the remaining
    # budget following its local call graph. Reserving an unrelated generic helper
    # as slot two can hide the parser/terminal helper two calls downstream.
    initial_function_slots = 1 if structural_gap and max_units >= 2 else min(2, max_units)
    for row in function_rows[:initial_function_slots]:
        key = (int(row.get("offset") or 0), int(row.get("end_offset") or 0))
        selected.append(row)
        selected_keys.add(key)

    if len(selected) < max_units and function_by_name:
        role_tokens = {
            re.sub(r"[^a-z0-9_$]+", "", keyword.casefold())
            for keyword in family_keywords
            if re.sub(r"[^a-z0-9_$]+", "", keyword.casefold())
        }
        role_tokens.update({"find", "link", "server", "tab"})
        neighbors: dict[tuple[int, int], tuple[tuple[int, ...], dict[str, Any]]] = {}
        frontier = [(index, row, 0) for index, row in enumerate(list(selected))]
        seen_frontier: set[tuple[int, int, int]] = set()
        while frontier:
            root_index, root, depth = frontier.pop(0)
            root_key = (
                int(root.get("offset") or 0),
                int(root.get("end_offset") or 0),
                depth,
            )
            if root_key in seen_frontier or depth >= 2:
                continue
            seen_frontier.add(root_key)
            root_source = str(root.get("source") or "")
            referenced_names: list[tuple[int, str]] = [
                (match.start(), match.group(1))
                for match in re.finditer(
                    r"\b([A-Za-z_$][A-Za-z0-9_$]*)\s*\(",
                    root_source,
                )
            ]
            # Parser/terminal helpers are often passed as callbacks rather than
            # invoked directly: promise.then(parseSources), rows.map(normalize),
            # etc. Treat those named function references as causal edges too.
            referenced_names.extend(
                (match.start(), match.group(1))
                for match in re.finditer(
                    r"\.(?:then|catch|finally|map|flatMap|filter|find|some|every|forEach|reduce)"
                    r"\s*\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\b",
                    root_source,
                )
            )
            seen_names: set[tuple[int, str]] = set()
            for call_index, (call_offset, name) in enumerate(
                sorted(referenced_names, key=lambda item: (item[0], item[1]))
            ):
                name_key = (call_offset, name)
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)
                callee = function_by_name.get(name)
                if callee is None:
                    continue
                key = (
                    int(callee.get("offset") or 0),
                    int(callee.get("end_offset") or 0),
                )
                lowered_name = name.casefold()
                lowered_source = str(callee.get("source") or "").casefold()
                name_hits = sum(1 for token in role_tokens if token in lowered_name)
                body_hits = sum(
                    1 for keyword in family_keywords
                    if keyword in lowered_source
                )
                score = (
                    depth + 1,
                    -name_hits,
                    -body_hits,
                    root_index,
                    call_index,
                    function_rank.get(key, 9999),
                )
                if key not in selected_keys:
                    current = neighbors.get(key)
                    if current is None or score < current[0]:
                        row_copy = dict(callee)
                        row_copy["reason"] = (
                            "causal_call_neighbor"
                            if depth == 0
                            else "causal_call_neighbor_depth2"
                        )
                        neighbors[key] = (score, row_copy)
                frontier.append((root_index, callee, depth + 1))
        ordered_neighbors = [
            row for _, row in sorted(neighbors.values(), key=lambda item: item[0])
        ]
        # Structural provider failures often hide the real parser/terminal step
        # behind a dispatcher and one intermediate request helper. With the
        # normal four-unit budget, depth-1 callees alone can consume every
        # remaining slot even though a useful depth-2 function was discovered.
        # Reserve one slot for the strongest second-hop causal neighbor when
        # possible; exact-byte and sandbox authority are unchanged.
        if failure_class in {"route_proven_gap", "chain_terminal_gap"} and max_units >= 4:
            for row in ordered_neighbors:
                if row.get("reason") != "causal_call_neighbor_depth2":
                    continue
                key = (int(row.get("offset") or 0), int(row.get("end_offset") or 0))
                if key in selected_keys:
                    continue
                selected.append(row)
                selected_keys.add(key)
                break
        for row in ordered_neighbors:
            key = (int(row.get("offset") or 0), int(row.get("end_offset") or 0))
            if key in selected_keys:
                continue
            selected.append(row)
            selected_keys.add(key)
            if len(selected) >= max_units:
                break

    for _, row in ranked:
        if len(selected) >= max_units:
            break
        key = (int(row.get("offset") or 0), int(row.get("end_offset") or 0))
        if key in selected_keys:
            continue
        selected.append(row)
        selected_keys.add(key)

    per_window = {}
    units = []
    for row in selected:
        wid = str(row.get("window_id") or "")
        per_window[wid] = per_window.get(wid, 0) + 1
        item = dict(row)
        item["id"] = f"{wid}u{per_window[wid]}"
        units.append(item)
    return units

def build_force_prompt_payload(
    request: RepairRequest,
    causal_prior: dict[str, Any] | None = None,
    mutation_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Minimal provider-local context for CPU-bound Force synthesis.

    The Force model does not need RAG documents, historical prose, verification
    tests or the complete provider context. Deterministic NiakVIO already owns
    those. Give the model only current causal state plus the exact authored
    mutation surface it is allowed to edit.
    """
    prior = causal_prior or {}
    policy = mutation_policy or {}
    context = request.provider_context or {}

    allowed_scopes = list(policy.get("allowed_scopes") or request.allowed_mutations or [])
    validation_feedback = next(
        (
            row
            for row in (request.observations or [])
            if isinstance(row, dict)
            and str(row.get("stage") or "") == "force_validation_feedback"
        ),
        None,
    )
    force_window_kwargs = _force_window_kwargs_for_request(request)
    structural_focus_keywords = _force_structural_focus_keywords(request)
    # Editable units are derived from the full bounded causal windows, but the
    # model does not need those same bytes duplicated verbatim as context.
    # Keep a smaller context view to reduce CPU prompt ingestion at fleet scale.
    route_gap = str(request.failure_class or "").strip().casefold() == "route_proven_gap"
    context_window_kwargs = (
        {"max_chars": 500, "max_windows": 1}
        if route_gap
        else (
            {"max_chars": 650, "max_windows": 1}
            if validation_feedback is not None
            else {"max_chars": 1000, "max_windows": 2}
        )
    )
    registered = context.get("registered_patch_sources")
    target: dict[str, Any] = {}
    if "provider_patch" in allowed_scopes and isinstance(registered, dict) and registered:
        path, source = next(iter(registered.items()))
        target = {
            "scope": "provider_patch",
            "path": str(path)[:240],
            "source_windows": _force_source_windows(source, request.failure_class, focus_keywords=structural_focus_keywords, **context_window_kwargs),
            "editable_units": _force_edit_units(source, request.failure_class, focus_keywords=structural_focus_keywords, **force_window_kwargs),
        }
    elif "provider_js" in allowed_scopes and context.get("authored_module"):
        target = {
            "scope": "provider_js",
            "path": f"engine_v2/providers/{request.provider_id}.mjs",
            "source_windows": _force_source_windows(context.get("authored_module"), request.failure_class, focus_keywords=structural_focus_keywords, **context_window_kwargs),
            "editable_units": _force_edit_units(context.get("authored_module"), request.failure_class, focus_keywords=structural_focus_keywords, **force_window_kwargs),
        }
    elif "provider_data" in allowed_scopes and context.get("override"):
        target = {
            "scope": "provider_data",
            "path": "provider-overrides.json > provider_patches[provider_id]",
            "source": _clip(context.get("override"), 1200),
        }

    new_bloc_target: dict[str, Any] = {}
    runtime_source = (
        context.get("preferredRuntimeMutationSource")
        or context.get("runtimeMutationSource")
    )
    if runtime_source and "provider_bloc" in allowed_scopes:
        new_bloc_target = {
            "scope": "provider_bloc",
            "filename": _clip(context.get("runtimeMutationFilename"), 180),
            "source_windows": _force_source_windows(runtime_source, request.failure_class, focus_keywords=structural_focus_keywords, **context_window_kwargs),
            "editable_units": _force_edit_units(runtime_source, request.failure_class, focus_keywords=structural_focus_keywords, **force_window_kwargs),
        }

    observation_source = (
        [validation_feedback]
        if validation_feedback is not None
        else list(request.observations or [])[:2]
    )
    observations = [
        _compact_force_observation(row)
        for row in observation_source
        if isinstance(row, dict)
    ]
    references = []
    reference_source = (
        []
        if validation_feedback is not None
        else (context.get("validated_reference_patterns") or [])[:1]
    )
    for raw in reference_source:
        if not isinstance(raw, dict):
            continue
        references.append({
            "provider": _clip(raw.get("provider"), 80),
            "status": "FULL OK",
            "source_kind": _clip(raw.get("source_kind"), 180),
            "technical_features": [str(x)[:40] for x in (raw.get("technical_features") or [])[:8]],
            "snippet": _clip(raw.get("snippet"), 500),
            "proof_authority": False,
            "copy_policy": "pattern_reference_only",
            "novelty_allowed": True,
        })
    force_failures = [
        {
            "lastReason": _clip(row.get("lastReason"), 180),
            "lastOutcome": _clip(row.get("lastOutcome"), 60),
            "consecutiveFailures": int(row.get("consecutiveFailures") or 0),
            "executionObserved": row.get("executionObserved") is True,
            "rejectedMechanisms": [
                {
                    "scope": _clip(item.get("scope"), 40),
                    "operation": _clip(item.get("operation"), 40),
                    **({"family": _clip(item.get("family"), 80)} if item.get("family") else {}),
                    **({"path": _clip(item.get("path"), 160)} if item.get("path") else {}),
                }
                for item in (row.get("lastMutationSummary") or [])[:4]
                if isinstance(item, dict)
            ],
        }
        for row in (context.get("advisor_experiment_history") or [])
        if isinstance(row, dict)
        and str(row.get("memoryRole") or "") == "force_sandbox_execution"
    ][:3]
    census = {}
    return {
        "provider_id": request.provider_id,
        "failure_class": request.failure_class,
        "status": request.status,
        "supported_types": list(request.supported_types or [])[:4],
        "causal_prior": {
            "target_layer": prior.get("target_layer"),
            "confidence": prior.get("confidence"),
            "strategy_prior": prior.get("strategy_prior"),
        },
        "mutation_policy": {
            "allow_mutations": bool(policy.get("allow_mutations")),
            "allowed_scopes": allowed_scopes,
            "force_abstain": bool(policy.get("force_abstain")),
            "reason": _clip(policy.get("reason"), 260),
        },
        "structural_focus": list(structural_focus_keywords)[:6],
        "current_observations": observations,
        "prior_force_sandbox_failures": force_failures,
        "census_prior": census,
        "validated_reference_patterns": references,
        "reference_policy": {
            "role": "optional_implementation_inspiration",
            "may_adapt_combine_or_ignore": True,
            "novel_provider_local_mechanisms_allowed": True,
            "never_copy_routes_hosts_urls_or_provider_specific_literals": True,
            "reference_is_not_proof": True,
        },
        "mutation_target": target,
        "new_bloc_target": new_bloc_target,
        "output_contract": {
            "max_edits": 1,
            "provider_local_only": True,
            "file_edit_format": "unit_id_replace" if target.get("scope") in {"provider_patch", "provider_js"} else "provider_data_mutation",
            "generated_bloc_format": "family_unit_id_replace" if new_bloc_target else None,
            "unit_id_selects_exact_current_bytes": bool(target.get("scope") in {"provider_patch", "provider_js"} or new_bloc_target),
            "model_never_copies_find_bytes": True,
            "brain_resolves_window_occurrence_by_causal_focus": True,
            "brain_resolves_global_anchor_uniqueness": True,
            "source_windows_are_exact_current_bytes": True,
            "validation_retry_context": "focused" if validation_feedback is not None else "compact_initial",
        },
    }
