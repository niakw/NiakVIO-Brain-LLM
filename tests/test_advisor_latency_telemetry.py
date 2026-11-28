from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src" / "niakvio_brain_llm" / "planner.py").read_text(encoding="utf-8")

assert "FIELD_BRAIN_ADVISOR_MODEL" in source
assert "user_chars={len(user)}" in source
assert "system_chars={len(system_prompt)}" in source
assert "total_chars={len(user) + len(system_prompt)}" in source
assert "experiences={len(experiences)} documents={len(documents)}" in source
assert "outcome=starting raw_content_logged=false" in source
assert "outcome=error " in source
assert "outcome=success " in source
assert "raw_content_logged=false" in source

print("Brain advisor latency telemetry contract passed")
