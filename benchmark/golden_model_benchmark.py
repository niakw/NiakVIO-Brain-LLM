#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from niakvio_brain_llm.backend import LocalOpenAICompatibleBackend
from niakvio_brain_llm.contracts import RepairRequest
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.mutation_guard import validate_mutations
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.policy import build_mutation_policy
from niakvio_brain_llm.priors import build_causal_prior
from niakvio_brain_llm.retrieval import ExperienceStore
from niakvio_brain_llm.verification_plan import recommended_tests

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--experience", required=True)
    parser.add_argument("--documents", required=True)
    parser.add_argument("--extra-documents", action="append", default=[])
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="niakvio-local")
    args = parser.parse_args()

    cases = [
        json.loads(line)
        for line in Path(args.cases).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    store = ExperienceStore.from_jsonl(args.experience)
    planner = BrainPlanner(
        LocalOpenAICompatibleBackend(
            base_url=args.endpoint,
            model=args.model,
            timeout_seconds=240,
            temperature=0.0,
        ),
        store,
        DocumentStore.from_jsonl_many([args.documents, *args.extra_documents]),
    )

    counts = {
        "schema_valid": 0,
        "provider_id_ok": 0,
        "layer_ok": 0,
        "strategy_ok": 0,
        "mutation_policy_ok": 0,
        "mutation_valid": 0,
        "abstain_policy_ok": 0,
        "brain_verification_plan_ok": 0,
        "model_tests_present": 0,
        "fully_compliant": 0,
    }
    rows = []

    for case in cases:
        request = RepairRequest(**case["request"])
        expected_layer = case["expected_target_layer"]
        expected_strategies = set(case.get("expected_strategies") or [])

        experiences = store.search(request.to_dict(), limit=6)
        retrieved_documents = planner.documents.search(request.to_dict(), limit=4)
        private_document_hits = sum(
            1 for row in retrieved_documents
            if row.get("private_memory") is True
        )
        prior = build_causal_prior(request, experiences)
        policy = build_mutation_policy(request, prior)

        try:
            proposal = planner.propose_raw(request)
            counts["schema_valid"] += 1
        except Exception as exc:
            rows.append({
                "id": case["id"],
                "schema_valid": False,
                "error": type(exc).__name__ + ": " + str(exc),
            })
            continue

        provider_id_ok = proposal.provider_id == request.provider_id
        layer_ok = proposal.target_layer == expected_layer
        strategy_ok = proposal.strategy in expected_strategies

        allowed_scopes = set(policy.get("allowed_scopes") or [])
        if not policy.get("allow_mutations"):
            mutation_policy_ok = not proposal.mutations
        else:
            mutation_policy_ok = all(
                str(mutation.get("scope") or "") in allowed_scopes
                for mutation in proposal.mutations
            )

        mutation_valid = True
        if proposal.mutations:
            try:
                validate_mutations(request.provider_id, proposal.mutations)
            except Exception:
                mutation_valid = False

        abstain_policy_ok = (
            proposal.abstain
            if policy.get("force_abstain")
            else True
        )

        brain_tests = recommended_tests(
            proposal.strategy or str(prior.get("strategy_prior") or ""),
            target_layer=proposal.target_layer,
            mutation_policy=policy,
        )
        brain_verification_plan_ok = bool(brain_tests)
        model_tests_present = bool(proposal.tests)

        scored_metrics = {
            "provider_id_ok": provider_id_ok,
            "layer_ok": layer_ok,
            "strategy_ok": strategy_ok,
            "mutation_policy_ok": mutation_policy_ok,
            "mutation_valid": mutation_valid,
            "abstain_policy_ok": abstain_policy_ok,
            "brain_verification_plan_ok": brain_verification_plan_ok,
        }
        for key, value in scored_metrics.items():
            counts[key] += int(value)
        counts["model_tests_present"] += int(model_tests_present)

        fully_compliant = all(scored_metrics.values())
        counts["fully_compliant"] += int(fully_compliant)

        rows.append({
            "id": case["id"],
            "schema_valid": True,
            **scored_metrics,
            "model_tests_present": model_tests_present,
            "fully_compliant": fully_compliant,
            "expected_layer": expected_layer,
            "actual_layer": proposal.target_layer,
            "expected_strategies": sorted(expected_strategies),
            "actual_strategy": proposal.strategy,
            "confidence": proposal.confidence,
            "abstain": proposal.abstain,
            "mutation_count": len(proposal.mutations),
            "brain_required_tests": brain_tests,
            "policy": policy,
            "retrieved_document_count": len(retrieved_documents),
            "private_document_hits": private_document_hits,
        })

    total = len(cases)
    result = {
        "model": args.model,
        "cases": total,
        "mode": "raw_model_reasoning_plus_deterministic_brain_verification_policy",
        "rates": {
            key: (value / total if total else 0.0)
            for key, value in counts.items()
        },
        "document_sources": 1 + len(args.extra_documents),
        "private_document_hit_cases": sum(
            1 for row in rows
            if int(row.get("private_document_hits") or 0) > 0
        ),
        "notes": {
            "model_tests_present": "diagnostic only; verification planning is owned by deterministic Brain policy",
            "fully_compliant": "does not require the model to invent verification tests",
        },
        "results": rows,
    }
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
