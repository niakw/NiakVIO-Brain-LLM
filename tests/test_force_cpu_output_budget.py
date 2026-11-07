#!/usr/bin/env python3
"""The first CPU proof may complete a JSON edit; fleet FORCE stays bounded."""
from scripts.plan_batch_from_checkout import force_output_token_caps

normal = {
    "provider_data": (192, 256),
    "provider_patch": (640, 768),
    "provider_js": (640, 768),
    "provider_bloc": (320, 256),
    "other": (320, 384),
}
for scope, caps in normal.items():
    assert force_output_token_caps(scope) == caps, (scope, caps)
    assert force_output_token_caps(scope, cpu_local_single=False) == caps
    if scope != "provider_bloc":
        assert force_output_token_caps(scope, cpu_local_single=True) == caps
assert force_output_token_caps("provider_bloc", cpu_local_single=True) == (1024, 1408)

from pathlib import Path
source = (Path(__file__).resolve().parents[1] / "scripts/plan_batch_from_checkout.py").read_text()
for required in (
    'NIAKVIO_FORCE_CPU_OUTPUT_BUDGET',
    'args.backend == "local"',
    'len(args.provider) == 1',
    'int(args.max_hypotheses) == 1',
    'not portfolio_reserved',
    'truncated_completion and not cpu_output_budget',
    'FIELD_BRAIN_FORCE_OUTPUT_BUDGET',
    'retry_tokens',
):
    assert required in source, required
print("CPU_FORCE_OUTPUT_BUDGET_OK default-fleet-isolated-local-1024-1408")
