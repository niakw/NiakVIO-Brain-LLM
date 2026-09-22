# Architecture

## Ownership

### NiakVIO

Owns reality and execution:

- provider catalogue and authored modules;
- census and live evidence;
- sandbox/materialization;
- playback and identity proof;
- non-regression gates;
- publication.

### NiakVIO-Brain-LLM

Owns reasoning and learning:

- normalize bounded provider evidence;
- derive causal failure classes from census depth;
- retrieve public + sanitized-private experience;
- route deterministic/probe/LLM work;
- synthesize bounded provider-local candidates only when useful;
- derive mandatory verification plans;
- consume external verification feedback;
- maintain positive/negative/safety learning memory;
- prepare LoRA/SFT data only from explicitly validated outcomes.

The LLM has no publication authority.

## Runtime flow

1. Read current NiakVIO evidence from a read-only checkout.
2. Build a bounded RepairRequest for each symptomatic provider.
3. Retrieve relevant NiakVIO experiences and documents.
4. Derive the causal prior and mutation/evidence policy.
5. Route the case:
   - skip;
   - deterministic replay/diagnostic;
   - gather missing proof;
   - LLM diagnosis;
   - LLM provider-local repair.
6. Load/call the local model only when the route requires it.
7. Reject cross-provider/Core/ProviderBase mutations and synthetic values.
8. Add the deterministic proof protocol to the proposal.
9. A future NiakVIO bridge may execute the candidate only in its existing sandbox.
10. Feed the external VerificationOutcome into the bounded BrainSession.
11. Persist only sanitized learning records.

## Batch scaling

The batch queue is ordered by evidence depth:

1. candidate proof;
2. chain reached;
3. route proven;
4. remaining repair-eligible cases.

A pre-routing pass can determine that zero LLM calls are necessary and skip model startup entirely.

On the current 46-provider census snapshot, 14 providers require Brain attention and 7 of those are resolved/routed without LLM inference.

## Current integration boundary

This repository is **not connected to NiakVIO production**.

NiakVIO is used read-only for tests and benchmarks. No Brain workflow can currently publish provider changes or update the census.

Integration is a separate future phase.

## Private memory

A private repository may enrich RAG using sanitized NiakVIO-only technical experiences.

Raw conversations never become a runtime dependency and never enter this public repository.
