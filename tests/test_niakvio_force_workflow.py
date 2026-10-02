from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / ".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")

assert "--mode repair" in workflow
assert "--advisor-only" in workflow
assert "routing-force-summary.json" in workflow
assert "routing-force.jsonl" in workflow
assert "routing.jsonl" in workflow
assert "force_llm_needed=" in workflow
assert "-c 16384" in workflow
assert "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M" in workflow
assert "--model qwen2.5-coder-7b" in workflow
assert "-np 1" in workflow
assert "private-force-batch.jsonl" in workflow
assert "publish_niakvio_force_mutations.py" in workflow
assert "guidance/niakvio-force-mutations.json" in workflow
assert "sandboxMutationAuthority" in workflow
assert 'publicationAuthority") is False' in workflow
assert "provider_patch" in workflow

print("NiakVIO private guidance Force-mutation workflow contract passed")
assert "--workers 1" in workflow
assert "--max-hypotheses 4" in workflow
assert "--max-tokens 512" in workflow
assert "--timeout-seconds 240" in workflow
assert "--timeout-seconds 45" in workflow
assert "--limit 4" not in workflow
assert "requested_repair_queue" in workflow
assert "niakvio-guidance-targets.txt" in workflow
assert "audit_registered_runtime_variant_coverage" in workflow
assert "niakvio-runtime-variant-coverage.json" in workflow
assert "coverage_high" in workflow
assert "dynamic_high" in workflow
assert "audit_current_dynamic_variant_coverage" in workflow
assert "niakvio-dynamic-variant-coverage.json" in workflow
assert "repair_set|coverage_high|dynamic_high" in workflow
assert 'Path("niakvio/manifest.json")' in workflow
assert "coverage_high &= current" in workflow
assert "dynamic_high &= current" in workflow
assert "*sorted(dynamic_high)" in workflow
assert "neither current repairQueue nor static/dynamic variant coverage debt" in workflow
assert '"${provider_args[@]}"' in workflow
assert "FIELD_NIAKVIO_FORCE_MUTATIONS_READY ready=false" in workflow
force_command = workflow.index("--mode repair \\\n            --max-hypotheses 4 \\\n            --stop-after-first-mutation \\\n            \"${provider_args[@]}\" \\\n            --endpoint")
advisor_command = workflow.index("--mode brain \\\n            \"${provider_args[@]}\" \\\n            --endpoint")
assert force_command < advisor_command

assert "select_niakvio_guidance_page.py" in workflow
assert "merge_niakvio_guidance_page.py" in workflow
assert "niakvio-guidance-page.txt" in workflow
assert "niakvio-guidance-state.json" in workflow
assert "Continue remaining guidance page" in workflow
assert "steps.page.outputs.complete" in workflow
assert "actions: write" in workflow
assert "mutationContextFingerprint" in workflow
assert "guidance/niakvio-guidance-state.json" in workflow
assert "guidance/niakvio-force-diagnostics.json" in workflow
assert "--previous-diagnostics" in workflow
assert "niakvio-guidance-family-wave.json" in workflow
assert "execution_blocked=" in (ROOT / "scripts/select_niakvio_repair_family_wave.py").read_text(encoding="utf-8")
assert "files=4" in workflow

assert "brain_sha:" in workflow
assert 'ref: ${{ inputs.brain_sha || github.sha }}' in workflow
assert "niakvio-private-guidance-v4-${{ (github.event_name == 'workflow_dispatch' && inputs.brain_sha) || 'current' }}" in workflow
assert "cancel-in-progress: ${{ github.event_name == 'push' }}" in workflow

assert 'echo "brain_sha=$brain_sha" >> "$GITHUB_OUTPUT"' in workflow
assert '-f brain_sha="${{ steps.page.outputs.brain_sha }}"' in workflow
assert '-f brain_sha="$(git -C brain rev-parse HEAD)"' not in workflow
