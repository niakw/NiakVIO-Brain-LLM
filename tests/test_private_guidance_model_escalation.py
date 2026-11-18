"""Private FORCE keeps 3B default and permits only a hash-pinned 9B challenger."""
from pathlib import Path

root=Path(__file__).resolve().parents[1]
workflow=(root/".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")

assert 'default: "qwen25-coder-3b"' in workflow
assert 'options: [qwen25-coder-3b, qwen35-9b]' in workflow
assert 'unsupported local model profile' in workflow
assert 'model="qwen2.5-coder-3b"' in workflow
assert 'model="qwen35-9b"' in workflow
assert "qwen35-9b-q4-ef6f244d" in workflow
assert "SoAIHQ/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q4_K_M.gguf" in workflow
assert "ef6f244d63abcba4f8d30b7cbd9369e9e798fc33cf21109889373f59af329c93" in workflow
assert "--reasoning off" in workflow
assert 'publication_authority=false' in workflow
assert '--model "${{ steps.model_profile.outputs.model }}"' in workflow
assert '--timeout-seconds "${{ steps.model_profile.outputs.force_timeout }}"' in workflow
assert '--force-provider-budget-seconds "${{ steps.model_profile.outputs.provider_budget }}"' in workflow
assert '-f model_profile="${{ steps.model_profile.outputs.profile || \'qwen25-coder-3b\' }}"' in workflow
# Challenger does not change sanitization, proof or publication authority.
assert 'assert force.get("publicationAuthority") is False' in workflow
assert 'assert force.get("proofAuthority") is False' in workflow
assert 'assert d["directMutationAuthority"] is False' in workflow
print("PRIVATE_GUIDANCE_MODEL_ESCALATION_OK default=3B challenger=9B pinned=true")
