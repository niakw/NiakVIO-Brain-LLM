from __future__ import annotations

import json
from typing import Any

from .backend import ModelBackend
from .contracts import RepairProposal, RepairRequest
from .retrieval import ExperienceStore

SYSTEM_PROMPT = """You are NiakVIO Brain LLM, a bounded provider-repair planner.
NiakVIO tests are the only proof authority. Retrieved experience is hypothesis material, not proof.
Never mutate outside allowed_mutations or touch forbidden_mutations.
Prefer the smallest causal change. If evidence is insufficient, abstain.
Return one JSON object only with provider_id, diagnosis, strategy, confidence, evidence,
mutations, tests, abstain and abstain_reason.
"""

def _extract_json(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("~~~"):
        lines = value.splitlines()
        value = "\n".join(lines[1:-1]).strip()
        if value.startswith("json"):
            value = value[4:].lstrip()
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
        return proposal
