from __future__ import annotations

import json
from typing import Any

from .backend import ModelBackend
from .contracts import RepairProposal, RepairRequest
from .mutation_guard import validate_mutations
from .retrieval import ExperienceStore

SYSTEM_PROMPT = """You are NiakVIO Brain LLM, a bounded repair planner.
First classify the causal layer as exactly one of: provider, core, harness, network, unknown.
NiakVIO tests are the only proof authority. Retrieved experience is hypothesis material, not proof.
Never mutate outside allowed_mutations or touch forbidden_mutations.
If target_layer is not provider, do not propose provider mutations: abstain and request the right diagnostic/retest.
Prefer the smallest causal change. If evidence is insufficient, abstain.

Mutation DSL:
- provider_data: {\"scope\":\"provider_data\",\"operation\":\"set|delete|append\",\"path\":\"dot.path\",\"value\":...}
- provider_js: {\"scope\":\"provider_js\",\"operation\":\"unified_diff\",\"path\":\"engine_v2/providers/<provider_id>.mjs\",\"diff\":\"...\"}

Never return shell commands or edits to unrelated files.
Return one JSON object only with provider_id, diagnosis, strategy, confidence, target_layer,
evidence, mutations, tests, abstain and abstain_reason.
"""

def _extract_json(text: str) -> dict[str, Any]:
    value = text.strip()
    for fence in ("~~~", "```"):
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
    def __init__(self, backend: ModelBackend, store: ExperienceStore | None = None):
        self.backend = backend
        self.store = store or ExperienceStore([])

    def plan(self, request: RepairRequest) -> RepairProposal:
        request_data = request.to_dict()
        experiences = self.store.search(request_data, limit=6)
        user = json.dumps(
            {"request": request_data, "retrieved_experiences": experiences},
            ensure_ascii=True,
            allow_nan=False,
        )
        proposal = RepairProposal.from_dict(
            _extract_json(self.backend.complete(system=SYSTEM_PROMPT, user=user))
        )
        if proposal.provider_id and proposal.provider_id != request.provider_id:
            raise ValueError("model changed provider_id")
        proposal.provider_id = request.provider_id

        if any(str(m.get("scope") or "") not in request.allowed_mutations for m in proposal.mutations):
            raise ValueError("model proposed mutation outside allowed scope")

        if proposal.target_layer != "provider" and proposal.mutations:
            raise ValueError("non-provider diagnosis cannot mutate provider code/data")

        if proposal.target_layer == "provider":
            validate_mutations(request.provider_id, proposal.mutations)

        if proposal.target_layer != "provider" and not proposal.abstain:
            proposal.abstain = True
            proposal.abstain_reason = proposal.abstain_reason or (
                f"causal layer is {proposal.target_layer}; provider mutation withheld"
            )

        return proposal
