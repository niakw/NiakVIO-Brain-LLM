# Standalone Brain readiness

This checklist defines when NiakVIO-Brain-LLM can be called **ready as a standalone Brain**.

It does **not** authorize or perform integration with NiakVIO production.

## Required

- [x] Local/offline-capable LLM runtime through llama.cpp
- [x] Replaceable model backend
- [x] NiakVIO causal taxonomy and priors
- [x] Public repair-experience RAG
- [x] Authority-aware MEMORY/document retrieval
- [x] Current census -> causal failure normalization
- [x] Deterministic routing before LLM inference
- [x] Separate repair vs diagnostic queues
- [x] Evidence-depth batch prioritization
- [x] Skip model startup when no LLM target exists
- [x] Provider-local mutation DSL
- [x] Cross-provider/Core/ProviderBase mutation guards
- [x] Placeholder/fake endpoint/fake diff rejection
- [x] Deterministic verification-plan ownership
- [x] Bounded propose -> verify -> replan session
- [x] Positive / negative / safety / transient learning tiers
- [x] Private NiakVIO-only sanitized-memory contract
- [x] Public + sanitized-private RAG merge
- [x] Verified-only SFT dataset builder and validator
- [x] LoRA policy present and disabled until sufficient verified data
- [x] Qwen model comparison performed
- [x] Provisional runtime selected: Qwen2.5-Coder-3B Q4_K_M
- [x] Read-only NiakVIO evidence contract CI
- [x] Unit/contract CI
- [ ] Compact-context 6-case 3B benchmark passes without material quality regression
- [ ] Expanded historical 3B benchmark accepted

## Explicitly deferred

- NiakVIO production bridge
- automatic provider patch application
- census mutation
- publication
- LoRA training itself

Those are separate phases and must not be enabled merely because the standalone Brain is ready.

## Definition of done

When the two remaining benchmark gates pass, the repository can be tagged as the first standalone Brain baseline.

At that point integration may be designed separately, but remains disabled until explicitly requested.
