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
# Reproduce a HTTP-200 GraphQL failure nested among successful HTML
# responses. Tight CPU prefill must preserve the class, not just status=200.
rows[2]["response_structure"] = {
    "kind": "json",
    "fields": [{"path": "data.episode", "type": "null"},
               {"path": "errors[].message", "type": "string"}],
    "graphql": {
        "errorCount": 1,
        "codes": ["GRAPHQL_VALIDATION_FAILED"],
        "kinds": ["schema_mismatch"],
        "dataState": "null",
        "nullRoots": [],
        "message": "PRIVATE_ERROR_PAYLOAD",
    },
}
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
causal = [
    row["response_structure"] for row in compact["current_network_evidence"]
    if isinstance(row.get("response_structure"), dict)
    and "graphql" in row["response_structure"]
]
assert causal, "tight CPU prompt discarded live GraphQL failure"
assert causal[0]["graphql"]["errorCount"] == 1
assert causal[0]["graphql"]["kinds"] == ["schema_mismatch"]
assert causal[0]["graphql"]["dataState"] == "null"
assert {"path": "data.episode", "type": "null"} in causal[0]["fields"]
assert "PRIVATE_ERROR_PAYLOAD" not in json.dumps(compact)
# Candidate verification feedback must retain the same causal category.
assert any(
    row.get("response_structure", {}).get("graphql", {}).get("errorCount") == 1
    for row in compact["previous_verification"]["candidate_network"]
)
assert compact["mutation_policy"]["allow_mutations"] is True
assert compact["current_fixture_evidence"][0]["streamsReturned"] == 0
assert compact["previous_verification"]["executionObserved"] is True
print("CPU_FORCE_TIGHT_PROMPT_OK exact-unit-ids and bounded causal evidence")

# An opt-in local CPU run must retain one sanitized, non-authoritative FULL
# peer pattern instead of throwing all successful reusable patterns away.
request.provider_context["validated_reference_patterns"] = [{
    "provider": "public-peer",
    "status": "FULL OK",
    "technical_features": ["player", "iframe"],
    "snippet": (
        "function inspectPlayer(html) { const hostname = "
        "'https://private.example.org/secret'; return html.match(/iframe/); }"
    ),
    "proof_authority": False,
    "copy_policy": "pattern_reference_only",
}]
with patch.dict(os.environ, {
    "NIAKVIO_FORCE_CPU_TIGHT_PROMPT": "1",
    "NIAKVIO_FORCE_CPU_PEER_PATTERN": "1",
}):
    with_reference = build_force_prompt_payload(request, {}, policy)
with patch.dict(os.environ, {
    "NIAKVIO_FORCE_CPU_TIGHT_PROMPT": "1",
    "NIAKVIO_FORCE_CPU_PEER_PATTERN": "0",
}):
    without_reference = build_force_prompt_payload(request, {}, policy)
references = with_reference["validated_reference_patterns"]
assert len(references) == 1
assert references[0]["proof_authority"] is False
assert references[0]["copy_policy"] == "pattern_reference_only"
assert references[0]["must_revalidate_current_provider"] is True
assert "<URL>" in references[0]["snippet"]
assert "private.example.org" not in str(references)
assert "public-peer" not in str(references)
assert without_reference["validated_reference_patterns"] == []
assert with_reference["new_bloc_target"]["editable_units"] == without_reference["new_bloc_target"]["editable_units"]
assert size(with_reference) <= 12000
print("CPU_FORCE_PEER_PATTERN_OK redacted prior, exact-unit-preserving, no-proof-authority")

