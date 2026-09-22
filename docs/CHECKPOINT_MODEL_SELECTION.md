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

Strength: best current control discipline while preserving causal/strategy quality.

The missing verification-plan behavior is no longer delegated to the model in production: the Brain derives mandatory tests deterministically from the causal strategy.

Measured 6-case inference wall time was roughly 10.5 minutes on the hosted CPU runner with the older, larger prompt context.

## Qwen3.5-2B Q4_K_M

The initial run was invalid because default thinking consumed the context before final structured JSON.

The corrected bounded-thinking run produced:

- schema valid: 6/6
- provider identity: 5/6
- causal layer: 6/6
- canonical strategy: 5/6
- mutation-policy compliance: 4/6
- mutation structural validity: 4/6
- verification-plan compliance: 6/6
- abstention-policy compliance: 2/6

Measured 6-case inference wall time was roughly 8.6 minutes.

It is only about 18% faster in this test while materially weaker on mutation and abstention discipline.

## Current provisional choice

**Qwen2.5-Coder-3B Q4_K_M** is the provisional runtime model.

It is not final until:

1. the compact-context 6-case benchmark shows no quality regression;
2. the expanded historical benchmark is acceptable;
3. CI/read-only boundaries remain green.

## Decision rule

A newer/larger model is promoted only if it materially improves raw reasoning and evidence discipline without unacceptable latency/RAM cost.

Guarded-production success alone is insufficient because deterministic schema constraints can mask model weaknesses.
