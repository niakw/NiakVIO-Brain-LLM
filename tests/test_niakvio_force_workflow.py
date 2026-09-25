from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / ".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")

assert "--mode repair" in workflow
assert "--advisor-only" in workflow
assert "routing-force-summary.json" in workflow
assert "force_llm_needed=" in workflow
assert "-c 32768" in workflow
assert "-np 2" in workflow
assert "private-force-batch.jsonl" in workflow
assert "publish_niakvio_force_mutations.py" in workflow
assert "guidance/niakvio-force-mutations.json" in workflow
assert "sandboxMutationAuthority" in workflow
assert 'publicationAuthority") is False' in workflow
assert "provider_patch" in workflow

print("NiakVIO private guidance Force-mutation workflow contract passed")
assert "--workers 2" in workflow
assert "--max-tokens 320" in workflow
assert "--timeout-seconds 150" in workflow
