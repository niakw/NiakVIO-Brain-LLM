from __future__ import annotations

import json
from typing import Any

from .backend import ModelBackend
from .contracts import RepairProposal, RepairRequest
from .document_memory import DocumentStore
from .mutation_guard import validate_mutations
from .policy import build_mutation_policy
from .priors import build_causal_prior
from .prompting import build_prompt_payload
from .retrieval import ExperienceStore
from .schema import REPAIR_PROPOSAL_SCHEMA, proposal_schema_for
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
Prefer the smallest causal change.\nFor provider-layer repairs, also propose an abstract experiment spec. It may only steer existing deterministic sandbox knobs: route_policy, recipe_policy, role_order, terminal_only, alias_search, response_salvage, document_request_mining, session_bootstrap, max_depth, max_pages, max_embeds, and max_recipe_passes. Never put URLs, routes, headers, tokens, cookies, source text, diffs, or private-memory text in experiment. Different specs are distinct hypotheses even inside the same strategy family.\n\nMutation DSL:
- provider_data paths are relative to provider-overrides.json > provider_patches[provider_id], never file paths.
- provider_js may target only engine_v2/providers/<provider_id>.mjs.
Never return shell commands or edits to unrelated files.
Return one JSON object only with provider_id, diagnosis, strategy, confidence, target_layer,
evidence, mutations, experiment, tests, abstain and abstain_reason.
"""

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
    ) -> tuple[RepairProposal, dict[str, Any], dict[str, Any]]:
        _, _, causal_prior, mutation_policy, user = self._prepare(request)
        schema = (
            proposal_schema_for(request.provider_id, causal_prior, mutation_policy)
            if constrained
            else REPAIR_PROPOSAL_SCHEMA
        )
        raw = self.backend.complete(
            system=SYSTEM_PROMPT,
            user=user,
            response_schema=schema,
        )
        return RepairProposal.from_dict(_extract_json(raw)), causal_prior, mutation_policy

    def propose_raw(self, request: RepairRequest) -> RepairProposal:
        """Model-only proposal for benchmarks; skips production normalization."""
        proposal, _, _ = self._generate(request, constrained=False)
        return proposal

    def plan(self, request: RepairRequest) -> RepairProposal:
        proposal, causal_prior, mutation_policy = self._generate(
            request,
            constrained=True,
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
            validate_mutations(request.provider_id, proposal.mutations)

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
