# Learning loop

NiakVIO Brain learns from verified execution outcomes, not from LLM confidence.

## Runtime loop

1. Build a bounded RepairRequest from current NiakVIO state.
2. Retrieve relevant historical experiences and document chunks.
3. Derive deterministic causal/mutation policy.
4. Ask the local LLM for a RepairProposal.
5. Apply production guards.
6. NiakVIO executes the candidate only in its existing sandbox/verifier.
7. Feed the VerificationOutcome back into the BrainSession.
8. Replan only if repair budget remains and the next hypothesis is different.
9. Persist a sanitized learning record.

## Memory promotion

### Validated

A repair that passes NiakVIO proof gates becomes:

- positive RAG memory;
- a possible supervised fine-tuning/LoRA candidate when its causal label is explicit.

### Failed

A failed candidate becomes:

- negative RAG memory;
- a constraint against repeating the same hypothesis;
- never positive LoRA truth.

### Abstained

A safe abstention becomes:

- safety memory;
- not LoRA truth unless a later verified outcome proves the decision class.

### Inconclusive

An inconclusive run remains transient and does not become durable training truth.

## Why this matters

The model is allowed to reason and propose, but it cannot train itself on its own claims. Only NiakVIO verification can promote an experience toward training data.

This keeps the loop self-improving without allowing model hallucinations to recursively become "knowledge".
