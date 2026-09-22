# Model candidates

Official model-family authority: QwenLM repositories and official model cards.

## Official Qwen family state used by NiakVIO Brain

The official QwenLM/Qwen3.8 repository currently records:

- Qwen3.5: 0.8B, 2B, 4B, 9B plus larger models;
- Qwen3.6: 27B and 35B-A3B;
- Qwen3.8: 27B and 2.4T-A95B.

QwenLM also documents llama.cpp support for the Qwen3.5 open-model series.

## Active lightweight candidates

- Qwen2.5-Coder-1.5B-Instruct Q4_K_M — baseline.
- Qwen2.5-Coder-3B-Instruct Q4_K_M — larger code-specialized challenger.
- Qwen3.5-2B Q4_K_M — newer small reasoning/agentic challenger.

All candidates are evaluated with the exact same NiakVIO RAG, document memory, causal priors and raw benchmark cases.

## Qwen3.8

Qwen3.8 is tracked as a future large teacher/critic, not as the default GitHub CPU runtime.

The smallest current Qwen3.8 dense model is 27B, which is outside the intended lightweight hosted-runner budget once quantized model bytes, KV cache and runtime overhead are included.

Potential future roles:

- teacher for distillation into a small NiakVIO model;
- reference/critic on a larger self-hosted runner;
- occasional generation of candidate training examples that still require NiakVIO verification.

It is not required for runtime autonomy.

## Selection rule

The production model is selected by measured NiakVIO performance, not model generation number.

Priority:

1. causal-layer accuracy;
2. strategy accuracy;
3. evidence/abstention judgment;
4. valid provider-local patch proposals;
5. latency and RAM on GitHub Actions;
6. model size.

The deterministic Brain remains responsible for authority and safety boundaries regardless of the selected LLM.
