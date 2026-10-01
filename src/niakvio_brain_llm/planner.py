from __future__ import annotations

import ast
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .backend import ModelBackend
from .contracts import RepairProposal, RepairRequest
from .document_memory import DocumentStore
from .mutation_guard import validate_mutations
from .policy import build_mutation_policy
from .priors import build_causal_prior
from .prompting import _force_edit_units, _force_source_windows, _force_structural_focus_keywords, _force_window_kwargs_for_request, build_force_prompt_payload, build_prompt_payload
from .retrieval import ExperienceStore
from .schema import REPAIR_PROPOSAL_SCHEMA, compact_force_schema_for, proposal_schema_for
from .verification_plan import recommended_tests

SYSTEM_PROMPT = """You are NiakVIO Brain LLM, a bounded repair planner.
Use high-confidence causal_prior and strategy_prior as authoritative planning constraints. If causal_prior.confidence >= 0.90 and strategy_prior is non-empty, copy strategy_prior verbatim into the strategy field.
Use mutation_policy as an execution boundary, not a suggestion.
Verification tests are owned and enforced by the deterministic Brain after your proposal. Do not use test names as the repair strategy.
NiakVIO tests are the only proof authority.
Retrieved experiences and documents are memory/context, not proof.
Respect document authority: current census/state > recent MEMORY > field evidence > historical docs.
Never let stale historical text override current repository state.
Never mutate outside allowed_mutations or touch forbidden_mutations.
If mutation_policy forbids mutation, mutations must be empty.
Never invent placeholder URLs, example domains, fake endpoints, fake diffs or unobserved current facts.
If a fresh value required for a patch is absent, abstain and request the exact diagnostic/probe needed.
Prefer the smallest causal change.\nFor provider-layer repairs, also propose an abstract experiment spec. It may only steer existing deterministic sandbox knobs: route_policy, recipe_policy, role_order, terminal_only, alias_search, response_salvage, document_request_mining, session_bootstrap, max_depth, max_pages, max_embeds, and max_recipe_passes. Never put URLs, routes, headers, tokens, cookies, source text, diffs, or private-memory text in experiment. Different specs are distinct hypotheses even inside the same strategy family.\nWhen advisor_only context contains provider_context.advisor_experiment_history, those rows are negative execution memory. Keep any high-confidence strategy_prior unchanged, but materially vary the experiment from exhausted advisor attempts; do not deliberately repeat a failed experiment fingerprint. Prefer changes that target the recorded lastReason or observed pipeline stage.\nprovider_context.published_bundle is the exact generated bundle referenced by NiakVIO manifest.json. Treat it as read-only current-byte evidence: compare its providerBlocks against registered_patch_sources/authored_module/override to locate projection or runtime drift, but NEVER target providers/*.js or provider-disabled/*.js as a mutation path.\n\nMutation DSL:
- provider_data paths are relative to provider-overrides.json > provider_patches[provider_id], never file paths.
- provider_patch may target only an already-registered scripts/provider_patches/* Bloc listed in provider_context.registered_patch_scripts.
- provider_bloc may request one bounded managed runtime Bloc synthesized from current provider-owned runtime bytes; it supplies family + exact unique find + replace, never a file path or Python source.
- provider_js may target only engine_v2/providers/<provider_id>.mjs.
Never return shell commands or edits to unrelated files.
Return one JSON object only with provider_id, diagnosis, strategy, confidence, target_layer,
evidence, mutations, experiment, tests, abstain and abstain_reason.
"""

COMPACT_FORCE_SYSTEM_PROMPT = """NiakVIO Brain Force. JSON only:
{"edit":<one provider-local edit or null>,"abstain_reason":"<short>"}
Use only current evidence and editable_units. Never invent network facts, URLs, routes, hosts, headers, tokens, cookies or placeholders.
One edit max:
- provider_data: {scope,operation,path,value?}
- provider_patch/provider_js: {scope,path,unit_id,replace}
- provider_bloc: {scope:"provider_bloc",family,unit_id,replace}
unit_id MUST come from editable_units; Brain owns exact find bytes.
For kind=function_unit, replace is the NEW FUNCTION BODY ONLY. Never emit or rename the function declaration/name/signature; Brain preserves it.
Existing-file replace <=640 chars unless function_unit; provider_bloc replace <=1200 chars.
Prefer runtime_template_prior/current runtime reuse before a novel Bloc. A new provider-local mechanism is allowed when current evidence supports it.
Never cosmetically repeat prior_force_sandbox_failures. force_portfolio_reservations are same-run candidates already reserved for sandbox; do not repeat them. force_validation_feedback requires a materially different valid edit or abstention.
Abstain only when required current network facts are absent or no complete syntax-safe unit can carry the repair."""


def _extract_json(text: str) -> dict[str, Any]:
    value = text.strip()
    for fence in ("~~~", chr(96) * 3):
        if value.startswith(fence):
            lines = value.splitlines()
            value = "\n".join(lines[1:-1]).strip()
            if value.casefold().startswith("json"):
                value = value[4:].lstrip()
            break
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("model response must be a JSON object")
    return parsed


def _function_names(value: str) -> set[str]:
    return set(re.findall(
        r"\b(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(",
        value,
    ))


def _preserve_selected_function_envelope(
    find: str,
    replace: str,
    *,
    normalize_explicit_wrapper: bool = False,
) -> str:
    """Keep the exact selected function declaration for function-unit edits.

    ``unit_id`` binds the mutation to exact current bytes. Body-only output is
    always wrapped in the selected declaration. For generated provider_bloc
    synthesis only, a complete single-function wrapper may also be normalized
    to the selected identity; authored provider_patch/provider_js surfaces keep
    explicit signature drift fail-closed.
    """
    find_names = _function_names(find)
    if len(find_names) != 1:
        return replace
    match = re.match(
        r"(?s)^(\s*(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*\s*\([^)]*\)\s*\{)(.*)(\}\s*)$",
        find,
    )
    if not match:
        return replace

    stripped = str(replace or "").strip()
    declaration = re.compile(
        r"^\s*(?P<async>async\s+)?function\s+"
        r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*"
        r"\((?P<params>[^)]*)\)\s*\{",
        re.S,
    )
    find_decl = declaration.match(find)
    replace_decl = declaration.match(stripped)
    if replace_decl:
        replace_names = _function_names(stripped)
        if len(replace_names) != 1 or not stripped.endswith("}") or not find_decl:
            return replace
        find_identity = (
            bool(find_decl.group("async")),
            find_decl.group("name"),
            re.sub(r"\s+", "", find_decl.group("params")),
        )
        replace_identity = (
            bool(replace_decl.group("async")),
            replace_decl.group("name"),
            re.sub(r"\s+", "", replace_decl.group("params")),
        )
        if replace_identity == find_identity:
            return stripped
        if not normalize_explicit_wrapper:
            raise ValueError("selected function declaration/signature changed")
        _node_check_javascript(stripped)
        body = stripped[replace_decl.end():-1]
        return match.group(1) + body.strip() + match.group(3)

    return match.group(1) + stripped + match.group(3)

def _compact_without_space(value: str) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _normalized_js_identity(value: str) -> str:
    """Remove only obvious boolean identity operands for no-op detection."""
    text = str(value or "")
    previous = None
    patterns = (
        (r"\s*\|\|\s*(?:false|0)(?=\s*[,;)\]}]|\s*\b(?:return|throw)\b|\s*$)", ""),
        (r"\s*&&\s*(?:true|1)(?=\s*[,;)\]}]|\s*\b(?:return|throw)\b|\s*$)", ""),
    )
    while previous != text:
        previous = text
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return re.sub(r"\s+", "", text)


def _reject_semantic_identity_edit(find: str, replace: str) -> None:
    if find == replace:
        raise ValueError("compact Force edit is a no-op")
    if _normalized_js_identity(find) == _normalized_js_identity(replace):
        raise ValueError("compact Force edit is a semantic no-op")


def _reject_partial_function_anchor(
    find: str,
    replace: str,
    *,
    allow_new_helpers: bool = False,
) -> None:
    """Reject structurally partial or neighbor-smashing helper edits."""
    find_names = _function_names(find)
    replace_names = _function_names(replace)
    if find_names:
        # Compact Force may replace an entire helper, but it must anchor a complete
        # function body. Replacing only a prefix leaves the old tail behind.
        if find.count("{") > find.count("}"):
            raise ValueError("compact Force function anchor is structurally incomplete")
        missing = find_names - replace_names
        if missing:
            raise ValueError("compact Force replacement may not silently remove a helper function declaration")
    added = replace_names - find_names
    if added and not allow_new_helpers:
        raise ValueError("compact Force replacement may not absorb a neighboring helper function")
    if re.search(r"\basync\s+async\b|\bfunction\s+function\b|\breturn\s+return\b", replace):
        raise ValueError("compact Force replacement contains duplicated JavaScript control tokens")

    # Neutral boolean constants inside a control condition are a common LLM
    # pseudo-fix: they change bytes but not behavior.
    if re.search(r"\b(?:if|while)\s*\(", replace):
        neutral = re.sub(r"\|\|\s*(?:0|false)\b|&&\s*(?:1|true)\b", "", replace, flags=re.I)
        if _compact_without_space(neutral) == _compact_without_space(find) and _compact_without_space(replace) != _compact_without_space(find):
            raise ValueError("compact Force replacement is a boolean-neutral no-op")


