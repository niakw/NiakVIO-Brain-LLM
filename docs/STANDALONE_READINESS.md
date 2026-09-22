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
- [x] Runtime selected: Qwen2.5-Coder-3B Q4_K_M
- [x] Read-only NiakVIO evidence contract CI
- [x] Unit/contract CI
- [x] Compact-context 6-case 3B benchmark passes without material quality regression
- [x] Expanded 25-case historical 3B benchmark accepted
- [x] Heavy comparison workflows are manual by default
- [x] Obsolete bootstrap benchmark paths removed

## Accepted benchmark

Expanded historical benchmark, 25 cases:

- 25/25 schema valid
- 25/25 provider identity
- 25/25 causal layer
- 24/25 canonical strategy
- 25/25 mutation policy
- 25/25 mutation validity
- 24/25 raw abstention policy
- 25/25 deterministic Brain verification plan
- 23/25 fully compliant raw model outputs

The two raw-model misses do not bypass production policy:

- high-confidence strategies are constrained by the production schema;
- `force_abstain` is enforced by deterministic Brain policy;
- NiakVIO remains the only future execution/proof authority.

## Explicitly deferred

- NiakVIO production bridge
- automatic provider patch application
- census mutation
- publication
- LoRA training itself

Those are separate phases and remain disabled.

## Definition of done

**Standalone Brain baseline: READY.**

Integration may be designed separately later, but is not enabled by this milestone.
