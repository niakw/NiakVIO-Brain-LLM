"""Exact-current unit IDs survive aggressive CPU-only FORCE prompt compaction."""
import json
import os
from unittest.mock import patch

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.prompting import build_force_prompt_payload
from niakvio_brain_llm.planner import _compact_wire_schema_for

runtime = (
    "function searchOneAt(term){return resolve(term);}\n"
    "function resolve(id){let hint='A';" + "".join(f"const item{i}=readSource(id);\n" for i in range(155)) +
    "return hint;}\n"
)
rows = [
    {
        "fixture": "Jujutsu Kaisen S01E01",
        "stage": ["search", "detail", "episode", "player", "source", "media"][i % 6],
        "status": 200,
        "address_scope": "s0123456789abcdef",
        "request_ref": "r" + str(i + 1),
        "response_ref": "r" + str(i + 11),
        "functions": ["resolve"],
        "response_structure": {
            "kind": "html",
            "player_markup": {
                "rows": [
                    {"tag": "iframe", "count": 3,
                     "value_kinds": {"data-src": "absolute_url"},
                     "address_refs": {"data-src": ["r15", "r16", "r17"]}}
                ] * 6
            },
        },
    } for i in range(8)
]
live = {
    "active_functions": ["resolve"],
    "network_evidence": rows,
    "fixture_evidence": [
        {"fixture": "Jujutsu Kaisen S01E01", "category": "anime",
         "status": "no_streams", "streamsReturned": 0, "streamsPlayable": 0}
    ],
    "previous_verification": {
        "reason": "no_playable_proof",
        "executionObserved": True, "materializedMutationObserved": True,
        "baseline": {"streamsReturned": 0, "streamsPlayable": 0},
        "candidate": {"streamsReturned": 0, "streamsPlayable": 0},
        "candidate_network": rows,
    },
}
request = RepairRequest(
    provider_id="demo", failure_class="chain_terminal_gap", status="CHAIN REACHED",
    allowed_mutations=["provider_bloc"],
    provider_context={
        "runtimeMutationSource": runtime,
        "runtimeMutationFilename": "providers/demo.js",
        "live_runtime_evidence": live,
    },
)
policy = {"allow_mutations": True, "allowed_scopes": ["provider_bloc"]}
with patch.dict(os.environ, {"NIAKVIO_FORCE_CPU_TIGHT_PROMPT": "1"}):
    compact = build_force_prompt_payload(request, {}, policy)
with patch.dict(os.environ, {"NIAKVIO_FORCE_CPU_TIGHT_PROMPT": "0"}):
    normal = build_force_prompt_payload(request, {}, policy)
size = lambda value: len(json.dumps(value, ensure_ascii=True, separators=(",", ":")))
assert size(compact) < size(normal), (size(compact), size(normal))
assert size(compact) <= 12000, size(compact)
units = compact["new_bloc_target"]["editable_units"]
assert units, "exact executable units lost"
assert units == normal["new_bloc_target"]["editable_units"], "mutation unit authority changed"
schema = _compact_wire_schema_for(request, policy)
variants = [row for row in schema["properties"]["edit"]["anyOf"]
            if row.get("properties", {}).get("scope", {}).get("enum") == ["provider_bloc"]]
assert len(variants) == 1
assert [u["id"] for u in units] == variants[0]["properties"]["unit_id"]["enum"]
assert any(row.get("stage") in {"media","player","source"} for row in compact["current_network_evidence"])
assert compact["mutation_policy"]["allow_mutations"] is True
assert compact["current_fixture_evidence"][0]["streamsReturned"] == 0
assert compact["previous_verification"]["executionObserved"] is True
print("CPU_FORCE_TIGHT_PROMPT_OK exact-unit-ids and bounded causal evidence")
