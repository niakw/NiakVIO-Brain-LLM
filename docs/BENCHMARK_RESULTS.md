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

Verification tests are generated deterministically by the Brain and are not scored as an LLM responsibility.

## Current expanded historical benchmark — 25 cases

Current public-only baseline, rerun during the private-memory A/B validation:

| Metric | Result |
|---|---:|
| Schema valid | 25/25 |
| Provider identity | 25/25 |
| Causal layer | 25/25 |
| Canonical strategy | 25/25 |
| Mutation policy | 25/25 |
| Mutation validity | 25/25 |
| Raw abstention policy | 24/25 |
| Brain verification plan | 25/25 |
| Raw fully compliant | 24/25 |

The single remaining raw-model miss is `hist-api-recipe-proof`: the model selects the correct layer and strategy but does not abstain despite insufficient patch context. Production `force_abstain` policy blocks execution, so this cannot bypass deterministic Brain safety.

## Private chat memory A/B — 25 cases

Workflow run: `35898406320`.

Summary artifact digest:

`sha256:681ee198c39b7749b599e92e9789de9c71da48be69c5f74b928b26ef3d91027e`

The exact same Qwen2.5-Coder-3B runtime and 25-case historical benchmark were run with:

1. public NiakVIO MEMORY/docs only;
2. public memory plus the ephemeral `niakvio-private` ChatGPT memory index.

| Metric | Public only | Public + private | Delta |
|---|---:|---:|---:|
| Schema valid | 25/25 | 25/25 | 0 |
| Provider identity | 25/25 | 25/25 | 0 |
| Causal layer | 25/25 | 25/25 | 0 |
| Canonical strategy | 25/25 | 25/25 | 0 |
| Mutation policy | 25/25 | 25/25 | 0 |
| Mutation validity | 25/25 | 25/25 | 0 |
| Raw abstention policy | 24/25 | 24/25 | 0 |
| Brain verification plan | 25/25 | 25/25 | 0 |
| Raw fully compliant | 24/25 | 24/25 | 0 |

Private memory was actually retrieved in **11/25 cases**.

Conclusion:

- enabling private chat memory produces **no measured regression**;
- it does not produce a measurable score increase on this historical corpus;
- it enriches historical context while deterministic Brain priors/policies preserve the same causal and safety discipline;
- the same single raw abstention miss remains in both modes.

Private memory therefore remains supplemental historical context, never proof and never an authority override.

## Privacy / isolation

Private chat data is checked out read-only from `niakvio-private`.

The generated private document index is ephemeral:

- it is not committed;
- it is not uploaded as a workflow artifact;
- TOOL transcript blocks are excluded;
- recognizable tokens, authorization values, emails, phone numbers, IP addresses and personal home paths are redacted;
- every private-memory row is `proof_authority=false`.

The public repository CI includes a privacy audit for concrete secrets/PII in tracked source, docs, workflows and configuration.

## Model comparison

Qwen2.5-Coder-1.5B remains the small reference model but was weaker on abstention discipline.

Qwen3.5-2B correctly classified causal layers but was weaker on mutation/abstention discipline under the same NiakVIO benchmark.

Qwen3.8 is tracked as a future large teacher/critic candidate, not the default CPU runtime.
