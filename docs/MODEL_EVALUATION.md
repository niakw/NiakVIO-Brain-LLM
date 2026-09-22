# Model promotion criteria

A local model is not promoted because one smoke test passes.

## Production invariants

NiakVIO remains the proof authority. The LLM may diagnose and propose, but it cannot:

- override current census/authority state with stale memory;
- mutate Core or ProviderBase through provider repair;
- patch a provider when the causal layer is harness/network/core;
- invent current endpoints, placeholder URLs, fake diffs or unobserved facts;
- publish a mutation without a verification plan.

## Evaluation layers

### 1. Retrieval

Historical/public memory must retrieve the relevant NiakVIO case from partial evidence.

Current public baseline: 32 historical cases; retrieval recall is measured separately from model reasoning.

### 2. Raw model reasoning

Golden benchmark runs without production answer constraints. It measures whether the model itself follows:

- provider identity;
- causal layer;
- strategy prior;
- mutation policy;
- mutation validity;
- abstention policy;
- verification-plan requirement.

### 3. Guarded production planning

The production planner then applies deterministic causal/schema/mutation/evidence guards.

Passing this layer means the output is safe enough to hand to a NiakVIO sandbox; it does not mean the provider is repaired.

### 4. NiakVIO verification

Only the existing NiakVIO sandbox, playback/identity proof, regression gates and census can validate success.

## Model selection

Qwen2.5-Coder-1.5B Q4 is the baseline.

A larger/smarter candidate (initially Qwen3.5-2B Q4) should replace it only if the raw golden benchmark materially improves while remaining practical on GitHub Actions.

## LoRA gate

Do not fine-tune yet.

LoRA becomes useful only after the private/public sanitized corpus contains enough explicitly validated causal labels and repair outcomes to improve the raw model rather than teach historical mistakes.
