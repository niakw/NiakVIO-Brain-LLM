# Qwen upstream authority

NiakVIO Brain treats the official QwenLM GitHub organization as the source of truth for Qwen family releases:

- https://github.com/orgs/QwenLM/repositories
- https://github.com/QwenLM/Qwen3.8
- https://github.com/QwenLM/Qwen3-Coder

Runtime GGUF files may come from a compatible distribution when official GGUF weights are not published directly by Qwen, but model-family existence and capabilities must be verified against official QwenLM information first.

## Current family snapshot

From the official Qwen3.8 repository:

- Qwen3.5 small dense releases include 0.8B, 2B, 4B and 9B.
- Qwen3.6 currently targets much larger 27B / 35B-A3B classes.
- Qwen3.8 currently exposes 27B and 2.4T-A95B.
- llama.cpp is documented as supporting the Qwen3.5 open-model series.

## NiakVIO policy

A newer generation does not automatically replace the runtime Brain model.

Promotion requires:

1. same NiakVIO golden benchmark;
2. same public/private RAG corpus;
3. same raw-model evaluation mode;
4. acceptable hosted-runner RAM/latency;
5. no regression in safe evidence handling.

Large models such as Qwen3.8 may be used later as teacher/critic models for dataset generation or distillation without becoming the production runtime.
