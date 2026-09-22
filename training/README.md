# NiakVIO LoRA training

LoRA is intentionally **not enabled yet**.

The runtime Brain already specializes Qwen through NiakVIO causal taxonomy, RAG, routing, mutation policy and verification policy. Fine-tuning becomes useful only after enough current repairs have been verified.

## Dataset path

1. Brain proposal is executed externally by the NiakVIO verifier.
2. `sanitized_experience(...)` records the outcome.
3. `scripts/build_learning_corpus.py` separates positive/negative/safety/transient memory.
4. Only records explicitly marked `_learning.sft_candidate=true` are passed to `training/build_sft_dataset.py`.
5. `training/validate_sft_dataset.py` rejects unverified or abstention examples.

## Promotion threshold

Default minimum: **100 verified examples**.

This is a bootstrap floor, not an automatic training trigger. The corpus should also cover multiple failure classes and providers.

## Training runtime

Training is optional and offline. It must not require a third-party inference API.

The adapter should be trained against the exact promoted base-model revision, then benchmarked against the same NiakVIO golden corpus before it can replace the base runtime.

## Never train on

- raw ChatGPT conversations;
- unverified historical claims;
- failed candidate repairs as positive examples;
- inconclusive runs;
- model-generated claims that have not passed NiakVIO proof gates;
- unrelated projects or personal context.

Failed attempts remain useful **negative RAG memory**, not supervised truth.
