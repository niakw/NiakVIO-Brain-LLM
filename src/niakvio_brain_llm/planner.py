from __future__ import annotations

import ast
import difflib
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
from .prompting import _force_edit_units, _force_source_windows, _force_window_kwargs_for_request, build_force_prompt_payload, build_prompt_payload
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

COMPACT_FORCE_SYSTEM_PROMPT = """NiakVIO Brain Force. Return JSON only:
{"edit":<one provider-local edit or null>,"abstain_reason":"<short>"}
Rules:
- One edit max; never invent URLs/routes/hosts/headers/tokens/cookies/placeholders or facts.
- provider_data: {scope,operation,path,value?}
- provider_patch/provider_js: {scope,path,unit_id,replace}; no unified diff.
- provider_bloc is the invention fallback for a new provider-local mechanism: {scope:"provider_bloc",family,unit_id,replace}; family must be lowercase snake_case.
- unit_id must come from editable_units. Brain owns the exact current-byte find text; never copy or invent find bytes.
- Existing-file replace <=640 chars, or <=1800 only for a supplied function_unit; provider_bloc replace <=1800 chars.
- Preserve syntax/function boundaries; do not emit partial function declarations.
- When the chosen editable unit has kind=function_unit, replace is the NEW FUNCTION BODY ONLY. Never emit or rename the function declaration/name/signature; Brain preserves that exact envelope deterministically.
- FULL OK references are optional inspiration only: adapt/combine/ignore them or invent a new provider-local mechanism. Never copy provider-specific network facts.
- For provider_bloc, an editable unit does NOT need to already implement the missing mechanism. Prefer the nearest complete function_unit and rewrite it with a new bounded provider-local mechanism using only observed current facts.
- Do not abstain merely because existing code lacks the desired helper/strategy. Abstain only when current evidence lacks a required network fact/value or no complete syntax-safe unit can carry a provider-local repair.
- force_validation_feedback means the previous shape failed; choose a materially different unit/replacement in the same scope or abstain.\n- prior_force_sandbox_failures are executed negative evidence: if a prior edit applied but did not improve playable proof, do not make a cosmetic variant of that mechanism; choose a materially different causal mechanism/unit or abstain."""


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


def _preserve_selected_function_envelope(find: str, replace: str) -> str:
    """Keep the exact selected function declaration when Qwen returns only a body.

    function_unit gives Brain the exact current signature. The generative part is
    the replacement body/logic, not permission to silently delete or rename the
    selected helper. Wrong explicit function declarations still fail closed.
    """
    find_names = _function_names(find)
    if len(find_names) != 1:
        return replace
    original_name = next(iter(find_names))
    replace_names = _function_names(replace)
    if original_name in replace_names:
        declaration = re.compile(
            r"^\s*(?P<async>async\s+)?function\s+"
            r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*"
            r"\((?P<params>[^)]*)\)\s*\{",
            re.S,
        )
        find_decl = declaration.match(find)
        replace_decl = declaration.match(replace)
        if not find_decl or not replace_decl:
            raise ValueError("selected function declaration/signature could not be verified")
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
        if replace_identity != find_identity:
            raise ValueError("selected function declaration/signature changed")
        return replace
    stripped = str(replace or "").lstrip()
    if stripped.startswith("function ") or stripped.startswith("async function "):
        return replace
    match = re.match(
        r"(?s)^(\s*(?:async\s+)?function\s+[A-Za-z_$][A-Za-z0-9_$]*\s*\([^)]*\)\s*\{)(.*)(\}\s*)$",
        find,
    )
    if not match:
        return replace
    return match.group(1) + str(replace or "").strip() + match.group(3)


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
    units = _force_edit_units(
        source,
        request.failure_class,
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
        source = str((request.provider_context or {}).get("runtimeMutationSource") or "")
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
                replace = _preserve_selected_function_envelope(find, replace)
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
                    "replace": {"type": "string", "maxLength": 1800},
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
        _, _, causal_prior, mutation_policy, user = self._prepare(request)
        if compact_force:
            user = json.dumps(
                build_force_prompt_payload(
                    request,
                    causal_prior,
                    mutation_policy,
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
