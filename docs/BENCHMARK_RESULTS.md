# Benchmark results — standalone baseline

## Selected runtime

- Model: Qwen2.5-Coder-3B-Instruct
- Quantization: Q4_K_M
- Runtime: llama.cpp
- Inference mode: local/OpenAI-compatible HTTP
- Third-party inference API: not required

## Golden benchmark — 6 cases

Compact-context benchmark:

| Metric | Result |
|---|---:|
| Causal layer | 6/6 |
| Canonical strategy | 6/6 |
| Mutation policy | 6/6 |
| Mutation validity | 6/6 |
| Abstention policy | 6/6 |

Verification tests are no longer scored as an LLM responsibility. They are generated deterministically by the Brain.

## Expanded historical benchmark — 25 cases

Sharded GitHub Actions benchmark:

| Metric | Result |
|---|---:|
| Schema valid | 25/25 |
| Provider identity | 25/25 |
| Causal layer | 25/25 |
| Canonical strategy | 24/25 |
| Mutation policy | 25/25 |
| Mutation validity | 25/25 |
| Raw abstention policy | 24/25 |
| Brain verification plan | 25/25 |
| Raw fully compliant | 23/25 |

Workflow run: `35711072623`.

Merged artifact digest:

`sha256:247fc52595baa4205b5057204aa02f2c431be36841e2816ad18106983caf0dd7`

## Interpretation

The 3B model is promoted because it combines:

- perfect causal-layer classification on the expanded set;
- near-perfect canonical strategy selection;
- perfect mutation-policy compliance;
- perfect structural mutation validity;
- strong raw abstention discipline;
- practical hosted CPU size.

The two raw-model misses are covered by deterministic production policy:

1. a core case returned `abstain` instead of the historical strategy; high-confidence production strategy constraints prevent this drift;
2. one provider API-recipe case did not set `abstain=true` despite insufficient patch context; production `force_abstain` policy blocks execution.

These guards are intentionally part of the Brain architecture rather than delegated to model confidence.

## Model comparison

Qwen2.5-Coder-1.5B remains the small reference model but was weaker on abstention discipline.

Qwen3.5-2B correctly classified causal layers but was weaker on mutation/abstention discipline under the same NiakVIO benchmark.

Qwen3.8 is tracked as a future large teacher/critic candidate, not the default CPU runtime.
