# Private conversation memory pipeline

Raw ChatGPT exports should live in a separate private repository.

Recommended flow:

1. Request/download the official ChatGPT account export.
2. Extract conversations.json (or numbered conversation JSON files).
3. Filter only conversations that belong to the NiakVIO project.
4. Remove unrelated chats, personal data, secrets, credentials, URLs/tokens that should not become model memory.
5. Convert useful technical episodes into the sanitized experience schema from this repository.
6. Push only the sanitized JSONL output to the Brain training/RAG pipeline.

The public Brain repository should never require access to raw private ChatGPT conversations.

There is intentionally no dependency on an unofficial ChatGPT web-session API.
