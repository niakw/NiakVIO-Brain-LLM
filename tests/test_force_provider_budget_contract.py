#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
batch=(ROOT/"scripts/plan_batch_from_checkout.py").read_text(encoding="utf-8")
workflow=(ROOT/".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")

assert 'budget_seconds = min(budget_cap, 600)' in batch
assert 'exact_runtime_template = bool(' in batch
assert 'portfolio={max_hypotheses}' in batch
assert 'FIELD_BRAIN_FORCE_PORTFOLIO_READY' in batch
assert 'FIELD_BRAIN_FORCE_PORTFOLIO_RESERVED' in batch
assert 'FIELD_BRAIN_FORCE_CANDIDATE_BUDGET' in batch
assert 'FIELD_BRAIN_FORCE_CANDIDATE_BUDGET_EXHAUSTED' in batch
assert 'remaining_candidates = max(1, max_hypotheses - candidate_index + 1)' in batch
assert '"variant_coverage_gap",' in batch
assert 'future_reserve = max(0, remaining_candidates - 1) * 45.0' in batch
assert 'max(\n                            90.0,' in batch
assert 'candidate_deadline = min(' in batch
assert 'FIELD_BRAIN_FORCE_PORTFOLIO_FEEDBACK' in batch
assert 'brain-force-portfolio-rejection' in batch
assert '"brain-force-sandbox-memory"' in batch
assert 'negative_memory_rows=' in batch
assert '60 if speculative_portfolio_slot else 180' in batch
assert 'FIELD_BRAIN_FORCE_SPECULATIVE_FAST_FAIL' in batch
assert 'retry=transport-suppressed' in batch
assert 'retry=validation-suppressed' in batch
assert 'failure_key == "provider_transport_gap"' in batch
assert 'budget_seconds = min(budget_cap, 300)' in batch
assert 'failure_key == "transport_environment_gap"' in batch
assert 'budget_seconds = min(budget_cap, 180)' in batch
assert '--force-provider-budget-seconds 600' in workflow
assert 'budget_seconds = min(' in batch
assert '--stop-after-first-mutation' in workflow
assert '--max-hypotheses 4' in workflow
assert 'FIELD_BRAIN_FORCE_EARLY_PUBLISH' in batch
assert '--force-provider-budget-seconds 360' not in workflow
assert 'timeout-minutes: 180' in workflow
assert 'default: "9"' in workflow
assert "PAGE_SIZE: ${{ inputs.page_size || '9' }}" in workflow
assert '-f page_size="${{ inputs.page_size || \'9\' }}"' in workflow
assert 'Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M' in workflow
assert '--model qwen2.5-coder-7b' in workflow
assert '-c 16384' in workflow
assert '--max-tokens 512' in workflow
assert '--timeout-seconds 240' in workflow
assert 'qwen25-coder-7b-q4-km-v1' in workflow
assert 'Qwen/Qwen2.5-Coder-3B-Instruct-GGUF:Q4_K_M' not in workflow
print("FORCE provider budget contract passed")
