# NiakVIO-private memory contract

The public Brain repository must never ingest raw ChatGPT conversations.

## Boundary

`NiakVIO-private` owns raw/private project material.

It may export only sanitized structured repair experiences to Brain-LLM.

Each exported record must:

- declare `project: NiakVIO`;
- contain a failure class and strategy;
- contain only technical provider/Core/harness evidence useful to repair;
- exclude unrelated projects and personal context;
- exclude raw message/transcript bodies;
- remain non-authoritative until replayed against current NiakVIO bytes.

## Recommended source flow

1. Obtain the official ChatGPT account/project export.
2. Keep raw exports only in the private repository.
3. Filter only conversations that belong to NiakVIO.
4. Remove unrelated chats, personal data, secrets, credentials and tokens.
5. Convert useful technical episodes into the structured sanitized experience schema.
6. Export only sanitized JSONL to Brain-LLM.

Allowed direction:

`ChatGPT export -> NiakVIO-private -> sanitize/extract -> structured JSONL -> NiakVIO-Brain-LLM RAG`

Never:

`raw conversations -> public Brain repo`

There is intentionally no dependency on an unofficial ChatGPT web-session API.

## Training

Private sanitized records may enrich RAG immediately.

They become LoRA/SFT candidates only after a current NiakVIO verification outcome explicitly validates the causal label and repair result.
