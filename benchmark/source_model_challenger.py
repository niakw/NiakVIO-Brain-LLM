#!/usr/bin/env python3
"""Read-only real-source challenger: no patch writes and no publication."""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend, HostedResponsesBackend
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.force_scope_order import select_force_scopes
from niakvio_brain_llm.live_context_ingest import attach_live_runtime_evidence
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


def safe_abstention_category(reason: str) -> str:
    """Never expose model narrative, URLs, secrets or source bytes in diagnostics."""
    cleaned = re.sub(r"[^a-z]+", " ", str(reason or "").casefold())
    if any(token in cleaned for token in ("evidence", "network", "response", "route")):
        return "missing_current_causal_evidence"
    if any(token in cleaned for token in ("unit", "syntax", "function", "snippet")):
        return "no_safe_edit_unit"
    if any(token in cleaned for token in ("policy", "unsafe", "permission")):
        return "policy_or_safety"
    return "other_or_unspecified"


def production_first_scope_request(request):
    """Use the exact production FORCE scope ordering, bounded to one CPU candidate."""
    scopes = select_force_scopes(request)
    if not scopes:
        raise ValueError("no evidence-backed FORCE mutation scope")
    scoped = copy.deepcopy(request)
    scoped.allowed_mutations = [scopes[0]]
    return scoped, scopes[0]


def load_challenger_rag(
    experience_path: Path | None, document_path: Path | None, *, require: bool
) -> tuple[ExperienceStore, DocumentStore]:
    """Production-compatible public RAG; never silently use empty stores in FORCE."""
    if require and (experience_path is None or document_path is None):
        raise ValueError("canonical FORCE needs both explicit public experience and document corpora")
    for path in (experience_path, document_path):
        if path is not None and (not path.is_file() or not path.stat().st_size):
            raise ValueError("missing or empty public RAG corpus")
    experience = (ExperienceStore.from_jsonl_many([experience_path])
                  if experience_path else ExperienceStore([]))
    documents = (DocumentStore.from_jsonl_many([document_path])
                 if document_path else DocumentStore([]))
    if require and (not experience.rows or not documents.rows):
        raise ValueError("canonical FORCE public RAG corpus has no usable records")
    return experience, documents


