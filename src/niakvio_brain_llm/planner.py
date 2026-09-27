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
from .prompting import build_force_prompt_payload, build_prompt_payload
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

COMPACT_FORCE_SYSTEM_PROMPT = """You are NiakVIO Brain LLM in bounded Force mutation mode.
Return exactly one compact JSON object with only:
{"edit": <one provider-local edit object or null>, "abstain_reason": "<short reason or empty>"}.
Do not repeat provider id, diagnosis, strategy, confidence, evidence, tests or experiment; deterministic NiakVIO owns them.
Emit at most one edit. Never invent URLs, routes, headers, tokens, cookies or placeholders.
For provider_data, edit is the normal {scope,operation,path,value?} mutation.
For provider_patch/provider_js, DO NOT emit a unified diff. Emit only:
{scope,path,find,replace}
where find is the smallest exact UNIQUE snippet wholly contained in one mutation_target.source_windows[].source and replace is its corrected text.
Never delete or truncate whole helper/function declarations to repair one expression or branch; preserve the enclosing function signature unless that signature itself is the proven defect.
For a genuinely new independent runtime mechanism, provider_bloc may emit only:
{scope:"provider_bloc",family:"<descriptive_snake_case_mechanism>",find,replace}
The family must describe the concrete mechanism (for example terminal_confirm_traversal), never copy the placeholder text from this prompt.
Use exact UNIQUE bytes wholly contained in one new_bloc_target.source_windows[].source. Each window is an exact current-byte slice; never join across windows. NiakVIO, not you, creates and versions the trusted Bloc file.
For file edits, find must be <= 320 characters. Existing-file replace must be <= 640 characters; provider_bloc replace must be <= 1200 characters.
Prefer changing one expression, branch, call, regex or small block.
If current_observations contains force_validation_feedback, the previous edit was rejected by deterministic validation. Do not repeat that rejected shape; produce a materially different exact edit in the same allowed scope or abstain.
If the correction cannot fit these bounds or the exact unique edit is not safely derivable, return edit:null.
Return JSON only."""

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


def _compact_without_space(value: str) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _reject_partial_function_anchor(find: str, replace: str) -> None:
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
    if added:
        raise ValueError("compact Force replacement may not absorb a neighboring helper function")
    if re.search(r"\basync\s+async\b|\bfunction\s+function\b|\breturn\s+return\b", replace):
        raise ValueError("compact Force replacement contains duplicated JavaScript control tokens")

    # Neutral boolean constants inside a control condition are a common LLM
    # pseudo-fix: they change bytes but not behavior.
    if re.search(r"\b(?:if|while)\s*\(", replace):
        neutral = re.sub(r"\|\|\s*(?:0|false)\b|&&\s*(?:1|true)\b", "", replace, flags=re.I)
        if _compact_without_space(neutral) == _compact_without_space(find) and _compact_without_space(replace) != _compact_without_space(find):
            raise ValueError("compact Force replacement is a boolean-neutral no-op")


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
        find = str(edit.get("find") or "")
        replace = str(edit.get("replace") or "")
        source = str((request.provider_context or {}).get("runtimeMutationSource") or "")
        if not family or not find or len(find) > 320 or not replace or len(replace) > 1200:
            raise ValueError("compact Force provider_bloc edit is missing or oversized")
        if not source:
            raise ValueError("compact Force provider_bloc runtime source is unavailable")
        if source.count(find) != 1:
            raise ValueError("compact Force provider_bloc find snippet must occur exactly once in current runtime source")
        if find == replace:
            raise ValueError("compact Force provider_bloc edit is a no-op")
        _reject_partial_function_anchor(find, replace)
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
    find = str(edit.get("find") or "")
    replace = str(edit.get("replace") or "")
    if not find or len(find) > 320 or len(replace) > 640:
        raise ValueError("compact Force find/replace is missing or oversized")
    stripped_find = find.strip()
    stripped_replace = replace.strip()
    if (
        stripped_replace
        and len(stripped_find) >= 48
        and len(stripped_replace) * 2 < len(stripped_find)
        and stripped_replace in stripped_find
    ):
        raise ValueError("compact Force replacement looks like a truncated source fragment")
    _reject_partial_function_anchor(find, replace)

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
    if source.count(find) != 1:
        raise ValueError("compact Force find snippet must occur exactly once in exact source")
    if find == replace:
        raise ValueError("compact Force edit is a no-op")

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
            variants.append({
                "type": "object",
                "additionalProperties": False,
                "required": ["scope", "family", "find", "replace"],
                "properties": {
                    "scope": {"type": "string", "enum": ["provider_bloc"]},
                    "family": {"type": "string", "maxLength": 49},
                    "find": {"type": "string", "maxLength": 320},
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
            variants.append({
                "type": "object",
                "additionalProperties": False,
                "required": ["scope", "path", "find", "replace"],
                "properties": {
                    "scope": {"type": "string", "enum": [scope]},
                    "path": path_schema,
                    "find": {"type": "string", "maxLength": 320},
                    "replace": {"type": "string", "maxLength": 640},
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
                    f"seconds={time.monotonic() - started:.2f} outcome=error "
                    f"error={type(exc).__name__} "
                    f"max_tokens={getattr(self.backend, 'max_tokens', 'unknown')}"
                )
            raise
        if compact_force:
            print(
                "FIELD_BRAIN_FORCE_MODEL "
                f"provider={request.provider_id} scopes={','.join(request.allowed_mutations)} chars={len(user)} "
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
