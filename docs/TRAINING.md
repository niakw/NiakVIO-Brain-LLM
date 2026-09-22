# Training strategy

## Phase 1 - no fine-tuning

Start with the base coder model plus retrieved NiakVIO experiences. This measures whether
the contracts, context selection and verification loop are useful before spending compute.

## Phase 2 - LoRA

Train a small adapter only from sanitized, verified outcomes. Preferred examples contain:

- failure class and bounded observations;
- diagnosis;
- selected repair strategy;
- bounded mutation;
- requested verification tests;
- final validated or abstained outcome.

Failed attempts remain useful for retrieval/negative memory but should not be blindly used
as positive supervised targets.

## Phase 3 - distillation

Only after the specialized model is demonstrably useful, evaluate distillation to a smaller
model for faster GitHub Actions inference.

Raw private conversations, secrets, tokens and unrelated personal/project context must never
enter training data.
