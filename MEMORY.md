# NiakVIO Brain LLM — Durable Memory

> Technical recovery memory only. No private chat content, credentials, personal data, raw provider secrets or proof-authority claims belong here.

## 2026-09-25 — Guidance/Force architecture closure

- Brain LLM remains advisory. NiakVIO current-byte sandbox execution, playable-media proof, identity gates, regression checks, census state and publication are authoritative.
- Private-guided advisor generation now supports up to three distinct sanitized experiment hypotheses per provider in one guidance cycle. Hypotheses are alternative experiments, not mutations to stack together.
- The public guidance bridge uses exact requested repair cohorts and paged coverage so a larger provider portfolio is not truncated by a fixed first-N limit.
- Concrete Force output is bounded to one provider-local edit candidate per provider. Multiple concrete Force candidates for the same provider are rejected until NiakVIO can sandbox them independently.
- Force file edits use compact exact find/replace wire payloads which are locally expanded into validated unified diffs; malformed, clipped, non-unique, cross-provider or unregistered edits fail closed.
- Targeted MalluMV advisor run 36189111014 used NiakVIO source SHA 833e350a45e9bf0dd5b52ded736241b1927bce36 and produced three valid non-mutating advisor hypotheses. Concrete Force generation failed with truncated JSON (unterminated string), and the old workflow incorrectly failed the whole guidance publication because Force produced zero executable mutations.
- The truncation root cause was an undersized 256-token retry budget relative to the allowed bounded find/replace payload. Force now starts at 768 tokens and retries truncated/timeout JSON with bounded 768/1024 then 1280-class budgets and a longer bounded timeout. Malformed JSON is never auto-closed or salvaged.
- Advisor publication is now independent from concrete Force success. A valid non-mutating advisor page can publish when Force abstains/fails. Explicit NiakVIO Force remains fail-closed later when requireExternalForceMutations is requested.
- Brain LLM CI is green on c27480936b4bf488dd61e2276f1d753d8f15b7af after the retry/advisor-preservation contract updates.
- The next production validation belongs to NiakVIO: regenerate guidance for the exact current 14-provider repair cohort/current NiakVIO SHA, then let one Fast Brain Repair portfolio run execute alternatives sequentially and attribute each result independently.


## 2026-09-26 — NiakVIO local FORCE integration audit

- NiakVIO local experiment farm was confirmed to be running deterministic strategy grids only; it was not consuming the live Brain-LLM guidance branch. NiakVIO now has a non-authoritative reader for sanitized `niakvio-guidance/guidance/niakvio-guidance.json`, with deterministic fallback and canonical FORCE remaining authoritative.
- Concrete FORCE mutations are a separate surface: `niakvio-guidance/guidance/niakvio-force-mutations.json`. The previously published artifact (NiakVIO source `accaa36c...`, Brain SHA `16bc03ea...`) contained executable candidates for only `allanime` and `anime-ultime`.
- The published `allanime` mutation was evaluated with NiakVIO's official isolated FORCE evaluator on a current, context-compatible checkout. It applied cleanly but produced no improvement (`no_streams -> no_streams`) and was correctly rejected. This is negative execution evidence, not a harness failure.
- NiakVIO's FORCE evaluator sandbox default was found to be problematic under Node permission mode when created outside the repo; NiakVIO now places that sandbox under repo `local-output/`.
- A fresh `NiakVIO Private-Guided Advisor` workflow was dispatched for exact NiakVIO SHA `998fa355e5cc2769af18b5864246ab184738be63` and the full 14-provider repair cohort, page size 8: run `36210705712`. It is FORCE/advisor generation, not Learning. At latest observation, private-informed advisor/Force batch generation was still in progress; no fresh candidate success is claimed yet.
- Scalability note: `plan_batch_from_checkout.py` supports bounded parallel workers, but current FORCE workflow intentionally uses one llama slot and `--workers 1` because two concurrent generations had caused timeouts on GitHub runners. Do not raise concurrency without benchmark evidence; local/resident model execution is the safer future scaling path to evaluate.


## 2026-09-26 — NiakVIO local FORCE corpus ingestion

- NiakVIO now exposes a sanitized aggregate local FORCE corpus under `automation/local-force-results/`. The consolidated corpus covers all 14 repair providers with 124 observed experiments and at least 127 generated candidates.
- `scripts/import_public_niakvio.py` now imports this corpus into public Brain-LLM experience memory as four non-authoritative outcome classes: `no_progress`, `progress_without_deep_acceptance`, `baseline_healthy`, and `ambiguous_deep_candidate`.
- Raw provider responses, local paths, credentials, cookies/tokens and private chat content are not imported.
- Ambiguous local Deep candidates remain explicitly baseline-coincident and carry `proof_authority=false` / `prior_only=true`; the model must recommend current-byte revalidation rather than treat them as validated repairs.
- Unit coverage: `tests/test_public_local_force_import.py`; Brain LLM CI is green on the implementation series ending at `677df60e984d2e882501c0f9900841f79c263a42`.

### 2026-09-26 — Hard advisor prompt budget
- NiakVIO Learning run 36272561268 showed 12 advisor requests rejected by llama.cpp because accumulated provider context produced 6.5k–8.8k-token prompts against a 4096-token fallback context.
- Advisor provider_context is now explicit-allowlist only. Exact source remains outside this path for deterministic validation and compact Force mutation.
- build_prompt_payload progressively removes optional documents, excess experiences and source excerpts, then compacts observations/census/context; payloads above the 7600-character contract fail before any model request.
- Added a synthetic worst-case prompt-budget regression test including oversized sources, advisor history, observations, documents and an unknown 50k context field.
