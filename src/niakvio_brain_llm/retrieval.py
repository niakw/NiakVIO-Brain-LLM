from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

TOKEN = re.compile(r"[a-z0-9_./:-]+", re.I)

def _tokens(value: Any) -> Counter[str]:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True) if not isinstance(value, str) else value
    return Counter(token.casefold() for token in TOKEN.findall(text))

def _cosine(a: Counter[str], b: Counter[str]) -> float:
    common = set(a) & set(b)
    numerator = sum(a[k] * b[k] for k in common)
    da = math.sqrt(sum(v * v for v in a.values()))
    db = math.sqrt(sum(v * v for v in b.values()))
    return numerator / (da * db) if da and db else 0.0

class ExperienceStore:
    """Dependency-free RAG baseline; replaceable by embeddings later."""

    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self._vectors = [_tokens(row) for row in rows]

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "ExperienceStore":
        rows: list[dict[str, Any]] = []
        source = Path(path)
        if source.exists():
            for line in source.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    value = json.loads(line)
                    if isinstance(value, dict):
                        rows.append(value)
        return cls(rows)

    def search(self, query: dict[str, Any], *, limit: int = 6) -> list[dict[str, Any]]:
        qv = _tokens(query)
        ranked = sorted(
            ((_cosine(qv, vector), row) for row, vector in zip(self.rows, self._vectors)),
            key=lambda item: item[0],
            reverse=True,
        )
        return [dict(row, _retrieval_score=round(score, 4)) for score, row in ranked[:limit] if score > 0]
