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

def _set(value: Any) -> set[str]:
    if isinstance(value, list):
        return {str(item).strip().casefold() for item in value if str(item).strip()}
    if value is None:
        return set()
    text = str(value).strip().casefold()
    return {text} if text else set()

def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0

def _field_score(query: dict[str, Any], row: dict[str, Any]) -> float:
    """NiakVIO-aware structural similarity layered over lexical similarity."""
    score = 0.0

    q_failure = str(query.get("failure_class") or query.get("failureClass") or "").casefold()
    r_failure = str(row.get("failure_class") or row.get("failureClass") or "").casefold()
    if q_failure and r_failure and q_failure == r_failure:
        score += 0.45

    score += 0.20 * _jaccard(
        _set(query.get("symptom_families") or query.get("symptomFamilies")),
        _set(row.get("symptom_families") or row.get("symptomFamilies")),
    )
    score += 0.15 * _jaccard(
        _set(query.get("signals") or query.get("transferableSignals")),
        _set(row.get("signals") or row.get("transferableSignals")),
    )
    score += 0.08 * _jaccard(
        _set(query.get("supported_types") or query.get("supportedTypes")),
        _set(row.get("supported_types") or row.get("supportedTypes")),
    )

    q_provider = str(query.get("provider_id") or "").casefold()
    providers = _set(row.get("providers"))
    if q_provider and q_provider in providers:
        score += 0.12

    return score

class ExperienceStore:
    """Dependency-free, NiakVIO-aware RAG baseline.

    Structural fields dominate ranking; lexical cosine breaks ties and still
    helps with unseen wording. Embeddings can be added later without changing
    the planner contract.
    """

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
        scored = []
        for row, vector in zip(self.rows, self._vectors):
            lexical = _cosine(qv, vector)
            structural = _field_score(query, row)
            score = structural + (0.18 * lexical)
            scored.append((score, structural, lexical, row))

        ranked = sorted(scored, key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [
            dict(
                row,
                _retrieval_score=round(score, 4),
                _structural_score=round(structural, 4),
                _lexical_score=round(lexical, 4),
            )
            for score, structural, lexical, row in ranked[:limit]
            if score > 0
        ]
