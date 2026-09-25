from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

TARGET_LAYERS = {"provider", "core", "harness", "network", "unknown"}

@dataclass(slots=True)
class RepairRequest:
    provider_id: str
    failure_class: str
    status: str = ""
    supported_types: list[str] = field(default_factory=list)
    census_prior: dict[str, Any] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)
    provider_context: dict[str, Any] = field(default_factory=dict)
    allowed_mutations: list[str] = field(default_factory=lambda: ["provider_data", "provider_patch", "provider_js"])
    forbidden_mutations: list[str] = field(default_factory=lambda: ["core", "provider_base"])
    max_hypotheses: int = 3
    advisor_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(slots=True)
class RepairProposal:
    provider_id: str
    diagnosis: str
    strategy: str
    confidence: float
    target_layer: str = "unknown"
    evidence: list[str] = field(default_factory=list)
    mutations: list[dict[str, Any]] = field(default_factory=list)
    experiment: dict[str, Any] = field(default_factory=dict)
    tests: list[str] = field(default_factory=list)
    abstain: bool = False
    abstain_reason: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RepairProposal":
        confidence = max(0.0, min(1.0, float(value.get("confidence", 0.0))))
        target_layer = str(value.get("target_layer") or "unknown").strip().casefold()
        if target_layer not in TARGET_LAYERS:
            target_layer = "unknown"
        return cls(
            provider_id=str(value.get("provider_id") or ""),
            diagnosis=str(value.get("diagnosis") or ""),
            strategy=str(value.get("strategy") or ""),
            confidence=confidence,
            target_layer=target_layer,
            evidence=[str(x) for x in value.get("evidence") or []][:12],
            mutations=[x for x in value.get("mutations") or [] if isinstance(x, dict)][:8],
            experiment=dict(value.get("experiment") or {}) if isinstance(value.get("experiment"), dict) else {},
            tests=[str(x) for x in value.get("tests") or []][:12],
            abstain=bool(value.get("abstain", False)),
            abstain_reason=str(value.get("abstain_reason") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
