from __future__ import annotations

import difflib
import json
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
where find is the smallest exact UNIQUE snippet from mutation_target.source and replace is its corrected text.
For file edits, find must be <= 320 characters and replace <= 640 characters. Prefer changing one expression, branch, call, regex or small block.
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


def _compact_edit_to_mutation(
    request: RepairRequest,
    edit: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(edit, dict):
        return None
    scope = str(edit.get("scope") or "")
    if scope == "provider_data":
        return dict(edit)

    if scope not in {"provider_patch", "provider_js"}:
        raise ValueError("compact Force edit has unsupported scope")
    path = str(edit.get("path") or "")
    find = str(edit.get("find") or "")
    replace = str(edit.get("replace") or "")
    if not find or len(find) > 320 or len(replace) > 640:
        raise ValueError("compact Force find/replace is missing or oversized")

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
            # llama.cpp JSON-Schema grammar for the complete mutation DSL is
            # substantially more expensive than the 3B generation itself on a
            # GitHub CPU runner. Keep only a minimal JSON-object wire grammar;
            # the full compact schema and all mutation guards are enforced
            # locally by BrainPlanner immediately after parsing.
            schema = {
                "type": "object",
                "additionalProperties": False,
                "required": ["edit", "abstain_reason"],
                "properties": {
                    "edit": {
                        "anyOf": [
                            {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["scope", "path"],
                                "properties": {
                                    "scope": {
                                        "type": "string",
                                        "enum": ["provider_data", "provider_patch", "provider_js"],
                                    },
                                    "operation": {
                                        "type": "string",
                                        "enum": ["set", "delete", "append"],
                                    },
                                    "path": {"type": "string", "maxLength": 240},
                                    "value": {},
                                    "find": {"type": "string", "maxLength": 320},
                                    "replace": {"type": "string", "maxLength": 640},
                                },
                            },
                            {"type": "null"},
                        ]
                    },
                    "abstain_reason": {"type": "string", "maxLength": 180},
                },
            }
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
        raw = self.backend.complete(
            system=COMPACT_FORCE_SYSTEM_PROMPT if compact_force else SYSTEM_PROMPT,
            user=user,
            response_schema=schema,
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
