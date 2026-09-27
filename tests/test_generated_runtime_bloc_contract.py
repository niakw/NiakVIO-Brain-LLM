from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.mutation_guard import validate_mutation
from niakvio_brain_llm.planner import _compact_edit_to_mutation
from niakvio_brain_llm.prompting import build_force_prompt_payload
from niakvio_brain_llm.provider_context import build_provider_context

ROOT = Path(__file__).resolve().parents[1]
runtime_source = (
    "/* BEGIN NIAKVIO_PROVIDER */\n"
    "function resolve(){return oldResolver();}\n"
    "/* STARTFIX:CORE.RUNTIME_COMPAT.V1 */\n"
    "coreRuntime();\n"
    "/* CLOSEFIX:CORE.RUNTIME_COMPAT.V1 */\n"
    "/* END NIAKVIO_PROVIDER */"
)
request = RepairRequest(
    provider_id="demo",
    failure_class="chain_terminal_gap",
    provider_context={
        "runtimeMutationFilename": "providers/demo.js",
        "runtimeMutationSource": runtime_source,
    },
)
mutation = _compact_edit_to_mutation(
    request,
    {
        "scope": "provider_bloc",
        "family": "terminal_resolution",
        "window_id": "w1",
        "find": "return oldResolver();",
        "replace": "return resolveTerminalMedia();",
    },
)
assert mutation == {
    "scope": "provider_bloc",
    "operation": "upsert",
    "family": "terminal_resolution",
    "find": "return oldResolver();",
    "replace": "return resolveTerminalMedia();",
}
validate_mutation("demo", mutation)

for bad in (
    {**mutation, "family": "../escape"},
    {**mutation, "replace": "return eval(payload);"},
    {**mutation, "replace": "/* STARTFIX:FORGED */ return 1;"},
):
    try:
        validate_mutation("demo", bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"unsafe generated Bloc mutation accepted: {bad}")

duplicate = RepairRequest(
    provider_id="demo",
    failure_class="chain_terminal_gap",
    provider_context={"runtimeMutationSource": "return oldResolver(); return oldResolver();"},
)
duplicate_mutation = _compact_edit_to_mutation(
    duplicate,
    {
        "scope": "provider_bloc",
        "family": "terminal_resolution",
        "window_id": "w1",
        "find": "return oldResolver();",
        "replace": "return resolveTerminalMedia();",
    },
)
duplicate_updated = duplicate.provider_context["runtimeMutationSource"].replace(
    duplicate_mutation["find"],
    duplicate_mutation["replace"],
    1,
)
assert duplicate_updated == "return oldResolver(); return resolveTerminalMedia();", duplicate_updated

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "providers").mkdir()
    (root / "scripts/provider_patches").mkdir(parents=True)
    (root / "providers/demo.js").write_text(runtime_source, encoding="utf-8")
    (root / "scripts/provider_patches/existing_v1.py").write_text(
        "def apply(value):\n    return value\n", encoding="utf-8"
    )
    (root / "manifest.json").write_text(
        json.dumps({"scrapers": [{"id": "demo", "filename": "providers/demo.js"}]}), encoding="utf-8"
    )
    (root / "provider-overrides.json").write_text(
        json.dumps({"provider_patches": {"demo": {"patch_scripts": ["scripts/provider_patches/existing_v1.py"]}}}),
        encoding="utf-8",
    )
    (root / "provider-hubs.json").write_text("{}", encoding="utf-8")
    ctx = build_provider_context(root, "demo")
    assert ctx["registered_patch_scripts"] == ["scripts/provider_patches/existing_v1.py"], ctx
    assert ctx["runtimeMutationFilename"] == "providers/demo.js"
    assert "return oldResolver();" in ctx["runtimeMutationSource"]
    assert "CORE.RUNTIME_COMPAT" not in ctx["runtimeMutationSource"]

spec = importlib.util.spec_from_file_location(
    "publish_force", ROOT / "scripts" / "publish_niakvio_force_mutations.py"
)
publisher = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(publisher)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "providers").mkdir()
    (root / "automation").mkdir()
    (root / "providers/demo.js").write_text(runtime_source, encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps({"scrapers": [{"id": "demo", "filename": "providers/demo.js"}]}), encoding="utf-8"
    )
    (root / "provider-overrides.json").write_text(
        json.dumps({"provider_patches": {"demo": {"patch_scripts": []}}}), encoding="utf-8"
    )
    fp = publisher.mutation_context_fingerprint(root, "demo", [mutation])
    assert len(fp) == 64


budget_request = RepairRequest(
    provider_id="budget-demo",
    failure_class="provider_transport_gap",
    observations=[{"reason": "challenge response then zero streams"}],
    provider_context={
        "registered_patch_sources": {
            "scripts/provider_patches/existing_v1.py": "PATCH_HEAD\n" + ("p" * 18000) + "\nPATCH_TAIL",
        },
        "runtimeMutationFilename": "providers/budget-demo.js",
        "runtimeMutationSource": "RUNTIME_HEAD\n" + ("r" * 18000) + "\nRUNTIME_TAIL",
    },
)
budget_payload = build_force_prompt_payload(
    budget_request,
    {
        "strategy_prior": "provider_origin_failover_v1",
        "target_layer": "provider",
        "confidence": 0.95,
    },
    {
        "allow_mutations": True,
        "allowed_scopes": ["provider_patch", "provider_bloc"],
        "reason": "bounded Force test",
    },
)
encoded_budget = json.dumps(budget_payload, ensure_ascii=True, allow_nan=False)
assert len(encoded_budget) < 10000, len(encoded_budget)
patch_windows = budget_payload["mutation_target"]["source_windows"]
runtime_windows = budget_payload["new_bloc_target"]["source_windows"]
assert sum(len(row["source"]) for row in patch_windows) <= 4000
assert sum(len(row["source"]) for row in runtime_windows) <= 4000
assert "PATCH_HEAD" in "\n".join(row["source"] for row in patch_windows)
assert "PATCH_TAIL" in "\n".join(row["source"] for row in patch_windows)
assert "RUNTIME_HEAD" in "\n".join(row["source"] for row in runtime_windows)
assert "RUNTIME_TAIL" in "\n".join(row["source"] for row in runtime_windows)

print("generated runtime Bloc contract passed")
