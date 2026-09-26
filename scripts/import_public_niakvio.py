#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

def normalize_case(case: dict[str, Any], *, source: str) -> dict[str, Any] | None:
    failure = str(case.get("failureClass") or "").strip()
    solution = str(case.get("solutionClass") or "").strip()
    if not failure or not solution:
        return None
    return {
        "experience_id": str(case.get("id") or ""),
        "source": source,
        "providers": [str(x) for x in case.get("providers") or []][:16],
        "failure_class": failure,
        "symptom_families": [str(x) for x in case.get("symptomFamilies") or []][:16],
        "signals": [str(x) for x in case.get("transferableSignals") or []][:24],
        "strategy": solution,
        "avoid": [str(x) for x in case.get("avoid") or []][:16],
        "lesson": str(case.get("lesson") or ""),
        "result": "validated",
        "proof_authority": False,
    }

def collect_local_force(root: Path) -> list[dict[str, Any]]:
    directory = root / "automation" / "local-force-results"
    corpora = sorted(directory.glob("*consolidated-corpus.json")) if directory.is_dir() else []
    if not corpora:
        return []
    corpus = load_json(corpora[-1], {})
    if not isinstance(corpus, dict) or corpus.get("role") != "local-force-consolidated-corpus-index":
        return []

    guidance_rows: dict[str, dict[str, Any]] = {}
    for raw_path in corpus.get("evidenceFiles") or []:
        path = root / str(raw_path)
        if not path.name.endswith("-winning-guidance.json"):
            continue
        guidance = load_json(path, {})
        if (
            not isinstance(guidance, dict)
            or guidance.get("publicationAuthority") is not False
            or guidance.get("directMutationAuthority") is not False
            or guidance.get("proofAuthority") is not False
            or guidance.get("rawMutationContentRetained") is not False
        ):
            continue
        for raw in guidance.get("rows") or []:
            if not isinstance(raw, dict):
                continue
            provider = str(raw.get("providerId") or "").strip().casefold().replace("_", "-")
            if provider:
                guidance_rows[provider] = raw

    source_sha = str((corpus.get("providerByteEquivalence") or {}).get("headSha") or "")
    rows: list[dict[str, Any]] = []

    def append(provider: str, *, outcome: str, strategy: str, signals: list[str], lesson: str) -> None:
        provider = str(provider or "").strip().casefold().replace("_", "-")
        if not provider:
            return
        rows.append({
            "experience_id": f"local-force:{source_sha[:12]}:{outcome}:{provider}",
            "source": "local-force-consolidated",
            "providers": [provider],
            "failure_class": f"local_force_{outcome}",
            "symptom_families": [outcome],
            "signals": signals[:24],
            "strategy": strategy,
            "avoid": ["treat_local_force_as_production_proof"],
            "lesson": lesson,
            "result": outcome,
            "proof_authority": False,
            "prior_only": True,
        })

    for provider in corpus.get("noProgressSampled") or []:
        append(
            provider,
            outcome="no_progress",
            strategy="evolve_beyond_sampled_profiles",
            signals=["sampled_profiles_executed", "no_quick_progress", "deep_acceptance_absent"],
            lesson="Sampled local FORCE profiles produced no useful progression; prefer a materially different hypothesis family.",
        )
    for provider in corpus.get("progressWithoutDeepAcceptance") or []:
        append(
            provider,
            outcome="progress_without_deep_acceptance",
            strategy="continue_with_evolved_strategy_after_partial_progress",
            signals=["quick_progress_observed", "deep_acceptance_absent"],
            lesson="The provider can make bounded runtime progress, but the sampled strategy did not reach accepted Deep proof.",
        )
    for provider in corpus.get("knownDeepBaselineHealthy") or []:
        append(
            provider,
            outcome="baseline_healthy",
            strategy="revalidate_baseline_before_mutation",
            signals=["deep_baseline_healthy", "mutation_causality_unproven"],
            lesson="Deep baseline health was observed; do not attribute health to a mutation without a differential current-byte proof.",
        )
    for provider in corpus.get("knownLocalDeepCandidates") or []:
        provider_id = str(provider or "").strip().casefold().replace("_", "-")
        guidance = guidance_rows.get(provider_id) or {}
        strategy = str(guidance.get("strategy") or "revalidate_ambiguous_local_candidate")
        fingerprint = str(guidance.get("experimentFingerprint") or "")
        signals = ["local_deep_candidate", "baseline_coincident", "requires_targeted_force_revalidation"]
        if fingerprint:
            signals.append("experiment_fingerprint:" + fingerprint[:16])
        append(
            provider_id,
            outcome="ambiguous_deep_candidate",
            strategy=strategy,
            signals=signals,
            lesson="A local Deep candidate coincided with a healthy baseline; revalidate the exact hypothesis before granting causal credit.",
        )
    return rows

def collect(root: Path) -> list[dict[str, Any]]:
    sources = [
        ("brain-repair-experience", root / "automation" / "brain-repair-experience.json"),
        ("historical-seed", root / "automation" / "brain-historical-experience-seed.json"),
    ]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source_name, path in sources:
        data = load_json(path, {})
        for case in data.get("historicalCases") or data.get("cases") or []:
            if not isinstance(case, dict):
                continue
            row = normalize_case(case, source=source_name)
            if not row:
                continue
            identity = row["experience_id"] or json.dumps(
                [row["failure_class"], row["strategy"], row["providers"]],
                sort_keys=True,
            )
            if identity in seen:
                continue
            seen.add(identity)
            rows.append(row)

    for row in collect_local_force(root):
        identity = str(row.get("experience_id") or "")
        if not identity or identity in seen:
            continue
        seen.add(identity)
        rows.append(row)

    return rows

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = collect(Path(args.niakvio_root))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )
    print(json.dumps({
        "experiences": len(rows),
        "failure_classes": len({row["failure_class"] for row in rows}),
        "strategies": len({row["strategy"] for row in rows}),
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
