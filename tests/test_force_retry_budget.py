from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "scripts" / "plan_batch_from_checkout.py").read_text(encoding="utf-8")
workflow = (ROOT / ".github" / "workflows" / "niakvio-private-guidance.yml").read_text(encoding="utf-8")

assert "max(int(args.max_tokens), 768)" in source
assert "retry_tokens = max(" in source
assert "retry_timeout = max(" in source
assert "min(int(args.timeout_seconds) + 90, 240)" in source
assert "1280" not in source
assert "timeout_seconds=150" not in source
assert '"unterminated string" in str(exc).casefold()' in source
assert '"jsondecodeerror" in type(exc).__name__.casefold()' in source

assert "--max-tokens 512" in workflow
assert "--timeout-seconds 150" in workflow
assert "FIELD_NIAKVIO_FORCE_MUTATIONS_READY ready=false" in workflow
assert "raise SystemExit(f\"Force routing requested" not in workflow

print("compact Force retry budget and advisor-preservation contract passed")
