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

Owns reasoning:

- normalize a bounded repair request;
- retrieve similar verified experience;
- classify causal layer;
- propose a provider-local mutation or abstain;
- consume verification feedback;
- learn sanitized outcomes;
- prepare LoRA/SFT data only from explicitly validated labels.

The LLM has no publication authority.

## Runtime flow

1. Read current NiakVIO checkout.
2. Build RepairRequest for one symptomatic provider.
3. Retrieve the nearest NiakVIO experiences.
4. Ask the local model for a schema-constrained RepairProposal.
5. Reject cross-provider/Core mutations.
6. Return proposal to NiakVIO.
7. NiakVIO applies it only in a sandbox and performs its ordinary proof gates.
8. Feed the result back into a bounded BrainSession.
9. Persist only a sanitized learning record.

## Integration boundary

The future production bridge can invoke:

    python scripts/plan_from_checkout.py       --niakvio-root /path/to/NiakVIO       --provider <id>       --experience <sanitized.jsonl>

The result is JSON and remains proposal-only.

## Private memory

A private repository may enrich the sanitized experience store from ChatGPT project
exports. Raw conversations never become a runtime dependency and never enter this
public repository.
