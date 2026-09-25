from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "scripts" / "plan_batch_from_checkout.py").read_text(encoding="utf-8")
workflow = (ROOT / ".github" / "workflows" / "niakvio-private-guidance.yml").read_text(encoding="utf-8")

assert "retry_budgets = (" in source
assert "max(int(args.max_tokens), 768)" in source
assert "1280" in source
assert "never salvage or auto-close malformed JSON" not in source  # comment wording may evolve
assert '"unterminated string" in str(retry_exc).casefold()' in source
assert '"jsondecodeerror" in type(retry_exc).__name__.casefold()' in source

assert "--max-tokens 768" in workflow
assert "--timeout-seconds 90" in workflow
assert "FIELD_NIAKVIO_FORCE_MUTATIONS_READY ready=false" in workflow
assert "raise SystemExit(f\"Force routing requested" not in workflow

print("compact Force retry budget and advisor-preservation contract passed")
