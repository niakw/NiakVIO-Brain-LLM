#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from niakvio_brain_llm.backend import StaticBackend
from niakvio_brain_llm.batch import load_census, select_batch_targets
from niakvio_brain_llm.document_memory import DocumentStore
from niakvio_brain_llm.niakvio_adapter import request_from_checkout
from niakvio_brain_llm.planner import BrainPlanner
from niakvio_brain_llm.repair_family import repair_family_descriptor
from niakvio_brain_llm.retrieval import ExperienceStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--niakvio-root", required=True)
    parser.add_argument("--experience", required=True)
    parser.add_argument("--extra-experience", action="append", default=[])
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    census = load_census(args.niakvio_root)
    requested = {
        str(value or "").strip().casefold()
        for value in args.provider
        if str(value or "").strip()
    }
    if requested:
        # The workflow page is already the resolved, authority-checked Repair
        # cohort. Do not reapply status/repair eligibility here: doing so can
        # silently discard FULL OK providers intentionally reopened for current
        # completeness debt.
        selected = [
            row for row in census
            if str(row.get("provider") or "").strip().casefold() in requested
        ]
        found = {
            str(row.get("provider") or "").strip().casefold()
            for row in selected
        }
        missing = sorted(requested - found)
        if missing:
            raise SystemExit(
                "deterministic Force preflight missing current census providers: "
                + ",".join(missing)
            )
    else:
        selected = select_batch_targets(census, mode="repair")
    store = ExperienceStore.from_jsonl_many(
        [args.experience, *args.extra_experience]
    )
    planner = BrainPlanner(StaticBackend("{}"), store, DocumentStore([]))

    rows: list[dict] = []
    for position, census_row in enumerate(selected, start=1):
        provider = str(census_row.get("provider") or "").strip()
        if not provider:
            continue
        request = request_from_checkout(args.niakvio_root, provider)
        request.advisor_only = False
        proposal = planner.plan_deterministic_force(request)
        print(
            "FIELD_BRAIN_DETERMINISTIC_FORCE_PROVIDER "
            f"provider={provider} failure={request.failure_class} status={request.status} "
            f"candidate={str(bool(proposal and proposal.mutations)).lower()}",
            flush=True,
        )
        if proposal is None or not proposal.mutations:
            continue
        rows.append({
            "position": position,
            "hypothesis_index": 1,
            "provider": provider,
            "status": request.status,
            "failure_class": request.failure_class,
            "repair_family": repair_family_descriptor(request),
            "ok": True,
            "routing": {
                "mode": "deterministic_force",
                "requires_llm": False,
                "target_layer": proposal.target_layer,
                "reason": "exact-current-byte deterministic Force compiler produced executable mutation",
            },
            "proposal": proposal.to_dict(),
        })

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )
    print(
        "FIELD_BRAIN_DETERMINISTIC_FORCE_PREFLIGHT "
        f"targets={len(selected)} candidates={len(rows)} "
        f"providers={','.join(str(row['provider']) for row in rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
