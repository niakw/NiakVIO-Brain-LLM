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

## Allowed direction

`ChatGPT export -> NiakVIO-private -> sanitize/extract -> structured JSONL -> NiakVIO-Brain-LLM RAG`

Never:

`raw conversations -> public Brain repo`

## Training

Private sanitized records may enrich RAG immediately.

They become LoRA/SFT candidates only after a current NiakVIO verification outcome explicitly validates the causal label and repair result.
