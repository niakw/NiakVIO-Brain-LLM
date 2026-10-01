from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
src=(ROOT/"scripts/plan_batch_from_checkout.py").read_text(encoding="utf-8")
wf=(ROOT/".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")
route=(ROOT/"scripts/route_batch_from_checkout.py").read_text(encoding="utf-8")

for token in (
    "ThreadPoolExecutor",
    "as_completed",
    "--workers",
    'thread_name_prefix="niakvio-llm"',
    'rows.sort(key=lambda row: (int(row["position"]), int(row.get("hypothesis_index") or 1)))',
    '"parallel_workers": workers',
    "--advisor-only",
    "--max-hypotheses",
    "_reserve_advisor_experiment",
    "plannedHypotheses",
    "--max-tokens",
    "--timeout-seconds",
    "LocalOpenAICompatibleBackend(",
    "validation_timeout = max(",
    "primary_timeout = max(",
    "transport_timeout = max(",
    "timeout_seconds=primary_timeout",
    "retry_tokens = max(",
    "scope_token_cap = {",
    '"provider_data": 192',
    '"provider_patch": 640',
    '"provider_js": 640',
    '"provider_bloc": 320',
    "recovery_token_cap = {",
    '"provider_patch": 768',
    '"provider_js": 768',
    '"provider_bloc": 256',
    "primary_tokens = max(128, min(int(args.max_tokens), scope_token_cap))",
    "retry_tokens = max(128, min(int(args.max_tokens), recovery_token_cap))",
    "FIELD_BRAIN_FORCE_PROVIDER_BUDGET ",
    '(90 if portfolio_reserved else 150) if scope == "provider_bloc" else 90',
    "90 if portfolio_reserved else 180",
    "FIELD_BRAIN_FORCE_CANDIDATE_BUDGET",
    "FIELD_BRAIN_FORCE_CANDIDATE_BUDGET_EXHAUSTED",
    "FIELD_BRAIN_FORCE_PORTFOLIO_FEEDBACK",
    'budget_seconds = min(budget_cap, 600)',
    "force_validation_feedback",
    "FIELD_BRAIN_FORCE_SCOPE_FEEDBACK",
    "window-local edit in the same scope or abstain",
    "force provider budget exhausted",
    "candidate budget exhausted",
):
    assert token in src, token

assert 'parser.add_argument("--advisor-only", action="store_true")' in route
assert "request.advisor_only = bool(args.advisor_only)" in route
assert "--mode brain \\" in wf
assert "--advisor-only \\" in wf
assert "--mode repair \\" in wf
assert '"${provider_args[@]}"' in wf
assert "force_llm_needed=" in wf
assert "--limit 4" not in wf
assert "requested_repair_queue" in wf
assert "niakvio-guidance-targets.txt" in wf
assert "FIELD_NIAKVIO_FORCE_MUTATIONS_READY ready=false" in wf

assert "-c 16384" in wf
assert "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M" in wf
assert "--model qwen2.5-coder-7b" in wf
assert "-np 1" in wf
assert "--workers 1" in wf
assert "--advisor-only" in wf
assert "--max-tokens 512" in wf
assert "--timeout-seconds 240" in wf
assert "--force-provider-budget-seconds 600" in wf
assert wf.index("-np 1") < wf.index("--workers 1")

print("bounded concurrent private-guidance batch contract passed")

assert "select_niakvio_guidance_page.py" in wf
assert "merge_niakvio_guidance_page.py" in wf
assert "niakvio-guidance-page.txt" in wf
assert "niakvio-guidance-state.json" in wf
assert "Continue remaining guidance page" in wf
assert "steps.page.outputs.complete" in wf
assert "actions: write" in wf
assert "mutationContextFingerprint" in wf
