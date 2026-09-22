from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

TOKEN = re.compile(r"[a-z0-9_./:-]+", re.I)
HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*$")

def _tokens(value: Any) -> Counter[str]:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True) if not isinstance(value, str) else value
    return Counter(token.casefold() for token in TOKEN.findall(text))

def _cosine(a: Counter[str], b: Counter[str]) -> float:
    common = set(a) & set(b)
    numerator = sum(a[k] * b[k] for k in common)
    da = math.sqrt(sum(v * v for v in a.values()))
    db = math.sqrt(sum(v * v for v in b.values()))
    return numerator / (da * db) if da and db else 0.0

def chunk_markdown(text: str, *, path: str, authority: int, role: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    heading = "(document root)"
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if not body:
            return
        for start in range(0, len(body), 3200):
            part = body[start:start + 3200]
            chunks.append({
                "kind": "document",
                "path": path,
                "heading": heading,
                "role": role,
                "authority": authority,
                "text": part,
            })

    for line in text.splitlines():
        match = HEADING.match(line)
        if match and len(match.group(1)) <= 2:
            flush()
            buffer.clear()
            heading = match.group(2).strip()
        else:
            buffer.append(line)
    flush()
    return chunks

class DocumentStore:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self._vectors = [_tokens({
            "path": row.get("path"),
            "heading": row.get("heading"),
            "role": row.get("role"),
            "text": row.get("text"),
        }) for row in rows]

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "DocumentStore":
        rows: list[dict[str, Any]] = []
        source = Path(path)
        if source.exists():
            for line in source.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    value = json.loads(line)
                    if isinstance(value, dict) and value.get("kind") == "document":
                        rows.append(value)
        return cls(rows)

    def search(self, query: dict[str, Any], *, limit: int = 4) -> list[dict[str, Any]]:
        qv = _tokens(query)
        provider = str(query.get("provider_id") or "").casefold()
        failure = str(query.get("failure_class") or "").casefold()
        status = str(query.get("status") or "").casefold()

        scored = []
        for row, vector in zip(self.rows, self._vectors):
            lexical = _cosine(qv, vector)
            haystack = (
                str(row.get("heading") or "") + "\n" + str(row.get("text") or "")
            ).casefold()
            hay_tokens = set(_tokens(haystack))

            exact = 0.0
            if provider and provider in hay_tokens:
                exact += 0.34
            if failure and failure in haystack:
                exact += 0.28
            if status and status in haystack:
                exact += 0.06

            relevance = (0.62 * lexical) + exact
            if relevance < 0.08:
                continue

            authority = max(0.0, min(1.0, float(row.get("authority") or 0) / 100.0))
            # Authority refines relevant matches; it never makes an irrelevant
            # document relevant by itself.
            score = relevance * (0.90 + (0.10 * authority))
            scored.append((score, relevance, authority, row))

        ranked = sorted(
            scored,
            key=lambda item: (item[0], item[1], item[2]),
            reverse=True,
        )
        return [
            dict(
                row,
                _document_score=round(score, 4),
                _document_relevance=round(relevance, 4),
            )
            for score, relevance, _, row in ranked[:limit]
        ]
