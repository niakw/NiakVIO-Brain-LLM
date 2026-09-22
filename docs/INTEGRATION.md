# NiakVIO integration contract

This repository is intentionally decoupled from NiakVIO production.

## Read-side inputs

A future adapter may consume sanitized subsets of:

- automation/provider-census-status.json
- automation/brain-repair-experience.json
- automation/brain-repair-memory.json
- provider-local code/data selected for one repair target
- bounded network/test observations

These are inputs to reasoning, not proof of success.

## Output

The Brain LLM returns a RepairProposal containing diagnosis, strategy, confidence,
bounded mutations and requested tests.

NiakVIO remains authoritative for:

1. applying a candidate in an isolated sandbox;
2. current-byte retest;
3. playable-media and identity proof;
4. non-regression verification;
5. census mutation and publication.

## Safety boundary

The first integration must be opt-in and read-only from NiakVIO's perspective.
No LLM proposal may directly update main, Core or ProviderBase. Promotion occurs only
through existing NiakVIO verification gates.

## Private memory

Raw ChatGPT conversations do not belong in this public repository.
A separate private exporter may emit sanitized JSONL experience/training records.
