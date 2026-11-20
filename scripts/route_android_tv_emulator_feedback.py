#!/usr/bin/env python3
"""Route a completed official Android TV emulator run through the Brain.

Called by NiakVIO's completed-native-run feedback workflow. Never executes
models, providers, JavaScript, or emits mutation/publication decisions. Only
source-pinned diagnostic plans are allowed through this bridge.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

from niakvio_brain_llm.niakvio_adapter import request_from_checkout
from niakvio_brain_llm.routing import route_request
from niakvio_brain_llm.native_origin_experiments import native_blocking_origin_priority_experiment
from niakvio_brain_llm.native_hls_receipt_experiments import native_hls_root_receipt_experiment

_SHA40 = re.compile(r"[0-9a-f]{40}")
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,95}")
_FIXTURE = re.compile(r"[a-z0-9][a-z0-9-]{0,95}")
_ALLOWED_MODES = {"probe", "skip", "deterministic", "deterministic_advisor",
                  "llm_diagnose", "llm_repair"}
_ALLOWED_SCOPES = {"manifest.json", "vf/manifest.json"}


def build(
    ledger: dict[str, Any],
    source_sha: str,
    run_id: str,
    *,
    checkout: str | Path,
    request_builder: Callable[..., Any] = request_from_checkout,
    router: Callable[..., Any] = route_request,
) -> dict[str, Any]:
    if not _SHA40.fullmatch(source_sha) or not run_id.isdigit():
        raise ValueError("exact NiakVIO SHA and numeric native run required")
    safe = (isinstance(ledger, dict)
            and ledger.get("schemaVersion") == 1
            and ledger.get("authority") == "official-android-tv-emulator-diagnostic-only"
            and ledger.get("primaryClient") == "tv"
            and all(ledger.get(key) is False for key in (
                "proofAuthority", "publicationAuthority",
                "nativePlaybackAuthority", "providerMutationAuthority")))
    if not safe:
        raise ValueError("untrusted or unauthorized official TV ledger")

    candidates: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in (ledger.get("rows") or [])[:1400]:
        if not isinstance(row, dict):
            continue
        provider = str(row.get("provider") or "")
        fixture = str(row.get("fixture") or "")
        key = (provider, fixture)
        if (
            not _ID.fullmatch(provider)
            or not _FIXTURE.fullmatch(fixture)
            or key in seen
            or row.get("sourceNiakvioSha") != source_sha
            or str(row.get("nativeRunId") or "") != run_id
            or row.get("manifestScope") not in _ALLOWED_SCOPES
            or any(row.get(flag) is not False for flag in (
                "proofAuthority", "publicationAuthority",
                "nativePlaybackAuthority", "providerMutationAuthority"))
        ):
            continue
        seen.add(key)
        candidates.append(key)
        if len(candidates) >= 4:
            break

    routes: list[dict[str, Any]] = []
    for provider, fixture in candidates:
        request = request_builder(checkout, provider)
        request.advisor_only = True
        observed = any(
            isinstance(obs, dict)
            and obs.get("source") == "official-android-tv-emulator"
            and isinstance(obs.get("value"), dict)
            and obs["value"].get("sourceRunId") == run_id
            and obs["value"].get("fixture") == fixture
            and obs["value"].get("historicalOnly") is True
            and obs["value"].get("providerMutationAuthority") is False
            for obs in (request.observations or [])
        )
        if not observed:
            # Mismatched manifest, digest or disabled provider: no route.
            continue
        decision = router(request)
        candidate_experiment = native_blocking_origin_priority_experiment(request)
        followup_core_experiment = native_hls_root_receipt_experiment(request)
        mode = str(getattr(decision, "mode", ""))
        if mode not in _ALLOWED_MODES:
            mode = "probe"
        layer = str(getattr(decision, "target_layer", ""))
        layer = layer if _ID.fullmatch(layer) else "unknown"
        strategy = str(getattr(decision, "strategy", ""))
        strategy = strategy if _ID.fullmatch(strategy.replace("_", "-")) else ""
        routes.append({
            "provider": provider,
            "fixture": fixture,
            "mode": mode,
            "targetLayer": layer,
            "strategy": strategy[:95],
            "nextStep": (
                "source_pinned_brain_causal_diagnosis" if mode in {"llm_diagnose", "llm_repair"}
                else "official_tv_discriminating_probe" if mode == "probe"
                else "recheck_tv_media_before_any_promotion"
            ),
            "modelExecuted": False,
            "providerMutationAuthority": False,
            "publicationAuthority": False,
            "nativePlaybackAuthority": False,
            **({"candidateExperiment": candidate_experiment} if candidate_experiment else {}),
            **({"followupCoreExperiment": followup_core_experiment} if followup_core_experiment else {}),
        })
    return {
        "schemaVersion": 1,
        "authority": "android-tv-brain-route-plan-only",
        "sourceNiakvioSha": source_sha,
        "nativeRunId": run_id,
        "primaryClient": "tv",
        "providerCount": len({row["provider"] for row in routes}),
        "routeCount": len(routes),
        "routes": routes,
        "modelExecuted": False,
        "proofAuthority": False,
        "publicationAuthority": False,
        "nativePlaybackAuthority": False,
        "providerMutationAuthority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    source = a.niakvio_root / "automation/brain-android-tv-emulator-history.json"
    ledger = json.loads(source.read_text("utf-8"))
    plan = build(ledger, a.source_sha, a.run_id, checkout=a.niakvio_root)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FIELD_BRAIN_ANDROID_TV_ROUTE "
          f"run={a.run_id} providers={plan['providerCount']} "
          f"routes={plan['routeCount']} model_executed=false "
          "provider_mutation_authority=false publication_authority=false")
    for route in plan["routes"]:
        print("FIELD_BRAIN_ANDROID_TV_NEXT "
              f"provider={route['provider']} mode={route['mode']} "
              f"layer={route['targetLayer']} action={route['nextStep']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
