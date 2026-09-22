# Brain checkpoint — model selection

## Qwen2.5-Coder-1.5B Q4_K_M

Raw model benchmark, 6 NiakVIO golden cases:

- schema valid: 6/6
- provider identity: 6/6
- causal layer: 6/6
- canonical strategy: 5/6
- mutation-policy compliance: 6/6
- mutation structural validity: 6/6
- verification-plan compliance: 5/6
- abstention-policy compliance: 1/6

Strength: efficient, correct causal classification, mostly correct strategy.
Weakness: too eager; often fails to mark required abstention.

## Qwen2.5-Coder-3B Q4_K_M

Same raw benchmark:

- schema valid: 6/6
- provider identity: 6/6
- causal layer: 6/6
- canonical strategy: 5/6
- mutation-policy compliance: 6/6
- mutation structural validity: 6/6
- verification-plan compliance: 1/6
- abstention-policy compliance: 6/6

Strength: much better control discipline.
Weakness: often abstains without expressing the concrete next verification step; strategy accuracy does not improve over 1.5B and runtime is slower.

## Qwen3.5-2B

First run was invalid as a model comparison because default Qwen3.5 thinking consumed the 4096-token context before final JSON. llama.cpp logs showed every case ending truncated during reasoning.

A corrected benchmark is now run with:

- reasoning disabled;
- reasoning format none;
- 8192-token context.

Do not compare the initial 0/6 JSON result as model intelligence.

## Decision rule

A larger/newer model is promoted only if it materially improves raw reasoning and evidence discipline without unacceptable latency/RAM cost.

Guarded-production success alone is insufficient because deterministic schema constraints can mask model weaknesses.
