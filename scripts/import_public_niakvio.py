#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
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



def provider_lego_mechanism_tags(root: Path, lego_names: list[str]) -> list[str]:
    """Extract a closed vocabulary of reusable mechanisms from owned Lego.

    No source snippet, host, route, literal identifier or request body survives
    this projection. The tags describe implementation shape only.
    """
    tags: set[str] = set()
    base = (root / "scripts" / "provider_patches").resolve()
    markers = (
        ("sitemap_slug_discovery", lambda s: "sitemap.xml" in s and "slug" in s),
        ("inline_script_parse", lambda s: "<script" in s or "function scripts(" in s),
        ("base64_decode", lambda s: "atob(" in s),
        ("packed_script_unpack", lambda s: "eval(function(p,a,c,k,e,d)" in s or "unpack" in s),
        ("form_post", lambda s: "application/x-www-form-urlencoded" in s and "post" in s),
        ("hls_playlist_validation", lambda s: "#extm3u" in s or ".m3u8" in s),
        ("direct_media_files", lambda s: ".mp4" in s or ".mkv" in s or ".webm" in s),
        ("tmdb_identity", lambda s: "tmdbid" in s or "tmdb_id" in s),
        ("season_episode_identity", lambda s: "season" in s and "episode" in s),
        ("embed_player_traversal", lambda s: "iframe" in s or "embed" in s),
        ("json_response_parse", lambda s: "json.parse" in s or "application/json" in s),
        ("alias_title_matching", lambda s: "alternative_titles" in s or "original_name" in s),
        ("request_header_replay", lambda s: "referer" in s and "user-agent" in s),
        ("terminal_media_crawl", lambda s: "_crawldirectmedia" in s or "terminal(" in s),
    )
    for raw in lego_names[:6]:
        name = Path(str(raw or "")).name.casefold()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,100}\.py", name):
            continue
        path = (base / name).resolve()
        if path.parent != base or not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace").casefold()
        except OSError:
            continue
        for tag, predicate in markers:
            if predicate(source):
                tags.add(tag)
    return sorted(tags)[:16]


def collect_provider_structured_priors(root: Path) -> list[dict[str, Any]]:
    """Project existing NiakVIO provider knowledge into non-authoritative RAG.

    This deliberately excludes hostnames, routes, request bodies and raw Lego
    source. Those values may be stale and current exact execution must always
    outrank historical construction knowledge.
    """
    import re
    data = load_json(root / "automation" / "brain-repair-experience.json", {})
    if not isinstance(data, dict) or data.get("role") != "repair-prior-only":
        return []
    source_sha = str(data.get("sourceSha") or "").strip().casefold()
    if not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        return []
    providers = data.get("providers")
    if not isinstance(providers, dict):
        return []

    def safe_tokens(values: Any, *, limit: int = 12) -> list[str]:
        out = []
        for raw in values or []:
            value = str(raw or "").strip().casefold()
            if re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,79}", value) and value not in out:
                out.append(value)
            if len(out) >= limit:
                break
        return out

    rows: list[dict[str, Any]] = []
    for raw_provider, raw in sorted(providers.items()):
        provider = str(raw_provider or "").strip().casefold().replace("_", "-")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", provider) or not isinstance(raw, dict):
            continue
        strategy = str(raw.get("strategy") or "").strip().casefold().replace("-", "_")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_]{1,79}", strategy):
            strategy = "provider_owned_runtime"
        lego_families = []
        for value in raw.get("providerLegoScripts") or []:
            name = Path(str(value or "")).name.casefold()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,100}\.py", name):
                continue
            stem = name[:-3]
            if stem not in lego_families:
                lego_families.append(stem)
            if len(lego_families) >= 6:
                break
        recipe = {
            "strategy": strategy,
            "lego_families": lego_families,
            "mechanisms": provider_lego_mechanism_tags(
                root, list(raw.get("providerLegoScripts") or [])
            ),
            "route_families": safe_tokens(raw.get("routeFamilies"), limit=8),
            "recipe_roles": safe_tokens(raw.get("recipeRoles"), limit=8),
            "recipe_methods": safe_tokens(raw.get("recipeMethods"), limit=6),
            "recipe_responses": safe_tokens(raw.get("recipeResponses"), limit=6),
            "media_types": safe_tokens(raw.get("mediaTypes"), limit=4),
            "has_api_recipe": raw.get("hasApiRecipe") is True,
            "has_provider_value_plan": raw.get("hasProviderValuePlan") is True,
            "has_search_request_plan": raw.get("hasSearchRequestPlan") is True,
        }
        if not any((
            recipe["lego_families"], recipe["route_families"],
            recipe["recipe_roles"], recipe["recipe_methods"],
            recipe["has_api_recipe"], recipe["has_provider_value_plan"],
            recipe["has_search_request_plan"],
        )):
            continue
        rows.append({
            "experience_id": f"provider-knowledge:{source_sha[:12]}:{provider}",
            "source": "provider-structured-knowledge",
            "providers": [provider],
            "failure_class": "provider_structured_recipe_prior",
            "symptom_families": ["historical_provider_construction"],
            "signals": ["provider_owned_lego_or_recipe"],
            "strategy": strategy,
            "result": "provider_recipe_prior",
            "provider_recipe": recipe,
            "provider_source_sha": source_sha,
            "proof_authority": False,
            "prior_only": True,
            "current_execution_proof": False,
            "current_network_proof": False,
        })
    return rows

