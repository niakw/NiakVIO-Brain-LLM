from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "scripts" / "plan_batch_from_checkout.py").read_text(encoding="utf-8")
workflow = (ROOT / ".github" / "workflows" / "niakvio-private-guidance.yml").read_text(encoding="utf-8")

assert "scope_token_cap = {" in source
assert '"provider_data": 192' in source
assert '"provider_patch": 320' in source
assert '"provider_js": 320' in source
assert '"provider_bloc": 448' in source
assert "primary_tokens = max(128, min(int(args.max_tokens), scope_token_cap))" in source
assert "retry_tokens = max(" in source
assert "validation_timeout = max(" in source
assert "transport_timeout = max(" in source
assert "min(int(args.timeout_seconds), 90)" in source
assert "min(int(args.timeout_seconds) + 15, 120)" in source
assert "1280" not in source
assert "timeout_seconds=150" not in source
assert '"unterminated string" in str(exc).casefold()' in source
assert '"jsondecodeerror" in type(exc).__name__.casefold()' in source
assert '"function anchor is structurally incomplete", "truncated_fragment"' in source
assert "except ValueError as validation_exc:" in source
assert "timeout_seconds=validation_timeout" in source
assert "timeout_seconds=transport_timeout" in source
assert "max_validation_corrections = 1" in source
assert "for correction_index in range(1, max_validation_corrections + 1):" in source
assert "window-local edit in the same scope or abstain" in source
assert "force provider budget exhausted" in source
assert "FIELD_BRAIN_FORCE_PROVIDER_BUDGET_EXHAUSTED" in source
assert "--force-provider-budget-seconds" in source
assert "prefill_prompt=True" in source
assert 'prefill_prompt=(args.mode == "repair" and not args.advisor_only)' in source

assert "--max-tokens 512" in workflow
assert "--timeout-seconds 120" in workflow
assert "--force-provider-budget-seconds 180" in workflow
assert "FIELD_NIAKVIO_FORCE_MUTATIONS_READY ready=false" in workflow
assert "raise SystemExit(f\"Force routing requested" not in workflow

print("compact Force retry budget and advisor-preservation contract passed")
