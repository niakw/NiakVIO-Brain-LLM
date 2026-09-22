from __future__ import annotations

from typing import Any

def classify_learning_record(row: dict[str, Any]) -> dict[str, Any]:
    result = str(row.get("result") or "inconclusive")
    layer = str(row.get("target_layer") or "unknown")
    verified_lanes = [str(x) for x in row.get("verified_lanes") or []]
    authority = str(row.get("verification_authority") or "").strip().casefold()

    if result == "validated":
        verified_training_truth = layer != "unknown" and authority == "niakvio"
        return {
            "rag_bucket": "positive",
            "sft_candidate": verified_training_truth,
            "promotion_reason": (
                "verified NiakVIO repair outcome"
                if verified_training_truth
                else "positive memory lacks current NiakVIO verification authority"
            ),
            "weight": 1.0 + min(len(verified_lanes), 3) * 0.1,
        }

    if result == "failed":
        return {
            "rag_bucket": "negative",
            "sft_candidate": False,
            "promotion_reason": "failed hypothesis is useful as negative memory only",
            "weight": 0.8,
        }

    if result == "abstained":
        return {
            "rag_bucket": "safety",
            "sft_candidate": False,
            "promotion_reason": "abstention remains safety memory until separately validated",
            "weight": 0.7,
        }

    return {
        "rag_bucket": "transient",
        "sft_candidate": False,
        "promotion_reason": "inconclusive outcome is not durable training truth",
        "weight": 0.2,
    }