def _reject_removed_live_binding(source: str, absolute_start: int, find: str, replace: str) -> None:
    declared = set(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\b", find))
    retained = set(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\b", replace))
    removed = declared - retained
    if not removed:
        return
    tail = source[absolute_start + len(find): absolute_start + len(find) + 1400]
    for name in sorted(removed):
        use = re.search(rf"\b{re.escape(name)}\b", tail)
        if not use:
            continue
        redeclare = re.search(rf"\b(?:const|let|var)\s+{re.escape(name)}\b", tail)
        if redeclare is None or use.start() < redeclare.start():
            raise ValueError(
                f"compact Force replacement removes live binding still referenced nearby: {name}"
            )


def _reject_causally_empty_deletion(failure_class: str, find: str, replace: str) -> None:
    failure = str(failure_class or "").strip().casefold().replace("-", "_")
    if failure not in {
        "route_proven_gap",
        "chain_terminal_gap",
        "media_extraction_gap",
        "provider_transport_gap",
    }:
        return
    compact_find = _compact_without_space(find)
    compact_replace = _compact_without_space(replace)
    if not compact_replace or compact_replace == compact_find:
        return
    if compact_replace in compact_find and len(compact_replace) < len(compact_find):
        raise ValueError(
            "compact Force traversal repair may not be a pure deletion of existing logic"
        )
    # A selected network/helper body that already performs the request and
    # returns its response cannot be replaced by a side-effect-only fragment.
    # Doing so silently turns the helper into an undefined-return path even
    # when the new fragment mentions causally relevant headers/referers.
    if (
        ("fetch(" in compact_find or "await_fetch(" in compact_find)
        and "return" in compact_find
        and "return" not in compact_replace
        and "throw" not in compact_replace
    ):
        raise ValueError(
            "compact Force network repair may not discard request return semantics"
        )


def _node_check_javascript(source: str) -> None:
    node = shutil.which("node")
    if not node:
        raise ValueError("node is required for compact Force JavaScript syntax validation")
    with tempfile.TemporaryDirectory(prefix="niakvio-force-js-") as tmp:
        path = Path(tmp) / "candidate.js"
        path.write_text(source, encoding="utf-8")
        proc = subprocess.run(
            [node, "--check", str(path)],
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "node --check failed").strip().replace("\n", " ")
        raise ValueError("compact Force JavaScript syntax validation failed: " + detail[:500])


def _validate_compact_updated_source(scope: str, updated: str) -> None:
    if scope == "provider_js":
        _node_check_javascript(updated)
        return
    if scope != "provider_patch":
        return
    try:
        tree = ast.parse(updated)
    except SyntaxError as exc:
        raise ValueError(f"compact Force provider Bloc Python syntax validation failed: {exc.msg}") from exc
    wrappers: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = getattr(node, "value", None)
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        targets = list(getattr(node, "targets", []) or [])
        target = getattr(node, "target", None)
        if target is not None:
            targets.append(target)
        if any(isinstance(item, ast.Name) and item.id in {"WRAPPER", "JS", "RUNTIME"} for item in targets):
            wrappers.append(value.value)
    for wrapper in wrappers:
        _node_check_javascript(wrapper)


def _minimize_local_edit(find: str, replace: str) -> tuple[str, str, int]:
    """Trim unchanged context while preserving the exact replacement semantics."""
    if not find:
        return find, replace, 0
    prefix = 0
    limit = min(len(find), len(replace))
    while prefix < limit and find[prefix] == replace[prefix]:
        prefix += 1
    find_tail = find[prefix:]
    replace_tail = replace[prefix:]
    suffix = 0
    suffix_limit = min(len(find_tail), len(replace_tail))
    while (
        suffix < suffix_limit
        and find_tail[len(find_tail) - suffix - 1]
        == replace_tail[len(replace_tail) - suffix - 1]
    ):
        suffix += 1
    if suffix:
        minimized_find = find_tail[:-suffix]
        minimized_replace = replace_tail[:-suffix]
    else:
        minimized_find = find_tail
        minimized_replace = replace_tail
    # Pure insertion cannot be represented by exact find/replace. Keep the
    # original bounded edit rather than inventing an insertion anchor.
    if not minimized_find:
        return find, replace, 0
    return minimized_find, minimized_replace, prefix


def _resolve_structured_anchor(
    source: str,
    failure_class: str,
    window_id: str,
    find: str,
    replace: str,
    *,
    max_find: int,
    max_replace: int,
    window_kwargs: dict[str, int] | None = None,
    absolute_start_hint: int | None = None,
    allow_new_helpers: bool = False,
) -> tuple[str, str]:
    """Compile a window-local semantic edit into one globally unique anchor.

    The model is not responsible for textual uniqueness inside the chosen
    causal window. If the same exact snippet appears several times there, Brain
    deterministically selects the occurrence closest to the window's causal
    focus. A tie remains ambiguous and fails closed.
    """
    if not source:
        raise ValueError("compact Force exact source is unavailable")
    if not find:
        raise ValueError("compact Force find snippet is missing")

    absolute_start: int
    if absolute_start_hint is not None:
        absolute_start = int(absolute_start_hint)
        if absolute_start < 0 or source[absolute_start:absolute_start + len(find)] != find:
            raise ValueError("compact Force edit unit drifted from current exact bytes")
    elif window_id:
        windows = _force_source_windows(source, failure_class, **(window_kwargs or {}))
        window = next(
            (row for row in windows if str(row.get("id") or "") == window_id),
            None,
        )
        if window is None:
            raise ValueError("compact Force window_id is not valid for current source")
        def _occurrences(row: dict) -> list[int]:
            window_source = str(row.get("source") or "")
            found: list[int] = []
            cursor = 0
            while True:
                local = window_source.find(find, cursor)
                if local < 0:
                    break
                found.append(local)
                cursor = local + max(1, len(find))
            return found

        def _focus_rank(row: dict, position: int) -> tuple[int, int, int]:
            window_source = str(row.get("source") or "")
            focus = int(row.get("focus_offset") or (len(window_source) // 2))
            end = position + len(find)
            if position <= focus < end:
                relation = 0
                distance = 0
            elif position >= focus:
                relation = 1
                distance = position - focus
            else:
                relation = 2
                distance = focus - end
            absolute = int(row.get("offset") or 0) + position
            return relation, max(0, distance), absolute

        occurrences = _occurrences(window)
        selected_window = window
        if not occurrences:
            # Qwen may identify the right exact bytes but attach the wrong window id.
            # Brain owns structural targeting, so relocate that exact snippet across
            # the current causal windows instead of spending another model call.
            candidates: dict[int, tuple[tuple[int, int, int], dict, int]] = {}
            for candidate_window in windows:
                for local in _occurrences(candidate_window):
                    absolute = int(candidate_window.get("offset") or 0) + local
                    rank = _focus_rank(candidate_window, local)
                    previous = candidates.get(absolute)
                    if previous is None or rank < previous[0]:
                        candidates[absolute] = (rank, candidate_window, local)
            if not candidates:
                raise ValueError(
                    "compact Force find snippet does not occur in any current causal source window"
                )
            ranked_candidates = sorted(candidates.values(), key=lambda item: item[0])
            best_rank = ranked_candidates[0][0][:2]
            best = [item for item in ranked_candidates if item[0][:2] == best_rank]
            if len(best) != 1:
                raise ValueError(
                    "compact Force find snippet remains ambiguous across causal source windows"
                )
            _, selected_window, local_start = best[0]
        elif len(occurrences) == 1:
            local_start = occurrences[0]
        else:
            ranked = sorted((_focus_rank(window, position), position) for position in occurrences)
            best_rank = ranked[0][0][:2]
            best = [
                position
                for rank, position in ranked
                if rank[:2] == best_rank
            ]
            if len(best) != 1:
                raise ValueError(
                    "compact Force selected source window remains ambiguous after causal-focus resolution"
                )
            local_start = best[0]
        absolute_start = int(selected_window.get("offset") or 0) + local_start
        if source[absolute_start:absolute_start + len(find)] != find:
            raise ValueError("compact Force causal source window drifted from current bytes")
    else:
        # Backward-compatible internal/test path. Real compact-wire schemas
        # require window_id; without it only a globally unique snippet is safe.
        if source.count(find) != 1:
            raise ValueError("compact Force find snippet must occur exactly once in exact source")
        absolute_start = source.index(find)

    _reject_semantic_identity_edit(find, replace)
    # Preserve declaration identity before minimization can strip common
    # "function _" prefixes or closing braces. Otherwise a full-function edit
    # such as _routeKind -> _extractUrls can collapse to routeKind -> extractUrls
    # and bypass the helper-removal guard below.
    _reject_partial_function_anchor(
        find,
        replace,
        allow_new_helpers=allow_new_helpers,
    )
    must_minimize = source.count(find) != 1 or bool(_function_names(find))
    if must_minimize:
        minimized_find, minimized_replace, prefix = _minimize_local_edit(find, replace)
    else:
        minimized_find, minimized_replace, prefix = find, replace, 0
    target_start = absolute_start + prefix
    target_end = target_start + len(minimized_find)

    anchor_find = minimized_find
    anchor_replace = minimized_replace
    _reject_semantic_identity_edit(anchor_find, anchor_replace)

    # If minimization made the local change globally ambiguous, deterministically
    # restore exact unchanged bytes around the selected occurrence. The LLM does
    # not have to solve repository-global or window-local textual uniqueness.
    while source.count(anchor_find) != 1:
        if len(anchor_find) >= max_find:
            raise ValueError(
                "compact Force selected window occurrence cannot be resolved to a globally unique anchor"
            )
        remaining = max_find - len(anchor_find)
        step = min(12, max(1, remaining // 2))
        left = min(step, target_start)
        right = min(step, len(source) - target_end)
        if left <= 0 and right <= 0:
            raise ValueError(
                "compact Force selected window occurrence cannot be resolved to a globally unique anchor"
            )
        new_start = target_start - left
        new_end = target_end + right
        prefix_text = source[new_start:target_start]
        suffix_text = source[target_end:new_end]
        anchor_find = prefix_text + anchor_find + suffix_text
        anchor_replace = prefix_text + anchor_replace + suffix_text
        target_start = new_start
        target_end = new_end
        if len(anchor_replace) > max_replace:
            raise ValueError("compact Force resolved replacement exceeds bounded size")

    if len(anchor_find) > max_find or len(anchor_replace) > max_replace:
        raise ValueError("compact Force resolved find/replace is oversized")
    _reject_partial_function_anchor(
        anchor_find,
        anchor_replace,
        allow_new_helpers=allow_new_helpers,
    )
    _reject_removed_live_binding(source, absolute_start, find, replace)
    _reject_causally_empty_deletion(failure_class, find, replace)
    return anchor_find, anchor_replace


def _force_unit_for_edit(
    request: RepairRequest,
    source: str,
    unit_id: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    if not unit_id:
        raise ValueError("compact Force unit_id is missing")
    edit_kwargs = _force_window_kwargs_for_request(request)
    focus_keywords = _force_structural_focus_keywords(request)
    units = _force_edit_units(
        source,
        request.failure_class,
        focus_keywords=focus_keywords,
        **edit_kwargs,
    )
    window_kwargs = {
        key: value
        for key, value in edit_kwargs.items()
        if key in {"max_chars", "max_windows"}
    }
    unit = next(
        (row for row in units if str(row.get("id") or "") == unit_id),
        None,
    )
    if unit is None:
        raise ValueError("compact Force unit_id is not valid for current source")
    find = str(unit.get("source") or "")
    absolute = int(unit.get("offset") or 0)
    if not find or source[absolute:absolute + len(find)] != find:
        raise ValueError("compact Force edit unit drifted from current exact bytes")
    return unit, window_kwargs


def _compact_edit_to_mutation(
    request: RepairRequest,
    edit: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(edit, dict):
        return None
    scope = str(edit.get("scope") or "")
    if scope == "provider_data":
        return dict(edit)

    if scope == "provider_bloc":
        family = str(edit.get("family") or "").strip().casefold()
        unit_id = str(edit.get("unit_id") or "").strip()
        window_id = str(edit.get("window_id") or "").strip()
        find = str(edit.get("find") or "")
        replace = str(edit.get("replace") or "")
        context = request.provider_context or {}
        source = str(
            context.get("preferredRuntimeMutationSource")
            or context.get("runtimeMutationSource")
            or ""
        )
        if not family or not replace or len(replace) > 1800:
            raise ValueError("compact Force provider_bloc edit is missing or oversized")
        if not source:
            raise ValueError("compact Force provider_bloc runtime source is unavailable")
        window_kwargs = {
            key: value
            for key, value in _force_window_kwargs_for_request(request).items()
            if key in {"max_chars", "max_windows"}
        }
        absolute_start_hint = None
        if unit_id:
            unit, window_kwargs = _force_unit_for_edit(request, source, unit_id)
            window_id = str(unit.get("window_id") or "")
            find = str(unit.get("source") or "")
            absolute_start_hint = int(unit.get("offset") or 0)
            if str(unit.get("kind") or "") == "function_unit":
                # Keep deletion/live-behavior guards meaningful on the raw model
                # body before adding the deterministic declaration envelope.
                _reject_causally_empty_deletion(request.failure_class, find, replace)
                replace = _preserve_selected_function_envelope(find, replace, normalize_explicit_wrapper=True)
        elif not find or len(find) > 320:
            raise ValueError("compact Force provider_bloc exact edit target is missing or oversized")
        # A provider_bloc selected through a complete function_unit may need
        # the full bounded function bytes to remain a unique exact anchor. The
        # free-form/backward-compatible path stays capped at 320 above.
        bloc_max_find = 1800 if unit_id else 320
        find, replace = _resolve_structured_anchor(
            source,
            request.failure_class,
            window_id,
            find,
            replace,
            max_find=bloc_max_find,
            max_replace=1800,
            window_kwargs=window_kwargs,
            absolute_start_hint=absolute_start_hint,
            allow_new_helpers=True,
        )
        added_helpers = _function_names(replace) - _function_names(find)
        existing_helpers = _function_names(source)
        collisions = sorted(added_helpers & existing_helpers)
        if collisions:
            raise ValueError(
                "compact Force provider_bloc helper name collides with current runtime: "
                + ",".join(collisions)
            )
        updated = source.replace(find, replace, 1)
        _node_check_javascript(updated)
        return {
            "scope": "provider_bloc",
            "operation": "upsert",
            "family": family,
            "find": find,
            "replace": replace,
        }

    if scope not in {"provider_patch", "provider_js"}:
        raise ValueError("compact Force edit has unsupported scope")
    path = str(edit.get("path") or "")
    unit_id = str(edit.get("unit_id") or "").strip()
    window_id = str(edit.get("window_id") or "").strip()
    find = str(edit.get("find") or "")
    replace = str(edit.get("replace") or "")
    if len(replace) > 1800:
        raise ValueError("compact Force replacement is oversized")
    context = request.provider_context or {}
    if scope == "provider_patch":
        sources = context.get("registered_patch_sources")
        if not isinstance(sources, dict) or path not in sources:
            raise ValueError("compact Force edit does not target a registered provider Bloc")
        source = str(sources[path])
    else:
        expected = f"engine_v2/providers/{request.provider_id}.mjs"
        if path != expected:
            raise ValueError("compact Force provider_js edit targets the wrong provider")
        source = str(context.get("authored_module") or "")

    if not source:
        raise ValueError("compact Force exact source is unavailable")
    window_kwargs = {
        key: value
        for key, value in _force_window_kwargs_for_request(request).items()
        if key in {"max_chars", "max_windows"}
    }
    absolute_start_hint = None
    max_find = 320
    max_replace = 640
    if unit_id:
        unit, window_kwargs = _force_unit_for_edit(request, source, unit_id)
        window_id = str(unit.get("window_id") or "")
        find = str(unit.get("source") or "")
        absolute_start_hint = int(unit.get("offset") or 0)
        if str(unit.get("kind") or "") == "function_unit":
            # function_unit has the same deterministic contract for authored
            # provider_patch/provider_js surfaces as for generated Bloc: the
            # model may return the new body only, while Brain preserves the
            # exact selected declaration. Keep the full bounded function
            # available as an anchor when a structural rewrite changes most of
            # its body instead of forcing every edit back under 320 bytes.
            _reject_causally_empty_deletion(request.failure_class, find, replace)
            replace = _preserve_selected_function_envelope(find, replace)
            max_find = 1800
            max_replace = 1800
    elif not find or len(find) > 320:
        raise ValueError("compact Force exact edit target is missing or oversized")
    if len(replace) > max_replace:
        raise ValueError("compact Force replacement is oversized for selected edit unit")

    stripped_find = find.strip()
    stripped_replace = replace.strip()
    if (
        stripped_replace
        and len(stripped_find) >= 48
        and len(stripped_replace) * 2 < len(stripped_find)
        and stripped_replace in stripped_find
    ):
        raise ValueError("compact Force replacement looks like a truncated source fragment")

    find, replace = _resolve_structured_anchor(
        source,
        request.failure_class,
        window_id,
        find,
        replace,
        max_find=max_find,
        max_replace=max_replace,
        window_kwargs=window_kwargs,
        absolute_start_hint=absolute_start_hint,
    )

    updated = source.replace(find, replace, 1)
    _validate_compact_updated_source(scope, updated)
    diff = "".join(
        difflib.unified_diff(
            source.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
            n=3,
        )
    )
    if not diff:
        raise ValueError("compact Force edit produced no diff")
    return {
        "scope": scope,
        "operation": "unified_diff",
        "path": path,
        "diff": diff,
    }


def _deterministic_exact_function_mutation(
    request: RepairRequest,
    *,
    path: str,
    source: str,
    unit: dict[str, Any],
    replacement_body: str,
) -> dict[str, Any]:
    """Compile one Brain-owned exact function unit without re-running prompt selection.

    Deterministic progression already resolved this unit from exact current bytes.
    Re-selecting it through the compact LLM prompt budget can hide the next helper
    and turn a valid internal progression into a false unit_id drift. This helper
    accepts no model-controlled path/unit lookup: callers must provide the exact
    registered source, unit offset and current function bytes.
    """
    if str(unit.get("kind") or "") != "function_unit":
        raise ValueError("deterministic Force exact unit is not a function")
    find = str(unit.get("source") or "")
    raw_offset = unit.get("offset")
    offset = int(raw_offset) if raw_offset is not None else -1
    if not path or not find or offset < 0:
        raise ValueError("deterministic Force exact unit metadata is incomplete")
    if len(find) > 1800 or len(str(replacement_body or "")) > 1800:
        raise ValueError("deterministic Force exact function is oversized")
    if source[offset:offset + len(find)] != find:
        raise ValueError("deterministic Force exact unit drifted from current bytes")
    if source.count(find) != 1:
        raise ValueError("deterministic Force exact function anchor is not unique")

    _reject_causally_empty_deletion(request.failure_class, find, replacement_body)
    replace = _preserve_selected_function_envelope(find, replacement_body)
    _reject_removed_live_binding(source, offset, find, replace)

    updated = source[:offset] + replace + source[offset + len(find):]
    _validate_compact_updated_source("provider_patch", updated)
    diff = "".join(
        difflib.unified_diff(
            source.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
            n=3,
        )
    )
    if not diff:
        raise ValueError("deterministic Force exact function produced no diff")
    return {
        "scope": "provider_patch",
        "operation": "unified_diff",
        "path": path,
        "diff": diff,
    }


def _deterministic_exact_bloc_function_mutation(
    request: RepairRequest,
    *,
    source: str,
    unit: dict[str, Any],
    replacement_body: str,
    family: str,
) -> dict[str, Any]:
    """Compile one exact current-runtime function into a provider_bloc mutation."""
    if str(unit.get("kind") or "") != "function_unit":
        raise ValueError("deterministic Force exact Bloc unit is not a function")
    find = str(unit.get("source") or "")
    raw_offset = unit.get("offset")
    offset = int(raw_offset) if raw_offset is not None else -1
    family = str(family or "").strip().casefold().replace("-", "_")
    if not family or not find or offset < 0:
        raise ValueError("deterministic Force exact Bloc metadata is incomplete")
    if len(find) > 1800 or len(str(replacement_body or "")) > 1800:
        raise ValueError("deterministic Force exact Bloc function is oversized")
    if source[offset:offset + len(find)] != find:
        raise ValueError("deterministic Force exact Bloc unit drifted from current bytes")
    if source.count(find) != 1:
        raise ValueError("deterministic Force exact Bloc function anchor is not unique")

    _reject_causally_empty_deletion(request.failure_class, find, replacement_body)
    replace = _preserve_selected_function_envelope(
        find,
        replacement_body,
        normalize_explicit_wrapper=True,
    )
    _reject_removed_live_binding(source, offset, find, replace)
    anchor_find, anchor_replace = _resolve_structured_anchor(
        source,
        request.failure_class,
        "",
        find,
        replace,
        max_find=1800,
        max_replace=1800,
        absolute_start_hint=offset,
        allow_new_helpers=True,
    )
    updated = source.replace(anchor_find, anchor_replace, 1)
    _node_check_javascript(updated)
    return {
        "scope": "provider_bloc",
        "operation": "upsert",
        "family": family,
        "find": anchor_find,
        "replace": anchor_replace,
    }


def _mixed_nested_class_container_evidence(
    request: RepairRequest,
    focus_keywords: tuple[str, ...],
) -> bool:
    """Return true only for bounded current evidence of nested mixed-tag class containers."""
    focused = {str(value or "").casefold() for value in focus_keywords if str(value or "")}
    for observation in request.observations or []:
        if (
            not isinstance(observation, dict)
            or str(observation.get("source") or "") not in {"targeted-regression-current", "census-sharded-current"}
        ):
            continue
        value = observation.get("value") if isinstance(observation.get("value"), dict) else {}
        for hint in (value.get("structureHints") or [])[:8]:
            text = str(hint or "")
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
                token = str(fields.get("token") or "").casefold()
                try:
                    count = int(fields.get("count") or 0)
                    self_href = int(fields.get("selfHref") or 0)
                    nested_anchors = int(fields.get("nestedAnchors") or 0)
                except ValueError:
                    continue
                tags = {
                    item.strip().casefold()
                    for item in str(fields.get("tags") or "").split(",")
                    if item.strip()
                }
                if (
                    token in focused
                    and count >= 2
                    and nested_anchors > 0
                    and len(tags) >= 2
                    and self_href < count
                ):
                    return True
    return False


def _force_stable_fingerprint(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _force_memory_blocks_mutation(
    request: RepairRequest,
    mutation: dict[str, Any],
) -> bool:
    """Reject an exact already-executed negative mutation on this provider.

    provider_patch remains byte-context-sensitive because the mutation targets an
    authored generator file directly. provider_bloc mutations already carry the
    exact current-byte find/replace payload in their mutation fingerprint; if
    that identical Bloc edit was executed and rejected, a Core/release/version
    drift must not make Brain publish it again unchanged.
    """
    scope = str(mutation.get("scope") or "")
    if scope not in {"provider_patch", "provider_bloc"}:
        return False

    mutation_fp = _force_stable_fingerprint([mutation])
    context_fp = ""
    if scope == "provider_patch":
        path = str(mutation.get("path") or "")
        context = request.provider_context or {}
        digests = context.get("registered_patch_sha256")
        if not path or not isinstance(digests, dict):
            return False
        digest = str(digests.get(path) or "").strip().casefold()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            return False
        context_fp = _force_stable_fingerprint([
            {"scope": "provider_patch", "path": path, "sha256": digest}
        ])

    for observation in request.observations or []:
        if not isinstance(observation, dict):
            continue
        source = str(observation.get("source") or "")
        if source not in {"brain-force-sandbox-memory", "brain-force-portfolio-reservation"}:
            continue
        rows = observation.get("value")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("mutationFingerprint") or "").strip().casefold() != mutation_fp:
                continue
            if source == "brain-force-portfolio-reservation":
                # Same-run portfolio candidates are not failures; they are only
                # reserved so later hypotheses must be causally distinct.
                return True
            if int(row.get("consecutiveFailures") or 0) <= 0:
                continue
            if scope == "provider_bloc":
                return True
            if str(row.get("mutationContextFingerprint") or "").strip().casefold() == context_fp:
                return True
    return False


def _deterministic_complete_line_function_units(source: str) -> list[dict[str, Any]]:
    """Extract compact named JavaScript helpers from exact current source.

    Published provider bundles can collapse an entire runtime onto one physical
    line, so a line-based greedy matcher can accidentally treat every following
    helper as part of the first function. Use the next *named* function
    declaration as the structural boundary instead. Anonymous callbacks do not
    terminate the unit. The resulting candidate is still syntax-validated by
    the deterministic mutation compiler before it can leave Brain.
    """
    text = str(source or "")
    declaration = re.compile(
        r"(?m)(?:^|[\s;])((?:async\s+)?function\s+"
        r"[A-Za-z_$][A-Za-z0-9_$]*\s*\([^\r\n]*?\)\s*\{)"
    )
    starts = [match.start(1) for match in declaration.finditer(text)]
    units: list[dict[str, Any]] = []
    for index, offset in enumerate(starts, start=1):
        boundary = starts[index] if index < len(starts) else len(text)
        chunk = text[offset:boundary].rstrip()
        # Top-level compact helpers end at their own closing brace. Reject
        # chunks with unrelated trailing statements rather than guessing.
        close = chunk.rfind("}")
        if close < 0:
            continue
        find = chunk[: close + 1].strip()
        trailing = chunk[close + 1 :].strip(" ;\t\r\n")
        if trailing or not find or len(find) > 1800:
            continue
        leading = len(text[offset:boundary]) - len(text[offset:boundary].lstrip())
        exact_offset = offset + leading
        if text[exact_offset: exact_offset + len(find)] != find:
            continue
        units.append({
            "id": f"detline{index}",
            "kind": "function_unit",
            "source": find,
            "offset": exact_offset,
            "end_offset": exact_offset + len(find),
            "window_id": "deterministic-full-source",
        })
    return units


def _deterministic_class_text_boundary_mutation(
    request: RepairRequest,
    mutation_policy: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the next exact class-selector repair after a failed container fix.

    The progression is surface-neutral: exact-runtime-first requests may expose
    only provider_bloc, while older/generator-owned cases may expose
    provider_patch. The same current-byte helper is compiled on whichever
    provider-local surface the scoped FORCE request actually owns.
    """
    focus_keywords = _force_structural_focus_keywords(request)
    if not focus_keywords:
        return None
    allowed = {
        str(scope)
        for scope in mutation_policy.get("allowed_scopes") or request.allowed_mutations or []
    }
    if not ({"provider_patch", "provider_bloc"} & allowed):
        return None
    context = request.provider_context or {}

    source_rows: list[tuple[str, str, str]] = []
    sources = context.get("registered_patch_sources")
    if "provider_patch" in allowed and isinstance(sources, dict):
        source_rows.extend(
            ("provider_patch", str(path), str(source_raw or ""))
            for path, source_raw in sources.items()
            if str(path) and str(source_raw or "")
        )
    if "provider_bloc" in allowed:
        runtime_source = str(
            context.get("preferredRuntimeMutationSource")
            or context.get("runtimeMutationSource")
            or ""
        )
        if runtime_source:
            source_rows.append(("provider_bloc", "", runtime_source))

    candidates: list[tuple[str, str, str, dict[str, Any], str]] = []
    for scope, path, source in source_rows:
        # This is a deterministic local scan, not model prompt context. The
        # compact route-gap prompt intentionally exposes only two causal units,
        # but negative-memory progression must still inspect the next exact
        # provider-owned helper after the first mechanism failed.
        window_units = _force_edit_units(
            source,
            request.failure_class,
            max_chars=5000,
            max_windows=4,
            max_units=32,
            focus_keywords=focus_keywords,
        )
        units = _deterministic_complete_line_function_units(source)
        seen_units = {
            (int(unit.get("offset") or -1), str(unit.get("source") or ""))
            for unit in units
        }
        for unit in window_units:
            key = (int(unit.get("offset") or -1), str(unit.get("source") or ""))
            if key not in seen_units:
                units.append(unit)
                seen_units.add(key)

        for unit in units:
            if str(unit.get("kind") or "") != "function_unit":
                continue
            unit_source = str(unit.get("source") or "")
            signature = re.match(
                r"(?s)^\s*(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*"
                r"\s*\((?P<params>[^)]*)\)\s*\{(?P<body>.*)\}\s*$",
                unit_source,
            )
            if not signature:
                continue
            params = [
                value.strip()
                for value in str(signature.group("params") or "").split(",")
                if value.strip()
            ]
            if len(params) < 2:
                continue
            class_param = params[1]
            if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", class_param):
                continue
            body = str(signature.group("body") or "")
            compact_body = re.sub(r"\s+", "", body)
            if (
                "starts=[]" in compact_body
                or "starts[i+1].at" in compact_body
                or "out.push({html:" in compact_body
            ):
                continue
            marker = class_param + ".replace("
            marker_at = body.find(marker)
            if marker_at < 0 or "class=" not in body:
                continue
            boundary = ')+"\\\\b'
            boundary_at = body.find(boundary, marker_at)
            if boundary_at < 0:
                continue
            replacement_body = (
                body[:boundary_at]
                + ')+"(?![-_])\\\\b'
                + body[boundary_at + len(boundary):]
            )
            candidates.append((scope, path, source, unit, replacement_body))

    if len(candidates) > 1:
        # The authored generator and exact materialized runtime can expose the
        # same helper. Collapse byte-identical semantic candidates and keep the
        # durable provider_patch surface when both are available.
        groups: dict[tuple[str, str], list[tuple[str, str, str, dict[str, Any], str]]] = {}
        for candidate in candidates:
            key = (str(candidate[3].get("source") or ""), candidate[4])
            groups.setdefault(key, []).append(candidate)
        if len(groups) == 1:
            same = next(iter(groups.values()))
            candidates = [
                next(
                    (candidate for candidate in same if candidate[0] == "provider_patch"),
                    same[0],
                )
            ]

    if len(candidates) != 1:
        return None
    scope, path, source, unit, replacement_body = candidates[0]
    if scope == "provider_patch":
        return _deterministic_exact_function_mutation(
            request,
            path=path,
            source=source,
            unit=unit,
            replacement_body=replacement_body,
        )
    return _deterministic_exact_bloc_function_mutation(
        request,
        source=source,
        unit=unit,
        replacement_body=replacement_body,
        family="class_text_boundary",
    )

def _deterministic_class_attribute_tokens_mutation(
    request: RepairRequest,
    mutation_policy: dict[str, Any],
) -> dict[str, Any] | None:
    """Replace regex class-prefix matching with exact class-attribute tokens.

    This progression is current-byte-derived and provider-independent. It only
    activates for the already-proven mixed/nested class-container family, keeps
    the existing tag family and slice cap from the selected helper, and requires
    an existing local attr() helper instead of inventing a DOM/network contract.
    """
    focus_keywords = _force_structural_focus_keywords(request)
    if not focus_keywords or not _mixed_nested_class_container_evidence(request, focus_keywords):
        return None
    allowed = {
        str(scope)
        for scope in mutation_policy.get("allowed_scopes") or request.allowed_mutations or []
    }
    if not ({"provider_patch", "provider_bloc"} & allowed):
        return None
    context = request.provider_context or {}
    source_rows: list[tuple[str, str, str]] = []
    sources = context.get("registered_patch_sources")
    if "provider_patch" in allowed and isinstance(sources, dict):
        source_rows.extend(
            ("provider_patch", str(path), str(source_raw or ""))
            for path, source_raw in sources.items()
            if str(path) and str(source_raw or "")
        )
    if "provider_bloc" in allowed:
        runtime_source = str(
            context.get("preferredRuntimeMutationSource")
            or context.get("runtimeMutationSource")
            or ""
        )
        if runtime_source:
            source_rows.append(("provider_bloc", "", runtime_source))

    candidates: list[tuple[str, str, str, dict[str, Any], str]] = []
    for scope, path, source in source_rows:
        units = _deterministic_complete_line_function_units(source)
        has_attr_helper = any(
            re.match(
                r"^\s*(?:async\s+)?function\s+attr\s*\(",
                str(unit.get("source") or ""),
            )
            for unit in units
            if str(unit.get("kind") or "") == "function_unit"
        )
        if not has_attr_helper:
            continue
        window_units = _force_edit_units(
            source,
            request.failure_class,
            max_chars=5000,
            max_windows=4,
            max_units=32,
            focus_keywords=focus_keywords,
        )
        seen = {
            (int(unit.get("offset") if unit.get("offset") is not None else -1), str(unit.get("source") or ""))
            for unit in units
        }
        for unit in window_units:
            key = (
                int(unit.get("offset") if unit.get("offset") is not None else -1),
                str(unit.get("source") or ""),
            )
            if key not in seen:
                units.append(unit)
                seen.add(key)

        for unit in units:
            if str(unit.get("kind") or "") != "function_unit":
                continue
            unit_source = str(unit.get("source") or "")
            signature = re.match(
                r"(?s)^\s*(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*"
                r"\s*\((?P<params>[^)]*)\)\s*\{(?P<body>.*)\}\s*$",
                unit_source,
            )
            if not signature:
                continue
            params = [
                value.strip()
                for value in str(signature.group("params") or "").split(",")
                if value.strip()
            ]
            if len(params) != 2 or not all(
                re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", value)
                for value in params
            ):
                continue
            html_param, class_param = params
            body = str(signature.group("body") or "")
            compact = re.sub(r"\s+", "", body)
            if (
                "starts=[]" not in compact
                or "starts[i+1].at" not in compact
                or "out.push({html:" not in compact
                or class_param + ".replace(" not in body
            ):
                continue
            tags_match = re.search(r"<\(\?:([A-Za-z0-9|]+)\)\\\\b", body)
            cap_match = re.search(r"starts\[i\]\.at\+(\d{2,6})", compact)
            if not tags_match or not cap_match:
                continue
            tags = tags_match.group(1)
            if not re.fullmatch(r"[A-Za-z0-9]+(?:\|[A-Za-z0-9]+){0,12}", tags):
                continue
            cap = max(256, min(int(cap_match.group(1)), 50000))
            replacement_body = (
                f'var re=/<(?:{tags})\\b[^>]*>/gi,starts=[],m;'
                f'while((m=re.exec({html_param}||""))!==null){{'
                'var names=attr(m[0],"class").split(/\\s+/).filter(Boolean);'
                f'if(names.indexOf({class_param})>=0)starts.push({{at:m.index,tag:m[0]}})}}'
                'var out=[];for(var i=0;i<starts.length;i++){'
                'var end=i+1<starts.length?starts[i+1].at:'
                f'Math.min(String({html_param}||"").length,starts[i].at+{cap});'
                f'out.push({{html:String({html_param}||"").slice(starts[i].at,end),tag:starts[i].tag}})}}'
                'return out'
            )
            candidates.append((scope, path, source, unit, replacement_body))

    if len(candidates) > 1:
        groups: dict[tuple[str, str], list[tuple[str, str, str, dict[str, Any], str]]] = {}
        for candidate in candidates:
            key = (str(candidate[3].get("source") or ""), candidate[4])
            groups.setdefault(key, []).append(candidate)
        if len(groups) == 1:
            same = next(iter(groups.values()))
            candidates = [
                next(
                    (candidate for candidate in same if candidate[0] == "provider_patch"),
                    same[0],
                )
            ]
    if len(candidates) != 1:
        return None

    scope, path, source, unit, replacement_body = candidates[0]
    if scope == "provider_patch":
        return _deterministic_exact_function_mutation(
            request,
            path=path,
            source=source,
            unit=unit,
            replacement_body=replacement_body,
        )
    return _deterministic_exact_bloc_function_mutation(
        request,
        source=source,
        unit=unit,
        replacement_body=replacement_body,
        family="exact_class_attribute_tokens",
    )



def _deterministic_optional_format_gate_mutation(
    request: RepairRequest,
    mutation_policy: dict[str, Any],
) -> dict[str, Any] | None:
    """Make a search-result media-format guard fail-open only when metadata is absent.

    Some catalogue pages retain the result card/title/href structure while the
    optional format label is absent or no longer extractable. A hard format
    guard then drops every otherwise valid identity candidate before any detail
    request is attempted. This repair is network-neutral: it preserves the
    existing movie/series check whenever a format value exists and changes no
    routes, hosts, identity threshold or terminal-media logic.
    """
    focus_keywords = _force_structural_focus_keywords(request)
    if not focus_keywords:
        return None
    allowed = {
        str(scope)
        for scope in mutation_policy.get("allowed_scopes") or request.allowed_mutations or []
    }
    if not ({"provider_patch", "provider_bloc"} & allowed):
        return None
    context = request.provider_context or {}
    source_rows: list[tuple[str, str, str]] = []
    sources = context.get("registered_patch_sources")
    if "provider_patch" in allowed and isinstance(sources, dict):
        source_rows.extend(
            ("provider_patch", str(path), str(source_raw or ""))
            for path, source_raw in sources.items()
            if str(path) and str(source_raw or "")
        )
    if "provider_bloc" in allowed:
        runtime_source = str(
            context.get("preferredRuntimeMutationSource")
            or context.get("runtimeMutationSource")
            or ""
        )
        if runtime_source:
            source_rows.append(("provider_bloc", "", runtime_source))

    tv_guard = re.compile(
        r'if\((?P<media>[A-Za-z_$][A-Za-z0-9_$]*)\.type==='
        r'(?P<quote>["\'])tv(?P=quote)&&!/series/i\.test\('
        r'(?P<format>[A-Za-z_$][A-Za-z0-9_$]*)\)\)continue;'
    )
    movie_guard = re.compile(
        r'if\((?P<media>[A-Za-z_$][A-Za-z0-9_$]*)\.type==='
        r'(?P<quote>["\'])movie(?P=quote)&&!/movies\?/i\.test\('
        r'(?P<format>[A-Za-z_$][A-Za-z0-9_$]*)\)\)continue;'
    )
    candidates: list[tuple[str, str, str, dict[str, Any], str]] = []
    for scope, path, source in source_rows:
        units = _deterministic_complete_line_function_units(source)
        for unit in units:
            if str(unit.get("kind") or "") != "function_unit":
                continue
            unit_source = str(unit.get("source") or "")
            signature = re.match(
                r"(?s)^\s*(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*"
                r"\s*\([^)]*\)\s*\{(?P<body>.*)\}\s*$",
                unit_source,
            )
            if not signature:
                continue
            body = str(signature.group("body") or "")
            if not all(token in body for token in ("classBlocks(", "classText(", "anchors(", "scoreTitle(")):
                continue
            tv = tv_guard.search(body)
            movie = movie_guard.search(body)
            if not tv or not movie:
                continue
            if tv.group("media") != movie.group("media") or tv.group("format") != movie.group("format"):
                continue
            format_var = tv.group("format")
            if not re.search(rf"\b{re.escape(format_var)}\s*=\s*classText\(", body):
                continue
            replacement_body = body
            replacement_body = replacement_body.replace(
                tv.group(0),
                tv.group(0).replace("&&!", f"&&{format_var}&&!", 1),
                1,
            )
            replacement_body = replacement_body.replace(
                movie.group(0),
                movie.group(0).replace("&&!", f"&&{format_var}&&!", 1),
                1,
            )
            if replacement_body == body:
                continue
            candidates.append((scope, path, source, unit, replacement_body))

    if len(candidates) > 1:
        groups: dict[tuple[str, str], list[tuple[str, str, str, dict[str, Any], str]]] = {}
        for candidate in candidates:
            key = (str(candidate[3].get("source") or ""), candidate[4])
            groups.setdefault(key, []).append(candidate)
        if len(groups) == 1:
            same = next(iter(groups.values()))
            candidates = [
                next(
                    (candidate for candidate in same if candidate[0] == "provider_patch"),
                    same[0],
                )
            ]
    if len(candidates) != 1:
        return None

    scope, path, source, unit, replacement_body = candidates[0]
    if scope == "provider_patch":
        return _deterministic_exact_function_mutation(
            request,
            path=path,
            source=source,
            unit=unit,
            replacement_body=replacement_body,
        )
    return _deterministic_exact_bloc_function_mutation(
        request,
        source=source,
        unit=unit,
        replacement_body=replacement_body,
        family="optional_metadata_format_gate",
    )


def _deterministic_catalog_identity_query_variants_mutation(
    request: RepairRequest,
    mutation_policy: dict[str, Any],
) -> dict[str, Any] | None:
    """Retry a bounded catalogue lookup with canonical + original-title variants.

    Route-proven HTML scrapers can fail before the detail request even when the
    catalogue is live: the provider may index an original/English title while
    TMDB supplies a localized title, or a series search may reject a synthetic
    "Season N" suffix. This compiler preserves all downstream identity gates and
    terminal extraction. It only broadens the *search queries* and scores cards
    against both the canonical and original TMDB titles, with a hard six-query
    cap and the existing year/season checks.
    """
    focus_keywords = _force_structural_focus_keywords(request)
    if not focus_keywords:
        return None
    allowed = {
        str(scope)
        for scope in mutation_policy.get("allowed_scopes") or request.allowed_mutations or []
    }
    if not ({"provider_patch", "provider_bloc"} & allowed):
        return None
    context = request.provider_context or {}
    source_rows: list[tuple[str, str, str]] = []
    sources = context.get("registered_patch_sources")
    if "provider_patch" in allowed and isinstance(sources, dict):
        source_rows.extend(
            ("provider_patch", str(path), str(source_raw or ""))
            for path, source_raw in sources.items()
            if str(path) and str(source_raw or "")
        )
    if "provider_bloc" in allowed:
        runtime_source = str(
            context.get("preferredRuntimeMutationSource")
            or context.get("runtimeMutationSource")
            or ""
        )
        if runtime_source:
            source_rows.append(("provider_bloc", "", runtime_source))

    candidates: list[tuple[str, str, str, dict[str, Any], str]] = []
    for scope, path, source in source_rows:
        if not (
            ("async function meta(" in source or "function meta(" in source)
            and "function scoreTitle(" in source
            and "function classBlocks(" in source
            and "function classText(" in source
        ):
            continue
        for unit in _deterministic_complete_line_function_units(source):
            if str(unit.get("kind") or "") != "function_unit":
                continue
            unit_source = str(unit.get("source") or "")
            signature = re.match(
                r"(?s)^\s*(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*"
                r"\s*\((?P<params>[^)]*)\)\s*\{(?P<body>.*)\}\s*$",
                unit_source,
            )
            if not signature:
                continue
            params = [
                value.strip()
                for value in str(signature.group("params") or "").split(",")
                if value.strip()
            ]
            if len(params) != 2 or not all(
                re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", value)
                for value in params
            ):
                continue
            q, meta_view = params
            body = str(signature.group("body") or "")
            required = (
                "var query=",
                "encodeURIComponent(query)",
                'classBlocks(sr.text,"movie-card")',
                'classText(card.html,"movie-card-title")',
                'classText(card.html,"movie-card-format")',
                "scoreTitle(" + meta_view + ".title,title)",
                "return await fetchText(best.url,sr.url)",
            )
            if not all(token in body for token in required):
                continue
            if "queries.length&&qi<6" in body or "original_title||raw.title" in body:
                continue
            replacement_body = (
                'var b=base();if(!b||!' + meta_view + '.title)return null;'
                'var raw=null,alt="";try{raw=await meta(' + q + ');'
                'alt=s(raw&&(' + q + '.type==="tv"?(raw.original_name||raw.name):'
                '(raw.original_title||raw.title)))}catch(_){}'
                'var names=[' + meta_view + '.title];'
                'if(alt&&norm(alt)!==norm(' + meta_view + '.title))names.push(alt);'
                'var queries=[];for(var ni=0;ni<names.length;ni++){var n=names[ni];'
                'if(' + q + '.type==="tv"){queries.push(n+" Season "+' + q + '.season);'
                'if(' + meta_view + '.year)queries.push(n+" "+' + meta_view + '.year);queries.push(n)}'
                'else{if(' + meta_view + '.year)queries.push(n+" "+' + meta_view + '.year);queries.push(n)}}'
                'var seenQ={},best=null,bestRef="";'
                'for(var qi=0;qi<queries.length&&qi<6;qi++){var query=queries[qi];'
                'if(seenQ[query])continue;seenQ[query]=1;'
                'var sr=await fetchText(b+"/?s="+encodeURIComponent(query),b+"/");if(!sr)continue;'
                'var cards=classBlocks(sr.text,"movie-card");for(var i=0;i<cards.length;i++){'
                'var card=cards[i],title=classText(card.html,"movie-card-title")||visible(card.html),'
                'format=classText(card.html,"movie-card-format"),metaText=classText(card.html,"movie-card-meta"),'
                'href=attr(card.tag,"href"),aa=anchors(card.html,sr.url);'
                'if(!href&&aa.length)href=aa[0].url;href=abs(href,sr.url);if(!href)continue;'
                'if(' + q + '.type==="tv"&&!/series/i.test(format))continue;'
                'if(' + q + '.type==="movie"&&!/movies?/i.test(format))continue;'
                'var sc=Math.max(scoreTitle(' + meta_view + '.title,title),alt?scoreTitle(alt,title):0),'
                'ym=metaText.match(/\\b(19|20)\\d{2}\\b/),y=ym?Number(ym[0]):0,w=Number(' + meta_view + '.year)||0;'
                'if(w&&y){if(y===w)sc+=0.35;else if(Math.abs(y-w)>1)sc-=0.5}'
                'if(' + q + '.type==="tv"){var sm=title.match(/(?:season\\s*|s)(\\d+)/i);'
                'if(sm&&Number(sm[1])===' + q + '.season)sc+=0.4;else if(sm)sc-=0.6}'
                'if(!best||sc>best.score){best={url:href,score:sc,title:title};bestRef=sr.url}}'
                'if(best&&best.score>=0.7)break}'
                'if(!best||best.score<0.7)return null;return await fetchText(best.url,bestRef)'
            )
            if len(replacement_body) > 1800:
                continue
            candidates.append((scope, path, source, unit, replacement_body))

    if len(candidates) > 1:
        groups: dict[tuple[str, str], list[tuple[str, str, str, dict[str, Any], str]]] = {}
        for candidate in candidates:
            key = (str(candidate[3].get("source") or ""), candidate[4])
            groups.setdefault(key, []).append(candidate)
        if len(groups) == 1:
            same = next(iter(groups.values()))
            candidates = [
                next(
                    (candidate for candidate in same if candidate[0] == "provider_patch"),
                    same[0],
                )
            ]
    if len(candidates) != 1:
        return None

    scope, path, source, unit, replacement_body = candidates[0]
    if scope == "provider_patch":
        return _deterministic_exact_function_mutation(
            request,
            path=path,
            source=source,
            unit=unit,
            replacement_body=replacement_body,
        )
    return _deterministic_exact_bloc_function_mutation(
        request,
        source=source,
        unit=unit,
        replacement_body=replacement_body,
        family="catalog_identity_query_variants",
    )


def _deterministic_variant_coverage_mutation(
    request: RepairRequest,
    mutation_policy: dict[str, Any],
) -> dict[str, Any] | None:
    """Defer a premature global stream quota until bounded variant enumeration completes.

    This compiler is deliberately fail-closed. It activates only for current
    high-risk variant-coverage evidence and only when the quota break sits inside
    a loop that already has its own explicit numeric iteration bound. Removing
    the quota break therefore cannot make traversal unbounded.
    """
    failure = str(request.failure_class or "").strip().casefold().replace("-", "_")
    if failure not in {"variant_coverage_gap", "variant_coverage_truncation"}:
        return None
    context = request.provider_context if isinstance(request.provider_context, dict) else {}
    coverage = context.get("runtime_variant_coverage")
    if not isinstance(coverage, dict) or coverage.get("risk") != "high":
        return None
    if coverage.get("riskKind") != "variant-coverage-truncation":
        return None

    allowed = {
        str(scope)
        for scope in mutation_policy.get("allowed_scopes") or request.allowed_mutations or []
    }
    source_rows: list[tuple[str, str, str]] = []
    if "provider_bloc" in allowed:
        runtime_source = str(
            context.get("preferredRuntimeMutationSource")
            or context.get("runtimeMutationSource")
            or ""
        )
        if runtime_source:
            source_rows.append(("provider_bloc", "", runtime_source))
    if "provider_patch" in allowed:
        sources = context.get("registered_patch_sources")
        if isinstance(sources, dict):
            source_rows.extend(
                ("provider_patch", str(path), str(source or ""))
                for path, source in sources.items()
                if str(path) and str(source or "")
            )
    if not source_rows:
        return None

    quota_break = re.compile(
        r"if\s*\(\s*out\.length\s*>=\s*(?:\d+|[A-Za-z_$][A-Za-z0-9_$.]*)\s*\)\s*break\s*;?",
        re.I,
    )
    bounded_loop = re.compile(
        r"for\s*\((?P<header>[^)]{1,280})\)\s*\{",
        re.I | re.S,
    )
    numeric_bound = re.compile(r"(?:^|[^A-Za-z0-9_$])\w+\s*<=?\s*\d+\b")

    candidates: list[tuple[str, str, str, dict[str, Any], str]] = []
    for scope, path, source in source_rows:
        for unit in _deterministic_complete_line_function_units(source):
            if str(unit.get("kind") or "") != "function_unit":
                continue
            unit_source = str(unit.get("source") or "")
            signature = re.match(
                r"(?s)^\s*(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*"
                r"\s*\([^)]*\)\s*\{(?P<body>.*)\}\s*$",
                unit_source,
            )
            if not signature:
                continue
            body = str(signature.group("body") or "")
            breaks = list(quota_break.finditer(body))
            if not breaks:
                continue
            for break_match in breaks:
                prior_loops = [
                    match
                    for match in bounded_loop.finditer(body[:break_match.start()])
                    if numeric_bound.search(str(match.group("header") or ""))
                ]
                if not prior_loops:
                    continue
                loop_match = prior_loops[-1]
                header = str(loop_match.group("header") or "")
                if ".length" not in header:
                    continue
                replacement_body = body[:break_match.start()] + body[break_match.end():]
                if replacement_body == body or header not in replacement_body:
                    continue
                candidates.append((scope, path, source, unit, replacement_body))
                break

    if not candidates:
        return None

    groups: dict[tuple[str, str], list[tuple[str, str, str, dict[str, Any], str]]] = {}
    for candidate in candidates:
        key = (str(candidate[3].get("source") or ""), candidate[4])
        groups.setdefault(key, []).append(candidate)
    if len(groups) == 1:
        same = next(iter(groups.values()))
        candidates = [
            next(
                (candidate for candidate in same if candidate[0] == "provider_bloc"),
                next(
                    (candidate for candidate in same if candidate[0] == "provider_patch"),
                    same[0],
                ),
            )
        ]
    else:
        bloc_candidates = [candidate for candidate in candidates if candidate[0] == "provider_bloc"]
        if len(bloc_candidates) == 1:
            candidates = bloc_candidates

    if len(candidates) != 1:
        return None

    scope, path, source, unit, replacement_body = candidates[0]
    if scope == "provider_patch":
        return _deterministic_exact_function_mutation(
            request,
            path=path,
            source=source,
            unit=unit,
            replacement_body=replacement_body,
        )
    return _deterministic_exact_bloc_function_mutation(
        request,
        source=source,
        unit=unit,
        replacement_body=replacement_body,
        family="bounded_variant_enumeration_before_cap",
    )


def _deterministic_structural_force_mutation(
    request: RepairRequest,
    mutation_policy: dict[str, Any],
) -> dict[str, Any] | None:
    """Synthesize one exact class-token boundary repair from current evidence.

    This is deliberately narrow. It activates only when current targeted
    structural evidence proves an exact class token also has token-child
    siblings, and only when the focused editable surface contains exactly one
    complete function using the known escaped-class boundary form. Network
    facts, routes and provider-specific literals are never invented.
    """
    focus_keywords = _force_structural_focus_keywords(request)
    if not focus_keywords:
        return None
    allowed = [
        str(scope)
        for scope in mutation_policy.get("allowed_scopes") or request.allowed_mutations or []
        if str(scope) in {"provider_patch", "provider_bloc"}
    ]
    if not allowed:
        return None

    context = request.provider_context or {}
    mixed_nested_class_container = _mixed_nested_class_container_evidence(
        request,
        focus_keywords,
    )
    candidates: list[tuple[str, str, str, dict[str, Any]]] = []
    edit_kwargs = _force_window_kwargs_for_request(request)
    for scope in allowed:
        if scope == "provider_patch":
            sources = context.get("registered_patch_sources")
            if not isinstance(sources, dict):
                continue
            source_rows = [
                (str(path), str(source or ""))
                for path, source in sources.items()
                if str(path) and str(source or "")
            ]
        else:
            source = str(
                context.get("preferredRuntimeMutationSource")
                or context.get("runtimeMutationSource")
                or ""
            )
            source_rows = [("", source)] if source else []

        for path, source in source_rows:
            units = _force_edit_units(
                source,
                request.failure_class,
                focus_keywords=focus_keywords,
                **edit_kwargs,
            )
            for unit in units:
                if str(unit.get("kind") or "") != "function_unit":
                    continue
                unit_source = str(unit.get("source") or "")
                old_boundary = '\\\\b"+esc+"\\\\b'
                if unit_source.count(old_boundary) != 1:
                    continue
                match = re.match(
                    r"(?s)^\s*(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*"
                    r"\s*\([^)]*\)\s*\{(?P<body>.*)\}\s*$",
                    unit_source,
                )
                if not match:
                    continue
                candidates.append((scope, path, source, unit))

    if mixed_nested_class_container and len(candidates) != 1:
        structural_candidates = [
            candidate
            for candidate in candidates
            if (
                "starts=[]" in str(candidate[3].get("source") or "")
                and "starts[i+1].at" in str(candidate[3].get("source") or "")
            )
        ]
        if len(structural_candidates) == 1:
            candidates = structural_candidates
        elif structural_candidates:
            # The same authored runtime helper can be visible twice: once in
            # its durable registered provider_patch source and once in the
            # materialized provider_bloc bytes. This is not semantic
            # ambiguity. Prefer the durable registered patch authority; keep
            # provider_bloc only as a fallback when no patch-owned match exists.
            patch_candidates = [
                candidate
                for candidate in structural_candidates
                if candidate[0] == "provider_patch"
            ]
            if len(patch_candidates) == 1:
                candidates = patch_candidates
            else:
                # Collapse byte-identical duplicates before failing closed.
                deduped: list[tuple[str, str, str, dict[str, Any]]] = []
                seen_units: set[str] = set()
                for candidate in structural_candidates:
                    unit_source = str(candidate[3].get("source") or "")
                    if unit_source in seen_units:
                        continue
                    seen_units.add(unit_source)
                    deduped.append(candidate)
                if len(deduped) == 1:
                    candidates = deduped

    if len(candidates) != 1:
        return None

    scope, path, _source, unit = candidates[0]
    unit_source = str(unit.get("source") or "")
    match = re.match(
        r"(?s)^\s*(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*"
        r"\s*\([^)]*\)\s*\{(?P<body>.*)\}\s*$",
        unit_source,
    )
    if not match:
        return None
    body = str(match.group("body") or "")
    old_boundary = '\\\\b"+esc+"\\\\b'
    new_boundary = '\\\\b"+esc+"(?![-_])\\\\b'
    if body.count(old_boundary) != 1:
        return None

    mechanism = "exact_class_token_boundary"
    replacement_body = body.replace(old_boundary, new_boundary, 1)
    if mixed_nested_class_container:
        signature = re.match(
            r"(?s)^\s*(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*"
            r"\s*\((?P<params>[^)]*)\)\s*\{.*\}\s*$",
            unit_source,
        )
        params = [
            value.strip()
            for value in str(signature.group("params") if signature else "").split(",")
            if value.strip()
        ]
        if (
            len(params) == 2
            and all(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", value) for value in params)
            and "starts=[]" in body
            and "starts[i+1].at" in body
        ):
            html_param, class_param = params
            replacement_body = (
                "var src=String(" + html_param + '||""),esc=String(' + class_param
                + r'||"").replace(/[-/\\^$*+?.()|[\]{}]/g,"\\$&"),'
                + r're=new RegExp("<(div|article|li|a)\\b[^>]*class=[\\x22\\x27][^\\x22\\x27]*\\b"+esc+"(?![-_])\\b[^\\x22\\x27]*[\\x22\\x27][^>]*>","gi"),out=[],m;'
                + r'while((m=re.exec(src))!==null){var name=String(m[1]||"").toLowerCase(),start=m.index,end=Math.min(src.length,re.lastIndex+12000),depth=1,closeRe=new RegExp("<\\/?"+name+"\\b[^>]*>","gi"),cm;closeRe.lastIndex=re.lastIndex;while(depth&&(cm=closeRe.exec(src))!==null){if(cm[0].slice(0,2)==="</")depth--;else if(cm[0].trim().slice(-2)!=="/>")depth++;if(!depth){end=closeRe.lastIndex;break}}out.push({html:src.slice(start,end),tag:m[0]});re.lastIndex=Math.max(re.lastIndex,end)}return out'
            )
            mechanism = "balanced_class_container"

    edit: dict[str, Any] = {
        "scope": scope,
        "unit_id": str(unit.get("id") or ""),
        "replace": replacement_body,
    }
    if scope == "provider_patch":
        edit["path"] = path
    else:
        edit["family"] = mechanism
    mutation = _compact_edit_to_mutation(request, edit)
    if not isinstance(mutation, dict):
        return None
    if _force_memory_blocks_mutation(request, mutation):
        print(
            "FIELD_BRAIN_FORCE_DETERMINISTIC_BLOCKED "
            f"provider={request.provider_id} scope={mutation.get('scope')} reason=executed-negative-memory",
            flush=True,
        )
        try:
            next_mutation = _deterministic_class_text_boundary_mutation(
                request,
                mutation_policy,
            )
        except ValueError as exc:
            detail = re.sub(r"\s+", " ", str(exc or "ValueError")).strip()[:280]
            print(
                "FIELD_BRAIN_FORCE_DETERMINISTIC_NEXT_ERROR "
                f"provider={request.provider_id} mechanism=class_text_boundary "
                f"error=ValueError detail={detail}",
                flush=True,
            )
            raise
        class_text_blocked = False
        if isinstance(next_mutation, dict):
            if _force_memory_blocks_mutation(request, next_mutation):
                class_text_blocked = True
                print(
                    "FIELD_BRAIN_FORCE_DETERMINISTIC_BLOCKED "
                    f"provider={request.provider_id} scope={next_mutation.get('scope')} "
                    "reason=executed-negative-memory mechanism=class_text_boundary",
                    flush=True,
                )
            else:
                return next_mutation
        else:
            print(
                "FIELD_BRAIN_FORCE_DETERMINISTIC_NEXT_MISSING "
                f"provider={request.provider_id} mechanism=class_text_boundary",
                flush=True,
            )

        try:
            token_mutation = _deterministic_class_attribute_tokens_mutation(
                request,
                mutation_policy,
            )
        except ValueError as exc:
            detail = re.sub(r"\s+", " ", str(exc or "ValueError")).strip()[:280]
            print(
                "FIELD_BRAIN_FORCE_DETERMINISTIC_NEXT_ERROR "
                f"provider={request.provider_id} mechanism=exact_class_attribute_tokens "
                f"error=ValueError detail={detail}",
                flush=True,
            )
            raise
        if isinstance(token_mutation, dict):
            if _force_memory_blocks_mutation(request, token_mutation):
                print(
                    "FIELD_BRAIN_FORCE_DETERMINISTIC_BLOCKED "
                    f"provider={request.provider_id} scope={token_mutation.get('scope')} "
                    "reason=executed-negative-memory mechanism=exact_class_attribute_tokens",
                    flush=True,
                )
            else:
                return token_mutation
        else:
            print(
                "FIELD_BRAIN_FORCE_DETERMINISTIC_NEXT_MISSING "
                f"provider={request.provider_id} mechanism=exact_class_attribute_tokens "
                f"after_class_text_blocked={str(class_text_blocked).lower()}",
                flush=True,
            )

        try:
            format_gate_mutation = _deterministic_optional_format_gate_mutation(
                request,
                mutation_policy,
            )
        except ValueError as exc:
            detail = re.sub(r"\s+", " ", str(exc or "ValueError")).strip()[:280]
            print(
                "FIELD_BRAIN_FORCE_DETERMINISTIC_NEXT_ERROR "
                f"provider={request.provider_id} mechanism=optional_metadata_format_gate "
                f"error=ValueError detail={detail}",
                flush=True,
            )
            raise
        if isinstance(format_gate_mutation, dict):
            if _force_memory_blocks_mutation(request, format_gate_mutation):
                print(
                    "FIELD_BRAIN_FORCE_DETERMINISTIC_BLOCKED "
                    f"provider={request.provider_id} scope={format_gate_mutation.get('scope')} "
                    "reason=executed-negative-memory mechanism=optional_metadata_format_gate",
                    flush=True,
                )
            else:
                return format_gate_mutation
        else:
            print(
                "FIELD_BRAIN_FORCE_DETERMINISTIC_NEXT_MISSING "
                f"provider={request.provider_id} mechanism=optional_metadata_format_gate",
                flush=True,
            )

        try:
            query_mutation = _deterministic_catalog_identity_query_variants_mutation(
                request,
                mutation_policy,
            )
        except ValueError as exc:
            detail = re.sub(r"\s+", " ", str(exc or "ValueError")).strip()[:280]
            print(
                "FIELD_BRAIN_FORCE_DETERMINISTIC_NEXT_ERROR "
                f"provider={request.provider_id} mechanism=catalog_identity_query_variants "
                f"error=ValueError detail={detail}",
                flush=True,
            )
            raise
        if isinstance(query_mutation, dict):
            if _force_memory_blocks_mutation(request, query_mutation):
                print(
                    "FIELD_BRAIN_FORCE_DETERMINISTIC_BLOCKED "
                    f"provider={request.provider_id} scope={query_mutation.get('scope')} "
                    "reason=executed-negative-memory mechanism=catalog_identity_query_variants",
                    flush=True,
                )
                return None
            return query_mutation
        print(
            "FIELD_BRAIN_FORCE_DETERMINISTIC_NEXT_MISSING "
            f"provider={request.provider_id} mechanism=catalog_identity_query_variants",
            flush=True,
        )
        return None
    return mutation


def _compact_wire_schema_for(
    request: RepairRequest,
    mutation_policy: dict[str, Any],
) -> dict[str, Any]:
    allowed = [
        str(scope)
        for scope in mutation_policy.get("allowed_scopes") or []
        if str(scope) in {"provider_data", "provider_patch", "provider_bloc", "provider_js"}
    ]
    context = request.provider_context or {}
    variants: list[dict[str, Any]] = []
    for scope in allowed:
        if scope == "provider_bloc":
            source = str(context.get("runtimeMutationSource") or "")
            units = _force_edit_units(
                source,
                request.failure_class,
                **_force_window_kwargs_for_request(request),
            )
            unit_ids = [str(row.get("id")) for row in units if str(row.get("id") or "")]
            if not unit_ids:
                continue
            variants.append({
                "type": "object",
                "additionalProperties": False,
                "required": ["scope", "family", "unit_id", "replace"],
                "properties": {
                    "scope": {"type": "string", "enum": ["provider_bloc"]},
                    "family": {"type": "string", "minLength": 3, "maxLength": 49, "pattern": "^[a-z][a-z0-9_]{2,48}$"},
                    "unit_id": {"type": "string", "enum": unit_ids},
                    "replace": {"type": "string", "maxLength": 1200},
                },
            })
            continue
        if scope in {"provider_patch", "provider_js"}:
            if scope == "provider_patch":
                sources = context.get("registered_patch_sources")
                paths = [str(path) for path in (sources or {}).keys()] if isinstance(sources, dict) else []
                path_schema: dict[str, Any] = {
                    "type": "string",
                    "enum": paths[:1],
                } if paths else {"type": "string", "maxLength": 240}
            else:
                path_schema = {
                    "type": "string",
                    "enum": [f"engine_v2/providers/{request.provider_id}.mjs"],
                }
            if scope == "provider_patch":
                source = str(next(iter((context.get("registered_patch_sources") or {}).values()), ""))
            else:
                source = str(context.get("authored_module") or "")
            units = _force_edit_units(
                source,
                request.failure_class,
                **_force_window_kwargs_for_request(request),
            )
            unit_ids = [str(row.get("id")) for row in units if str(row.get("id") or "")]
            if not unit_ids:
                continue
            variants.append({
                "type": "object",
                "additionalProperties": False,
                "required": ["scope", "path", "unit_id", "replace"],
                "properties": {
                    "scope": {"type": "string", "enum": [scope]},
                    "path": path_schema,
                    "unit_id": {"type": "string", "enum": unit_ids},
                    "replace": {"type": "string", "maxLength": 1800},
                },
            })
            continue
        variants.append({
            "type": "object",
            "additionalProperties": False,
            "required": ["scope", "operation", "path"],
            "properties": {
                "scope": {"type": "string", "enum": ["provider_data"]},
                "operation": {"type": "string", "enum": ["set", "delete", "append"]},
                "path": {"type": "string", "maxLength": 240},
                "value": {},
            },
        })
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["edit", "abstain_reason"],
        "properties": {
            "edit": {"anyOf": [*variants, {"type": "null"}]},
            "abstain_reason": {"type": "string", "maxLength": 180},
        },
    }


def _force_mutation_mechanism(mutation: dict[str, Any] | None) -> str:
    if not isinstance(mutation, dict):
        return ""
    family = str(mutation.get("family") or "").strip().casefold().replace("_", "-")
    if family:
        return family
    diff = str(mutation.get("diff") or "")
    if "closeRe=" in diff:
        return "balanced-class-container"
    if "function classText" in diff and "(?![-_])" in diff:
        return "exact-class-text-token-boundary"
    if "(?![-_])" in diff:
        return "exact-class-token-boundary"
    if "/series/i.test(" in diff and "/movies?/i.test(" in diff and "&&!" in diff:
        return "optional-metadata-format-gate"
    if "queries.length&&qi<6" in diff and "original_title||raw.title" in diff:
        return "catalog-identity-query-variants"
    if "out.length" in diff and "break" in diff:
        return "bounded-variant-enumeration-before-cap"
    return ""


class BrainPlanner:
    def __init__(
        self,
        backend: ModelBackend,
        store: ExperienceStore | None = None,
        documents: DocumentStore | None = None,
    ):
        self.backend = backend
        self.store = store or ExperienceStore([])
        self.documents = documents or DocumentStore([])

    def plan_deterministic_force(
        self,
        request: RepairRequest,
        *,
        expected_mechanism: str = "",
    ) -> RepairProposal | None:
        experiences = self.store.search(request.to_dict(), limit=6)
        causal_prior = build_causal_prior(request, experiences)
        mutation_policy = dict(build_mutation_policy(request, causal_prior))
        mutation = _deterministic_variant_coverage_mutation(request, mutation_policy)
        if not isinstance(mutation, dict):
            mutation = _deterministic_structural_force_mutation(request, mutation_policy)
        if not isinstance(mutation, dict):
            return None
        mechanism = _force_mutation_mechanism(mutation)
        expected = str(expected_mechanism or "").strip().casefold().replace("_", "-")
        if expected and mechanism != expected:
            return None
        print(
            "FIELD_BRAIN_FORCE_FAMILY_REPLAY "
            f"provider={request.provider_id} mechanism={mechanism or 'unknown'} "
            f"scope={mutation.get('scope')}",
            flush=True,
        )
        return RepairProposal(
            provider_id=request.provider_id,
            diagnosis="validated repair-family mechanism recompiled on exact current provider bytes",
            strategy=mechanism or str(causal_prior.get("strategy_prior") or "provider_local_repair"),
            confidence=max(0.0, min(1.0, float(causal_prior.get("confidence") or 0.0))),
            target_layer=str(causal_prior.get("target_layer") or "provider"),
            evidence=["sandbox-validated repair-family mechanism; current bytes recompiled independently"],
            mutations=[mutation],
            experiment={},
            tests=[],
            abstain=False,
            abstain_reason="",
        )

    def _prepare(
        self,
        request: RepairRequest,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any], str]:
        query = request.to_dict()
        experiences = self.store.search(query, limit=6)
        documents = self.documents.search(query, limit=4)
        causal_prior = build_causal_prior(request, experiences)
        mutation_policy = dict(build_mutation_policy(request, causal_prior))
        strategy = str(causal_prior.get("strategy_prior") or "")
        layer = str(causal_prior.get("target_layer") or "unknown")
        mutation_policy["required_tests"] = recommended_tests(
            strategy,
            target_layer=layer,
            mutation_policy=mutation_policy,
        )
        user = json.dumps(
            build_prompt_payload(
                request,
                experiences,
                documents,
                causal_prior,
                mutation_policy,
            ),
            ensure_ascii=True,
            allow_nan=False,
        )
        return experiences, documents, causal_prior, mutation_policy, user

    def _generate(
        self,
        request: RepairRequest,
        *,
        constrained: bool,
        compact_force: bool = False,
    ) -> tuple[RepairProposal, dict[str, Any], dict[str, Any]]:
        _, documents, causal_prior, mutation_policy, user = self._prepare(request)
        if compact_force:
            try:
                deterministic_mutation = _deterministic_variant_coverage_mutation(
                    request,
                    mutation_policy,
                )
                if deterministic_mutation is None:
                    deterministic_mutation = _deterministic_structural_force_mutation(
                        request,
                        mutation_policy,
                    )
            except ValueError as deterministic_exc:
                detail = re.sub(r"\\s+", " ", str(deterministic_exc or "ValueError")).strip()[:280]
                print(
                    "FIELD_BRAIN_FORCE_DETERMINISTIC_ERROR "
                    f"provider={request.provider_id} error=ValueError detail={detail}",
                    flush=True,
                )
                deterministic_mutation = None
            if deterministic_mutation is not None:
                print(
                    "FIELD_BRAIN_FORCE_DETERMINISTIC "
                    f"provider={request.provider_id} "
                    f"mechanism={deterministic_mutation.get('family') or ('balanced_class_container' if 'closeRe=' in str(deterministic_mutation.get('diff') or '') else ('exact_class_text_token_boundary' if 'function classText' in str(deterministic_mutation.get('diff') or '') else 'exact_class_token_boundary'))} "
                    f"scope={deterministic_mutation.get('scope')}",
                    flush=True,
                )
                deterministic_family = str(deterministic_mutation.get("family") or "").strip()
                coverage_candidate = deterministic_family == "bounded_variant_enumeration_before_cap"
                proposal = RepairProposal(
                    provider_id=request.provider_id,
                    diagnosis=(
                        "premature global output quota truncates bounded stream variant enumeration"
                        if coverage_candidate
                        else "structural class-token prefix collision"
                    ),
                    strategy=str(causal_prior.get("strategy_prior") or "provider_local_repair"),
                    confidence=max(0.0, min(1.0, float(causal_prior.get("confidence") or 0.0))),
                    target_layer=str(causal_prior.get("target_layer") or "provider"),
                    evidence=[
                        (
                            "current runtime has high variant-coverage debt and an independent bounded source loop"
                            if coverage_candidate
                            else "current structural evidence proves class-token prefix collision"
                        )
                    ],
                    mutations=[deterministic_mutation],
                    experiment={},
                    tests=[],
                    abstain=False,
                    abstain_reason="",
                )
                return proposal, causal_prior, mutation_policy
            user = json.dumps(
                build_force_prompt_payload(
                    request,
                    causal_prior,
                    mutation_policy,
                    documents,
                ),
                ensure_ascii=True,
                allow_nan=False,
            )
            # Keep the grammar small, but make it scope-specific. The scoped
            # Force cascade normally exposes exactly one mutation family, so
            # llama.cpp can enforce the fields that family actually needs
            # without paying for the complete production proposal schema.
            schema = _compact_wire_schema_for(request, mutation_policy)
        else:
            schema = (
                proposal_schema_for(
                    request.provider_id,
                    causal_prior,
                    mutation_policy,
                    request.provider_context,
                )
                if constrained
                else REPAIR_PROPOSAL_SCHEMA
            )
        started = time.monotonic()
        try:
            raw = self.backend.complete(
                system=COMPACT_FORCE_SYSTEM_PROMPT if compact_force else SYSTEM_PROMPT,
                user=user,
                response_schema=schema,
            )
        except Exception as exc:
            if compact_force:
                print(
                    "FIELD_BRAIN_FORCE_MODEL "
                    f"provider={request.provider_id} scopes={','.join(request.allowed_mutations)} chars={len(user)} "
                    f"system_chars={len(COMPACT_FORCE_SYSTEM_PROMPT)} total_chars={len(user) + len(COMPACT_FORCE_SYSTEM_PROMPT)} "
                    f"seconds={time.monotonic() - started:.2f} outcome=error "
                    f"error={type(exc).__name__} "
                    f"max_tokens={getattr(self.backend, 'max_tokens', 'unknown')}"
                )
            raise
        if compact_force:
            print(
                "FIELD_BRAIN_FORCE_MODEL "
                f"provider={request.provider_id} scopes={','.join(request.allowed_mutations)} chars={len(user)} "
                f"system_chars={len(COMPACT_FORCE_SYSTEM_PROMPT)} total_chars={len(user) + len(COMPACT_FORCE_SYSTEM_PROMPT)} "
                f"seconds={time.monotonic() - started:.2f} outcome=success "
                f"max_tokens={getattr(self.backend, 'max_tokens', 'unknown')}"
            )
        parsed = _extract_json(raw)
        if compact_force:
            mutation = _compact_edit_to_mutation(
                request,
                parsed.get("edit") if isinstance(parsed.get("edit"), dict) else None,
            )
            mutations = [mutation] if isinstance(mutation, dict) else []
            abstain = not mutations
            proposal = RepairProposal(
                provider_id=request.provider_id,
                diagnosis="bounded Force mutation synthesis",
                strategy=str(causal_prior.get("strategy_prior") or "provider_local_repair"),
                confidence=max(0.0, min(1.0, float(causal_prior.get("confidence") or 0.0))),
                target_layer=str(causal_prior.get("target_layer") or "unknown"),
                evidence=[],
                mutations=mutations,
                experiment={},
                tests=[],
                abstain=abstain,
                abstain_reason=str(parsed.get("abstain_reason") or ("no executable mutation" if abstain else "")),
            )
            return proposal, causal_prior, mutation_policy
        return RepairProposal.from_dict(parsed), causal_prior, mutation_policy

    def propose_raw(self, request: RepairRequest) -> RepairProposal:
        """Model-only proposal for benchmarks; skips production normalization."""
        proposal, _, _ = self._generate(request, constrained=False)
        return proposal

    def plan(
        self,
        request: RepairRequest,
        *,
        compact_force: bool = False,
    ) -> RepairProposal:
        proposal, causal_prior, mutation_policy = self._generate(
            request,
            constrained=True,
            compact_force=compact_force,
        )

        if proposal.provider_id and proposal.provider_id != request.provider_id:
            raise ValueError("model changed provider_id")
        proposal.provider_id = request.provider_id

        prior_confidence = float(causal_prior.get("confidence") or 0.0)
        prior_layer = str(causal_prior.get("target_layer") or "unknown")
        prior_strategy = str(causal_prior.get("strategy_prior") or "")

        if (
            prior_confidence >= 0.90
            and prior_layer != "unknown"
            and proposal.target_layer != prior_layer
        ):
            raise ValueError(
                f"model causal layer {proposal.target_layer} conflicts with high-confidence prior {prior_layer}"
            )
        if (
            prior_confidence >= 0.90
            and prior_strategy
            and proposal.strategy != prior_strategy
        ):
            raise ValueError(
                f"model strategy {proposal.strategy} conflicts with high-confidence prior {prior_strategy}"
            )

        allowed_scopes = set(mutation_policy.get("allowed_scopes") or [])
        if proposal.mutations and not mutation_policy.get("allow_mutations"):
            raise ValueError("model proposed mutation while evidence policy forbids mutation")
        if any(str(m.get("scope") or "") not in request.allowed_mutations for m in proposal.mutations):
            raise ValueError("model proposed mutation outside request scope")
        if allowed_scopes and any(
            str(m.get("scope") or "") not in allowed_scopes
            for m in proposal.mutations
        ):
            raise ValueError("model proposed mutation outside evidence-backed scope")

        if proposal.target_layer != "provider" and proposal.mutations:
            raise ValueError("non-provider diagnosis cannot mutate provider code/data")

        if proposal.target_layer == "provider":
            validate_mutations(
                request.provider_id,
                proposal.mutations,
                allowed_patch_paths=set(
                    str(value)
                    for value in (request.provider_context or {}).get("registered_patch_scripts") or []
                    if str(value).strip()
                ),
            )

        if mutation_policy.get("force_abstain") and not proposal.abstain:
            raise ValueError("model must abstain under current evidence policy")

        if proposal.target_layer != "provider" and not proposal.abstain:
            proposal.abstain = True
            proposal.abstain_reason = proposal.abstain_reason or (
                f"causal layer is {proposal.target_layer}; provider mutation withheld"
            )

        if mutation_policy.get("force_abstain") and not proposal.abstain_reason:
            proposal.abstain_reason = str(mutation_policy.get("reason") or "insufficient evidence")

        required_tests = [str(x) for x in mutation_policy.get("required_tests") or []]
        proposal.tests = list(dict.fromkeys(required_tests + proposal.tests))[:12]

        return proposal
