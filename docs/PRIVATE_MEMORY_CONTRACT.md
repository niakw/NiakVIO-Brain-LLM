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

## FORCE reuse of existing project knowledge (2026-11-18)

The private-guidance production workflow already runs
`import_private_chat_project.py`, `import_public_docs.py` and
`import_public_niakvio.py` before actual local FORCE generation. This is the
same NiakVIO project memory, not a second database or fine-tuned model.

The compact FORCE generator now reserves one provider-specific private-chat
RAG result when present, and includes a bounded redacted historical excerpt.
Unrelated conversations are rejected before prompting; public Markdown,
validated manual reverse strategies, and exact source-pinned negative
experiments retain their separate relevance/provenance channels.
Each contextual hint explicitly has `proof_authority=false` and may never
supply network URLs, provider identity proof or an accepted mutation. The
public-only hosted FORCE CI cannot access private chat data; it checks only
public memory and synthetic private-access contracts.

The `Private NiakVIO Chat Memory Contract` workflow checks the actual source
corpus, masks local user paths regardless of case, bearer tokens and other
identifiers, validates provider retrieval and explicitly checks
`BrainPlanner._prepare(compact_force=True)` →
`build_force_prompt_payload` with no private source path or URL in hints.
It prints aggregate counts/provenance booleans only and deletes ephemeral
JSONL at job end. The 2026-11-18 run `44338035084` passed with 202 source
conversations, 167 indexed, 6,620 non-tool documents and one real private hint
at the FORCE boundary. Neither this test nor a 3B/7B/9B diagnostic benchmark
is an end-to-end playable provider repair.

## Learning / LoRA

Private chat memory may improve retrieval immediately.

It does **not** become positive SFT/LoRA truth by itself. A historical chat-derived strategy can enter supervised training only after a current NiakVIO verification outcome validates the causal label and repair result.

Failed attempts remain negative RAG memory, not supervised truth.

## Privacy

The importer is scoped to the NiakVIO project only. Other ChatGPT projects are rejected by Project ID validation.

The public Brain repository must never contain raw private conversation backups or generated private-memory indexes.
