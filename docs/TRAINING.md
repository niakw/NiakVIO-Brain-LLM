# Training strategy

## Phase 1 - base model + NiakVIO intelligence

The runtime starts with the selected base model plus:

- NiakVIO causal taxonomy;
- public and sanitized-private RAG;
- authority-aware document memory;
- deterministic routing;
- bounded mutation policy;
- deterministic verification planning.

This phase measures whether project intelligence improves repair quality before spending compute on fine-tuning.

## Phase 2 - LoRA

Train a small adapter only from **explicitly promoted, validated NiakVIO outcomes**.

Positive supervised examples may contain:

- failure class and bounded observations;
- verified causal layer;
- diagnosis;
- selected repair strategy;
- bounded mutation when applicable;
- deterministic verification tests;
- final validated outcome.

The following never become positive SFT truth:

- failed attempts;
- abstentions;
- inconclusive outcomes;
- historical claims without current proof;
- raw ChatGPT conversations;
- model-generated claims not verified by NiakVIO.

Failed attempts remain useful as negative RAG memory. Abstentions remain safety memory.

Default bootstrap floor before considering LoRA: **100 verified examples**, with diversity across providers and failure classes.

## Phase 3 - benchmark and promotion

A trained adapter must beat or materially improve the exact same raw NiakVIO benchmark without regressing safety/mutation discipline.

NiakVIO verification remains the proof authority.

## Phase 4 - optional distillation

Only after the specialized model is demonstrably useful, evaluate distillation to a smaller model for faster hosted CPU inference.

Raw private conversations, secrets, tokens and unrelated personal/project context must never enter training data.
