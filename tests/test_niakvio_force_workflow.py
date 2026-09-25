from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / ".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")

assert "--mode repair" in workflow
assert "--advisor-only" in workflow
assert "routing-force-summary.json" in workflow
assert "force_llm_needed=" in workflow
assert "-c 32768" in workflow
assert "-np 1" in workflow
assert "private-force-batch.jsonl" in workflow
assert "publish_niakvio_force_mutations.py" in workflow
assert "guidance/niakvio-force-mutations.json" in workflow
assert "sandboxMutationAuthority" in workflow
assert 'publicationAuthority") is False' in workflow
assert "provider_patch" in workflow

print("NiakVIO private guidance Force-mutation workflow contract passed")
assert "--workers 1" in workflow
assert "--max-tokens 256" in workflow
assert "--timeout-seconds 75" in workflow
assert "--timeout-seconds 45" in workflow
assert "--limit 4" not in workflow
assert "requested_repair_queue" in workflow
assert "niakvio-guidance-targets.txt" in workflow
assert '"${provider_args[@]}"' in workflow
assert "Force routing requested" in workflow
assert "produced zero executable mutations" in workflow
force_command = workflow.index("--mode repair \\\n            \"${provider_args[@]}\" \\\n            --endpoint")
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
assert "files=3" in workflow
