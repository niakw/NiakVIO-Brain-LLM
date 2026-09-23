# NiakVIO-private memory contract

The Brain may read the private NiakVIO ChatGPT project from `niakw/niakvio-private` as a historical RAG source.

## Source boundary

Only this project is accepted:

`g-p-6a7f1d27495c819182b4081bfccdafd8`

Expected source path:

`raw/chatgpt-project/g-p-6a7f1d27495c819182b4081bfccdafd8/`

The source repository is read-only to Brain workflows through:

`NIAKVIO_PRIVATE_READ_TOKEN`

The Brain never writes to `niakvio-private`.

## Runtime indexing

Private chat data is not copied into this public repository.

At runtime the Brain:

1. validates the Project ID and project name;
2. reads per-conversation `index.json` signals;
3. indexes technical USER/ASSISTANT transcript chunks as secondary context;
4. excludes TOOL transcript blocks;
5. redacts recognizable tokens, authorization values and email addresses;
6. creates an ephemeral private document JSONL;
7. merges that store with public MEMORY/technical documents;
8. deletes the ephemeral private index at the end of the job.

No private chat JSONL is uploaded as a workflow artifact.

## Authority

Private chat memory is **context, never proof**.

Every private-memory row is marked:

- `private_memory=true`;
- `proof_authority=false`.

Current NiakVIO census, live evidence and deterministic verification always override historical conversation text.

## Learning / LoRA

Private chat memory may improve retrieval immediately.

It does **not** become positive SFT/LoRA truth by itself. A historical chat-derived strategy can enter supervised training only after a current NiakVIO verification outcome validates the causal label and repair result.

Failed attempts remain negative RAG memory, not supervised truth.

## Privacy

The importer is scoped to the NiakVIO project only. Other ChatGPT projects are rejected by Project ID validation.

The public Brain repository must never contain raw private conversation backups or generated private-memory indexes.
