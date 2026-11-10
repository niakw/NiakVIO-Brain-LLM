#!/usr/bin/env python3
"""Read-only real-source challenger: no patch writes and no publication."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.mutation_guard import validate_mutations
from niakvio_brain_llm.niakvio_adapter import request_from_checkout
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.policy import build_mutation_policy
from niakvio_brain_llm.priors import build_causal_prior
from niakvio_brain_llm.retrieval import ExperienceStore
from scripts.publish_niakvio_force_mutations import validate_current_provider_bloc_anchors

TOPOLOGIES = {
    "4khdhub": "download_html",
    "allanime": "anime_api_player",
    "moviesmod": "html_player",
    "yflix": "film_series_api",
}


def classify_proposal(request, proposal, *, niakvio_root: Path | None = None) -> dict:
    """No provider source or route/URL is ever present in the report."""
    prior = build_causal_prior(request, [])
    policy = build_mutation_policy(request, prior)
    mutations = list(proposal.mutations)
    allowed = set(policy.get("allowed_scopes") or ())
    policy_ok = (not mutations or (
        policy.get("allow_mutations") is True and all(
            isinstance(m, dict) and m.get("scope") in allowed for m in mutations
        )
    ))
    if policy.get("force_abstain") and not proposal.abstain:
        policy_ok = False
    syntax_valid = False
    if mutations and policy_ok:
        try:
            validate_mutations(request.provider_id, mutations)
            syntax_valid = True
        except Exception:
            pass
    current_anchor_valid = None
    if niakvio_root is not None:
        current_anchor_valid = False
        if syntax_valid:
            try:
                current_anchor_valid = validate_current_provider_bloc_anchors(
                    niakvio_root, request.provider_id, mutations
                )
            except (OSError, ValueError):
                pass
    canonical_eligible = bool(
        syntax_valid and policy_ok and not proposal.abstain
        and current_anchor_valid is True
    )
    return {
        "currentByteAnchorValid": current_anchor_valid,
        "canonicalApplyEligible": canonical_eligible,
        "schemaValid": True,
        "targetLayer": proposal.target_layer,
        "strategyMatchesPrior": (not prior.get("strategy_prior")
                                 or proposal.strategy == prior["strategy_prior"]),
        "abstained": bool(proposal.abstain),
        "mutationCount": len(mutations),
        "mutationPolicyCompliant": policy_ok,
        "mutationDslValid": syntax_valid,
        "mutationAllowed": bool(policy.get("allow_mutations")),
        "proposedScopeKinds": sorted({str(v.get("scope") or "") for v in mutations if isinstance(v, dict)}),
        "materialized": False,
        "executed": False,
        "validated": False,
        "published": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--niakvio-root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--endpoint", default="http://127.0.0.1:8080")
    ap.add_argument("--model", default="qwen35-9b")
    ap.add_argument("--provider", action="append", default=[],
                    help="Exact family ID(s) for first live sandbox proof")
    ap.add_argument("--raw-candidates", default="",
                    help="Runner-local only, never upload this file as an artifact")
    ap.add_argument("--max-tokens", type=int, default=768)
    ap.add_argument("--timeout-seconds", type=int, default=420)
    args = ap.parse_args()
    if not 128 <= args.max_tokens <= 2048 or not 30 <= args.timeout_seconds <= 900:
        ap.error("outside bounded inference limits")
    selected = list(dict.fromkeys(args.provider)) if args.provider else list(TOPOLOGIES)
    if not selected or any(value not in TOPOLOGIES for value in selected):
        ap.error("provider must belong to the four evidence-based source families")
    root = Path(args.niakvio_root).resolve()
    sha = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    assert len(sha) == 40
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    backend = LocalOpenAICompatibleBackend(
        base_url=args.endpoint, model=args.model,
        timeout_seconds=args.timeout_seconds, max_tokens=args.max_tokens,
        temperature=0.0)
    planner = BrainPlanner(backend, ExperienceStore([]), DocumentStore([]))
    rows = []
    full_candidates = []
    for provider_id in selected:
        family = TOPOLOGIES[provider_id]
        row = {"provider": provider_id, "family": family}
        try:
            request = request_from_checkout(root, provider_id)
            if request.provider_id.casefold().replace("_", "-") != provider_id:
                raise ValueError("checkout provider identity mismatch")
            # The proposal has no side effects. No output includes prompt,
            # evidence values, edits, media, URLs, headers or tokens.
            with contextlib.redirect_stdout(sys.stderr):
                proposal = planner.propose_raw(request)
            row.update(classify_proposal(request, proposal, niakvio_root=root))
            if (args.raw_candidates and row.get("canonicalApplyEligible")
                    and row.get("mutationPolicyCompliant")
                    and not row.get("abstained") and proposal.confidence >= 0.80):
                full_candidates.append({
                    "ok": True, "provider": provider_id,
                    "proposal": proposal.to_dict(),
                })
                # This file is a transient sandbox input only. A public
                # artifact MUST NOT include unreviewed model-generated source,
                # upstream response bodies or route/credential text.
                destination = Path(args.raw_candidates)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(
                    "".join(json.dumps(item) + "\n" for item in full_candidates),
                    encoding="utf-8",
                )
                destination.chmod(0o600)
        except Exception as exc:
            row.update({"schemaValid": False, "errorType": type(exc).__name__,
                        "materialized": False, "executed": False,
                        "validated": False, "published": False})
        rows.append(row)
        report = {
            "schemaVersion": 1, "model": args.model,
            "sourceRepository": "niakw/NiakVIO",
            "sourceSha": sha,
            "families": len(selected),
            "processed": len(rows),
            "validCompletions": sum(bool(x.get("schemaValid")) for x in rows),
            "policyValidMutationProposals": sum(bool(x.get("mutationDslValid")) for x in rows),
            "repairAcceptanceProof": False,
            "mode": "read_only_public_current_source_diagnostic",
            "results": rows,
        }
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(output)
        print("FIELD_BRAIN_SOURCE_CHALLENGER provider=" + provider_id
              + " model_json=" + str(row.get("schemaValid") is True).lower()
              + " admissible_mutation=" + str(row.get("canonicalApplyEligible") is True).lower()
              + " publish=false", file=sys.stderr, flush=True)
    return 0 if len(rows) == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
