"""Private FORCE keeps 3B default and permits only a hash-pinned 9B challenger."""
from pathlib import Path

root=Path(__file__).resolve().parents[1]
workflow=(root/".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")

model_profile_step = workflow.split("      - name: Resolve bounded local model profile", 1)[1].split("\n      - ", 1)[0]
assert "if: steps.deterministic_force.outputs.ready != 'true'" in model_profile_step
assert "steps.route.outputs.llm_needed == 'true'" not in model_profile_step
# Merely resolving budgets must not start, download, or cache a model when the
# candidate is a deterministic replay with no LLM calls.
assert "if: steps.route.outputs.llm_needed == 'true' && steps.deterministic_force.outputs.ready != 'true'" in workflow

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

# The same exact-SHA live observer used by NiakVIO's hosted repair must
# be bridged to private FORCE, not silently replaced with old MD/chat priors.
# Keep the first provider proof bounded; larger pages must remain read-only
# and use the current census without running a fleet of network probes.
assert "Capture exact-current provider live preflight for one representative" in workflow
assert "steps.page.outputs.count == '1'" in workflow
assert 'python scripts/capture_brain_live_context.py' in workflow
assert 'sourceSha' in workflow and 'steps.source.outputs.sha' in workflow
assert 'wrong provider preflight' in workflow
assert 'stale source preflight' in workflow
assert 'preflight cannot publish' in workflow
assert 'structured network evidence' in workflow
assert "NIAKVIO_REQUIRE_DECODE_PROOF: '1'" in workflow
assert 'incomplete strict repair fixture contract' in workflow
assert 'provider=$target ready=false reason=capture_failed_or_timeout' in workflow
assert 'FIELD_BRAIN_LIVE_PREFLIGHT' in workflow
assert 'live_args=(--live-evidence' in workflow
assert workflow.count('"\x24{live_args[@]}"') == 2, "both repair + advisor must consume the exact same live context"
assert 'rm -f "$RUNNER_TEMP/niakvio-brain-live-evidence.json"' in workflow
assert 'proof_authority=false' in workflow
assert 'npm ci --prefix niakvio --ignore-scripts --no-audit --no-fund' in workflow

print("PRIVATE_GUIDANCE_MODEL_ESCALATION_OK default=3B challenger=9B pinned=true live-source=conditional-exact-sha")
