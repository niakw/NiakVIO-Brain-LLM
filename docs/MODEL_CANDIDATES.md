# Model candidates

NiakVIO Brain benchmarks small local models under the same RAG, prompt and raw-model benchmark.

## Active lightweight candidates

- Qwen2.5-Coder-1.5B-Instruct Q4_K_M — baseline.
- Qwen2.5-Coder-3B-Instruct Q4_K_M — larger code-specialized challenger.
- Qwen3.5-2B Q4_K_M — newer small general/reasoning challenger.

## Qwen3.8

Qwen3.8 is tracked, but the official current family does not provide a lightweight 1-3B model suitable for the standard GitHub CPU path.

Current practical dense candidate:
- Qwen3.8-27B
- llama.cpp GGUF available
- Q4_K_M is roughly 19 GB before runtime/context overhead

That makes it unsuitable as the default hosted GitHub Actions Brain model. It may later be useful as:

- an offline teacher for distillation;
- a benchmark/reference model on a larger self-hosted runner;
- an occasional dataset/critic generator whose outputs still require NiakVIO verification.

It is not required for runtime autonomy.

## Selection rule

The production model is selected by measured NiakVIO performance, not model generation number.

Priority:
1. causal/strategy accuracy;
2. safe evidence handling;
3. valid provider-local patch proposals;
4. latency and RAM on GitHub Actions;
5. model size.

The deterministic Brain remains responsible for safety and authority boundaries regardless of the selected LLM.
