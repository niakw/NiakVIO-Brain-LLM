#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
batch=(ROOT/"scripts/plan_batch_from_checkout.py").read_text(encoding="utf-8")
workflow=(ROOT/".github/workflows/niakvio-private-guidance.yml").read_text(encoding="utf-8")

assert 'budget_seconds = min(budget_cap, 600)' in batch
assert 'failure_key == "provider_transport_gap"' in batch
assert 'budget_seconds = min(budget_cap, 300)' in batch
assert 'failure_key == "transport_environment_gap"' in batch
assert 'budget_seconds = min(budget_cap, 180)' in batch
assert '--force-provider-budget-seconds 600' in workflow
assert '--force-provider-budget-seconds 360' not in workflow
assert 'default: "4"' in workflow
assert "PAGE_SIZE: ${{ inputs.page_size || '4' }}" in workflow
assert '-f page_size="${{ inputs.page_size || \'4\' }}"' in workflow
print("FORCE provider budget contract passed")
