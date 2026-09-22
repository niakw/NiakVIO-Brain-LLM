# Brain model selection

## Selected runtime

**Qwen2.5-Coder-3B-Instruct Q4_K_M** is the standalone runtime baseline.

Selection is based on NiakVIO-specific benchmarks, not model generation number.

## 1.5B reference

Qwen2.5-Coder-1.5B was efficient and strong on causal classification, but materially weaker on abstention discipline.

It remains a useful small-model reference, not the selected runtime.

## Qwen3.5-2B challenger

Qwen3.5-2B classified causal layers correctly but was weaker on mutation-policy and abstention discipline in the current benchmark.

It remains a challenger for future re-evaluation.

## Qwen3.8

Qwen3.8 is currently too large for the intended default hosted CPU path.

It may later serve as:

- a teacher for distillation;
- an offline critic/reference model;
- a generator of candidate training examples that still require NiakVIO verification.

## Accepted 3B results

### Compact 6-case benchmark

- causal layer: 6/6
- canonical strategy: 6/6
- mutation policy: 6/6
- mutation validity: 6/6
- abstention policy: 6/6

### Expanded 25-case historical benchmark

- causal layer: 25/25
- canonical strategy: 24/25
- mutation policy: 25/25
- mutation validity: 25/25
- raw abstention policy: 24/25
- deterministic Brain verification plan: 25/25
- fully compliant raw output: 23/25

The two misses are bounded by deterministic production policy and cannot directly mutate or publish NiakVIO.

## Runtime principle

The deterministic Brain owns:

- causal authority boundaries;
- mutation permission;
- forced abstention;
- verification planning;
- routing;
- final learning promotion.

Qwen owns bounded diagnosis/synthesis where deterministic routing decides an LLM is useful.

NiakVIO remains the future execution/proof authority.