def classify_proposal(
    request, proposal, *, niakvio_root: Path | None = None,
    experience_store: ExperienceStore | None = None,
) -> dict:
    """No provider source or route/URL is ever present in the report."""
    prior = build_causal_prior(
        request,
        experience_store.search(request.to_dict(), limit=6)
        if experience_store is not None else [],
    )
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
            registered = {
                str(path).strip()
                for path in (request.provider_context or {}).get("registered_patch_scripts") or []
                if str(path).strip().startswith("scripts/provider_patches/")
            }
            validate_mutations(
                request.provider_id, mutations, allowed_patch_paths=registered
            )
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
    ap.add_argument("--experience", type=Path, default=None,
                    help="Production-compatible public experience JSONL (required in FORCE)")
    ap.add_argument("--documents", type=Path, default=None,
                    help="Production-compatible public documents JSONL (required in FORCE)")
    ap.add_argument("--live-evidence", type=Path, default=None,
                    help="Source-SHA-bound execution preflight before any model synthesis")
    ap.add_argument("--output", required=True)
    ap.add_argument("--endpoint", default="http://127.0.0.1:8080")
    ap.add_argument("--backend", choices=("local", "hosted"), default="local")
    ap.add_argument("--model", default="qwen35-9b")
    ap.add_argument("--provider", action="append", default=[],
                    help="Exact family ID(s) for first live sandbox proof")
    ap.add_argument("--canonical-force", action="store_true",
                    help="Use the real Brain FORCE planner, grammar and exact edit-unit converter")
    ap.add_argument("--model-only-force", action="store_true",
                    help="Read-only test: preserve FORCE grammar but skip deterministic short-circuit")
    ap.add_argument("--raw-candidates", default="",
                    help="Runner-local only, never upload this file as an artifact")
    ap.add_argument("--max-tokens", type=int, default=768)
    ap.add_argument("--timeout-seconds", type=int, default=420)
    args = ap.parse_args()
    if args.model_only_force and not args.canonical_force:
        ap.error("--model-only-force requires --canonical-force")
    if args.backend == "hosted" and not (args.canonical_force and args.model_only_force):
        ap.error("hosted challenger must use constrained model-only FORCE")
    if not 128 <= args.max_tokens <= 2048 or not 30 <= args.timeout_seconds <= 900:
        ap.error("outside bounded inference limits")
    selected = list(dict.fromkeys(args.provider)) if args.provider else list(TOPOLOGIES)
    if args.backend == "hosted" and len(selected) != 1:
        ap.error("hosted source challenger allows exactly one requested provider")
    if not selected or any(value not in TOPOLOGIES for value in selected):
        ap.error("provider must belong to the four evidence-based source families")
    root = Path(args.niakvio_root).resolve()
    sha = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    assert len(sha) == 40
    live_context = None
    if args.live_evidence is not None:
        live_context = json.loads(args.live_evidence.read_text(encoding="utf-8"))
        if (not isinstance(live_context, dict)
                or live_context.get("sourceSha") != sha
                or live_context.get("provider") not in selected
                or len(selected) != 1
                or live_context.get("fixture_selection_complete") is not True):
            ap.error("current execution evidence must match exact SHA and complete provider fixtures")
    if args.canonical_force and live_context is None:
        ap.error("canonical FORCE source challenger requires current execution evidence")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    backend = (
        HostedResponsesBackend.from_environment(
            model=args.model, timeout_seconds=min(args.timeout_seconds, 300),
            max_tokens=max(1024, args.max_tokens), reasoning_effort="medium",
        )
        if args.backend == "hosted"
        else LocalOpenAICompatibleBackend(
            base_url=args.endpoint, model=args.model,
            timeout_seconds=args.timeout_seconds, max_tokens=args.max_tokens,
            temperature=0.0,
        )
    )
    experience_store, document_store = load_challenger_rag(
        args.experience, args.documents, require=args.canonical_force,
    )
    planner = BrainPlanner(backend, experience_store, document_store)
    rows = []
    full_candidates = []
    for provider_id in selected:
        family = TOPOLOGIES[provider_id]
        row = {"provider": provider_id, "family": family}
        try:
            request = request_from_checkout(root, provider_id)
            if request.provider_id.casefold().replace("_", "-") != provider_id:
                raise ValueError("checkout provider identity mismatch")
            if live_context is not None:
                current_live = attach_live_runtime_evidence(
                    request, live_context, source_sha=sha,
                    explicit_providers=[provider_id], repair_mode=True,
                )
                row["liveNetworkObservations"] = current_live["network_count"]
                row["liveFixtureObservations"] = current_live["fixture_count"]
                row["liveActiveFunctionCount"] = current_live["active_function_count"]
            if args.canonical_force:
                request, chosen_scope = production_first_scope_request(request)
                row["selectedScope"] = chosen_scope
            # The proposal has no side effects. No output includes prompt,
            # evidence values, edits, media, URLs, headers or tokens.
            with contextlib.redirect_stdout(sys.stderr):
                proposal = (
                    planner.plan(
                        request, compact_force=True,
                        allow_deterministic_force=not args.model_only_force,
                    )
                    if args.canonical_force else planner.propose_raw(request)
                )
            row["generationMode"] = (
                "canonical_model_force" if args.model_only_force else
                "canonical_force" if args.canonical_force else "raw_model_probe"
            )
            row.update(classify_proposal(
                request, proposal, niakvio_root=root,
                experience_store=experience_store,
            ))
            row["abstentionCategory"] = (
                safe_abstention_category(getattr(proposal, "abstain_reason", ""))
                if proposal.abstain else None
            )
            row["retrievedExperienceCount"] = len(
                experience_store.search(request.to_dict(), limit=6)
            )
            row["retrievedDocumentCount"] = len(
                document_store.search(request.to_dict(), limit=4)
            )
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
            "backend": args.backend,
            "publicExperienceRecords": len(experience_store.rows),
            "publicDocumentChunks": len(document_store.rows),
            "sourceRepository": "niakw/NiakVIO",
            "sourceSha": sha,
            "families": len(selected),
            "processed": len(rows),
            "validCompletions": sum(bool(x.get("schemaValid")) for x in rows),
            "policyValidMutationProposals": sum(bool(x.get("mutationDslValid")) for x in rows),
            "repairAcceptanceProof": False,
            "mode": "read_only_public_current_source_diagnostic",
            "generationMode": (
                "canonical_model_force" if args.model_only_force else
                "canonical_force" if args.canonical_force else "raw_model_probe"
            ),
            "results": rows,
        }
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(output)
        print("FIELD_BRAIN_SOURCE_CHALLENGER provider=" + provider_id
              + " model_json=" + str(row.get("schemaValid") is True).lower()
              + " admissible_mutation=" + str(row.get("canonicalApplyEligible") is True).lower()
              + " mode=" + str(row.get("generationMode") or "unknown")
              + " abstained=" + str(row.get("abstained") is True).lower()
              + " scope=" + str(row.get("selectedScope") or "all")
              + " mutation_count=" + str(row.get("mutationCount") or 0)
              + " abstention_category=" + str(row.get("abstentionCategory") or "none")
              + " live_network=" + str(row.get("liveNetworkObservations") or 0)
              + " live_fixtures=" + str(row.get("liveFixtureObservations") or 0)
              + " current_anchor=" + str(row.get("currentByteAnchorValid"))
              + " publish=false", file=sys.stderr, flush=True)
    return 0 if len(rows) == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
