# NiakVIO Brain LLM

Independent AI/LLM layer for NiakVIO provider repair.

## Goal

Build an offline-capable NiakVIO-specialized repair model without coupling its development to the production `niakw/NiakVIO` repository.

The LLM is **never the proof authority**. It diagnoses and proposes bounded repair candidates; NiakVIO remains responsible for sandbox execution, playable-media proof, identity checks, regression guards, census status and publication.

## Architecture

```text
NiakVIO evidence
  -> context normalizer
  -> experience retrieval (RAG)
  -> local LLM planner
  -> structured RepairProposal
  -> NiakVIO sandbox/verifier
  -> outcome
  -> sanitized experience memory
```

Initial target model: `Qwen2.5-Coder-1.5B-Instruct`, quantized for CPU inference through llama.cpp. The model backend is replaceable.

## Repository boundaries

- This repository owns: LLM contracts, retrieval, prompting, model adapters, training data format, LoRA/fine-tuning tooling and benchmarks.
- `niakw/NiakVIO` owns: providers, live probes, repair execution, census, safety gates and publication.
- Private ChatGPT/project history must not be copied here raw. A future private memory pipeline should export sanitized training/experience records only.

## Status

Bootstrap v0: contracts + lightweight RAG + local HTTP backend + planner + CI. No writes to the NiakVIO repository.
