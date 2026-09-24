# NiakVIO Brain LLM

Independent AI/LLM layer for NiakVIO provider repair.

## Goal

Build an offline-capable NiakVIO-specialized repair brain without coupling its development to the production `niakw/NiakVIO` repository.

The LLM is **never the proof authority**. It diagnoses and proposes bounded repair candidates; NiakVIO remains responsible for sandbox execution, playable-media proof, identity checks, regression guards, census status and publication.

## Architecture

```text
NiakVIO evidence (read-only)
  -> causal normalizer
  -> experience/document retrieval (RAG)
  -> deterministic router
       -> skip / probe / harness-core diagnostic
       -> local LLM only when synthesis is useful
  -> bounded RepairProposal
  -> deterministic mutation + verification policy
  -> external NiakVIO verifier (future integration only)
  -> sanitized positive / negative / safety memory
```

## Runtime model

Selected standalone runtime:

- `Qwen2.5-Coder-3B-Instruct`
- `Q4_K_M`
- `llama.cpp`
- local/OpenAI-compatible HTTP interface
- no third-party inference API required

Measured 6-case raw NiakVIO benchmark:

- causal layer: 6/6
- canonical strategy: 6/6
- mutation-policy compliance: 6/6
- mutation structural validity: 6/6
- abstention-policy compliance: 6/6

Current expanded 25-case historical benchmark:

- schema/provider identity: 25/25
- causal layer: 25/25
- canonical strategy: 25/25
- mutation-policy compliance: 25/25
- mutation structural validity: 25/25
- abstention-policy compliance: 24/25
- deterministic Brain verification plan: 25/25
- raw fully compliant: 24/25

The one remaining raw-model abstention miss is bounded by deterministic production `force_abstain` policy.

Other tracked candidates:

- Qwen2.5-Coder-1.5B — smaller baseline
- Qwen3.5-2B — newer challenger, weaker mutation/abstention discipline in current tests
- Qwen3.8-27B — future teacher/critic candidate, not default hosted CPU runtime

Official Qwen family authority: the QwenLM GitHub organization.

## Scaling model

The Brain does not load or call the LLM for every provider.

Current flow:

1. read census and project evidence;
2. classify the causal failure class;
3. prioritize higher-evidence providers;
4. deterministic routing;
5. start/call Qwen only for `llm_diagnose` or `llm_repair` cases.

Current census routing measurement: 14 Brain-required providers, 7 deterministic and 7 requiring LLM escalation. If a batch contains no LLM targets, model startup is skipped entirely.

## Learning

The model never trains on its own claims.

- validated repair -> positive RAG memory -> possible SFT/LoRA candidate;
- failed repair -> negative RAG memory only;
- safe abstention -> safety memory only;
- inconclusive -> transient memory only.

SFT accepts only explicitly promoted, validated learning records.

## Private chat memory

The Brain can now read the private NiakVIO ChatGPT project from `niakw/niakvio-private` using a read-only repository token.

Runtime flow:

```text
niakvio-private / raw ChatGPT project backup
  -> strict NiakVIO Project-ID validation
  -> signals + USER/ASSISTANT technical transcript filtering
  -> token/email/header redaction
  -> ephemeral private document index
  -> merge with public MEMORY/docs
  -> Brain RAG
```

The private index is generated inside the runner and is never committed or uploaded as a public artifact. TOOL transcript blocks are not indexed. Private chat memory is historical context only: `proof_authority=false` and current NiakVIO verification always wins.

The source secret is `NIAKVIO_PRIVATE_READ_TOKEN` and is used read-only against `niakvio-private`.

A 25-case A/B benchmark retrieved private-memory context in **11/25 cases** with **no quality or safety regression**: public-only and public+private both scored 25/25 causal layer, 25/25 strategy, 25/25 mutation safety and 24/25 raw fully compliant. On this corpus, the chat memory adds historical depth but no measurable score increase, so it remains supplemental rather than being given extra authority.


A 25-case A/B benchmark comparing public-only memory vs public + private chat memory showed **no regression**:

- causal layer: 25/25 in both modes;
- canonical strategy: 25/25 in both modes;
- mutation safety: 25/25 in both modes;
- raw fully compliant: 24/25 in both modes;
- private memory was retrieved in 11/25 cases (25 hits total).

The private memory therefore enriches context without changing already-correct bounded decisions on the current golden set.

## Repository boundaries

This repository owns:

- model/runtime selection;
- RAG and document memory;
- causal priors and routing;
- prompting/contracts;
- bounded mutation policy;
- batch planning;
- learning-memory policy;
- SFT/LoRA dataset preparation;
- benchmarks.

`niakw/NiakVIO` owns:

- provider source/data;
- live probes;
- sandbox execution;
- playback/identity proof;
- census;
- regression gates;
- publication.

## Integration state

**Connected to NiakVIO as a bounded Learning advisor.**

NiakVIO production now pins Brain LLM commit `c752f5c21ded26c578eaeacb492611f3fdb137a9` from its Learning workflow. The workflow builds the public/private retrieval context, routes the current repair cohort, starts the local Qwen runtime only when deterministic routing requires LLM synthesis, and converts model output into an allowlisted prior for the deterministic Brain planner.

The authority boundary remains strict: this repository does not directly mutate or publish NiakVIO providers. Brain LLM guidance is advisory; NiakVIO Learning executes bounded strategies, while current-byte Repair/Retest, playable-media proof, identity checks, regression gates, census status and publication remain authoritative in `niakw/NiakVIO`.

The integration deliberately fails back to deterministic Brain behavior when the local model is unnecessary or unavailable.

## NiakVIO sanitized guidance bridge

The `NiakVIO Private-Guided Advisor` workflow is the only public bridge from
private NiakVIO chat memory to production Repair. Private transcripts stay
ephemeral inside the workflow. The published `niakvio-guidance` branch contains
one allowlisted, non-authoritative hypothesis-ordering file only; current NiakVIO
tests remain the sole proof and publication authority.


### Bounded batch concurrency

Private-guided NiakVIO planning uses one local Qwen process with two llama.cpp parallel
slots and two provider workers. Provider requests remain isolated/read-only, results
are sorted back to deterministic evidence-depth order, and all publication/proof
authority remains outside the model. This prevents independent provider planning
from serializing behind a single LLM slot as repair cohorts grow.