def collect_hosted_replay_negatives(root: Path) -> list[dict[str, Any]]:
    """Retain executed *negative* Brain experience, never raw provider edits.

    Hosted reports are untrusted archival observations. Only same-run,
    source-pinned and executed+materialized reports become negative priors.
    They do not grant proof, provider authority, or transfer their source code.
    """
    import re
    directory = root / "automation" / "hosted-repair-evidence"
    if not directory.is_dir():
        return []
    rows = []
    for path in sorted(directory.glob("*.json"))[-500:]:
        if not re.fullmatch(r"[0-9]{8,14}\.json", path.name):
            continue
        report = load_json(path, {})
        if not isinstance(report, dict) or report.get("publicationAuthority") is not False:
            continue
        # Archived reports are untrusted inputs. Reject malformed counters
        # instead of letting one historical file abort all subsequent imports.
        accepted_count = report.get("acceptedProviderCount")
        if type(accepted_count) is not int or accepted_count != 0:
            continue
        provider = str(report.get("provider") or "").strip().casefold()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", provider):
            continue
        source_sha = str(report.get("sourceNiakvioSha") or "").lower()
        brain_sha = str(report.get("sourceBrainLlmSha") or "").lower()
        if not re.fullmatch(r"[a-f0-9]{40}", source_sha) or not re.fullmatch(r"[a-f0-9]{40}", brain_sha):
            continue
        exact = load_json(directory / (path.stem + "-evaluation.json"), {})
        if not isinstance(exact, dict) or exact.get("currentSha") != source_sha:
            continue
        evidence = [
            item for item in (exact.get("rows") or [])
            if isinstance(item, dict)
            and item.get("provider") == provider
            and item.get("accepted") is False
            and item.get("executionObserved") is True
            and item.get("materializedMutationObserved") is True
            and str(item.get("reason") or "") in {
                "decoded_repair_no_new_fixture_control",
                "decoded_repair_no_improvement",
                "no_new_decoded_media",
            }
        ]
        if not evidence:
            continue
        for item in evidence[:1]:
            reason = str(item["reason"])
            mechanism = [
                str(value.get("family") or "").strip().casefold()
                for value in (item.get("mutationSummary") or [])[:2]
                if isinstance(value, dict)
                and re.fullmatch(r"[a-z0-9_-]{2,80}", str(value.get("family") or "").strip().casefold())
            ]
            fingerprint = str(item.get("mutationFingerprint") or "").lower()
            if not re.fullmatch(r"[a-f0-9]{64}", fingerprint):
                continue
            rows.append({
                "experience_id": f"hosted-negative:{path.stem}:{fingerprint[:16]}",
                "source": "hosted-executed-negative",
                "providers": [provider],
                "failure_class": "executed_provider_no_improvement",
                "symptom_families": ["materialized_no_decoded_gain"],
                "signals": ["exact_source_replay", "materialized_execution",
                            "zero_new_decoded_fixture_control"],
                "strategy": mechanism[0] if mechanism else "discard_rejected_mutation",
                "avoid": ["repeat_same_mutation_fingerprint"],
                "lesson": "The exact mutation executed but added no independently decoded playable fixture. Do not treat this provider/plan as a validated repair.",
                "result": "rejected_executed_no_improvement",
                "provider_source_sha": source_sha,
                "brain_source_sha": brain_sha,
                "mutation_fingerprint": fingerprint,
                "proof_authority": False,
                "prior_only": True,
            })
    return rows[-24:]


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

    for row in [
        *collect_provider_structured_priors(root),
        *collect_local_force(root),
        *collect_hosted_replay_negatives(root),
    ]:
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
