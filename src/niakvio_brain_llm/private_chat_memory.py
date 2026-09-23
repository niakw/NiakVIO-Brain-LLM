from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

PROJECT_ID = "g-p-6a7f1d27495c819182b4081bfccdafd8"
PROJECT_NAME = "NiakVIO"

TECHNICAL_TERMS = {
    "niakvio", "provider", "providers", "providerbase", "stream", "streams",
    "census", "repair", "brain", "route", "routing", "chain", "candidate",
    "harness", "waf", "antibot", "tmdb", "manifest", "sanitizer",
    "materializer", "materialisation", "materialization", "playback",
    "identity", "core", "lego", "domain", "api", "scraper", "scraping",
    "m3u8", "hls", "mp4", "subtitle", "vf", "vostfr", "anime",
    "github", "workflow", "actions", "tailscale", "network", "transport",
    "provider-overrides", "provider_patches", "learn", "learning",
}

SENSITIVE_PATTERNS = [
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]+\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b"), "Bearer [REDACTED]"),
    (re.compile(r"(?i)(authorization\s*[:=]\s*)([^\s'\"]{8,})"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)([^\s'\"]{8,})"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(token\s*[:=]\s*)([^\s'\"]{8,})"), r"\1[REDACTED]"),
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[REDACTED_EMAIL]"),
]

MESSAGE_HEADING = re.compile(r"^##\s+(USER|ASSISTANT|TOOL)\s+·\s+(.+?)\s*$", re.M)


def redact_sensitive(text: str) -> str:
    value = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def technical_score(text: str) -> int:
    lower = text.casefold()
    score = sum(1 for term in TECHNICAL_TERMS if term in lower)
    if text.count(chr(96)) >= 3 or "github.com/" in lower:
        score += 1
    if any(token in text for token in ("provider_", "STREAM_", "TMDB", "FULL OK", "PARTIAL OK", "NO PROOF")):
        score += 2
    return score


def _split_message_sections(markdown: str) -> Iterable[tuple[str, str, str]]:
    matches = list(MESSAGE_HEADING.finditer(markdown))
    for index, match in enumerate(matches):
        role = match.group(1).casefold()
        timestamp = match.group(2).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        yield role, timestamp, body


def _chunk_text(text: str, limit: int = 1800) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + limit)
        if end < len(text):
            split = text.rfind("\n", start, end)
            if split > start + 400:
                end = split
        chunks.append(text[start:end].strip())
        start = end
    return [chunk for chunk in chunks if chunk]


def _document(
    *,
    conversation_id: str,
    title: str,
    source_ref: str,
    heading: str,
    text: str,
    authority: int,
    role: str,
    captured_at: str = "",
) -> dict[str, Any]:
    clean = redact_sensitive(text)
    digest = hashlib.sha256(
        (conversation_id + "\0" + source_ref + "\0" + heading + "\0" + clean).encode("utf-8")
    ).hexdigest()[:20]
    return {
        "kind": "document",
        "document_id": f"private-chat-{digest}",
        "source": "niakvio-private-chat",
        "project": PROJECT_NAME,
        "project_id": PROJECT_ID,
        "conversation_id": conversation_id,
        "conversation_title": title,
        "captured_at": captured_at,
        "path": source_ref,
        "heading": heading,
        "role": role,
        "authority": authority,
        "proof_authority": False,
        "private_memory": True,
        "text": clean,
    }


def import_private_chat_project(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))

    if project.get("id") != PROJECT_ID:
        raise ValueError("unexpected private project id")
    if str(project.get("name") or "").casefold() != PROJECT_NAME.casefold():
        raise ValueError("unexpected private project name")
    if index.get("projectId") != PROJECT_ID:
        raise ValueError("private project index id mismatch")

    rows: list[dict[str, Any]] = []
    conversations_root = root / "conversations"

    for conversation_dir in sorted(p for p in conversations_root.iterdir() if p.is_dir()):
        meta_path = conversation_dir / "index.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        conversation_id = str(meta.get("id") or conversation_dir.name)
        title = str(meta.get("title") or conversation_id)
        captured_at = str(meta.get("capturedAt") or "")
        signals = meta.get("signals") or {}

        if isinstance(signals, dict):
            for signal_kind, values in signals.items():
                if not isinstance(values, list):
                    continue
                for position, value in enumerate(values):
                    text = str(value).strip()
                    if not text or technical_score(text) < 1:
                        continue
                    rows.append(_document(
                        conversation_id=conversation_id,
                        title=title,
                        source_ref=f"conversations/{conversation_id}/index.json",
                        heading=f"{signal_kind} #{position + 1}",
                        text=text,
                        authority=55,
                        role="private_chat_signal",
                        captured_at=captured_at,
                    ))

        for part_path in sorted(conversation_dir.glob("part-*.md")):
            markdown = part_path.read_text(encoding="utf-8", errors="replace")
            for role, timestamp, body in _split_message_sections(markdown):
                if role == "tool":
                    continue
                if technical_score(body) < 2:
                    continue
                for chunk_index, chunk in enumerate(_chunk_text(body), start=1):
                    rows.append(_document(
                        conversation_id=conversation_id,
                        title=title,
                        source_ref=f"conversations/{conversation_id}/{part_path.name}",
                        heading=f"{role.upper()} {timestamp} · chunk {chunk_index}",
                        text=chunk,
                        authority=40 if role == "assistant" else 38,
                        role=f"private_chat_{role}",
                        captured_at=captured_at,
                    ))

    deduped: dict[str, dict[str, Any]] = {}
    for row in rows:
        deduped.setdefault(str(row["document_id"]), row)
    return list(deduped.values())
