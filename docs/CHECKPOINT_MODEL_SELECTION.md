# Brain checkpoint — model selection

## Baseline already measured

Qwen2.5-Coder-1.5B Q4_K_M, raw model benchmark:

- schema valid: 6/6
- provider identity: 6/6
- causal layer: 6/6
- canonical strategy: 5/6
- mutation-policy compliance: 6/6
- mutation structural validity: 6/6
- verification-plan compliance: 5/6
- abstention-policy compliance: 1/6

Interpretation:

The 1.5B model already understands the causal layer surprisingly well. Its principal weakness is control discipline: it often describes the correct next diagnostic but leaves `abstain=false` even when the Brain policy requires more evidence.

The production Brain therefore does not delegate final mutation/abstention authority to the LLM.

## Comparisons in progress

Same raw benchmark, same RAG/doc memory:

- Qwen2.5-Coder-3B Q4_K_M
- Qwen3.5-2B Q4_K_M

## Decision rule

A larger/newer model is promoted only if it materially improves raw reasoning/discipline without unacceptable latency/RAM cost.

A perfect guarded-production score alone is not sufficient because deterministic schema constraints can mask model weaknesses.
