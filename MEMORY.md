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


## 2026-09-27 — Generated runtime Bloc contract

- Confirmed an architectural gap in current Force: Brain LLM could mutate provider DATA, an authored provider module, or an already-registered provider Bloc, but could not create a new runtime Bloc when existing mechanisms were insufficient.
- Added the bounded `provider_bloc` mutation contract. The model emits only a family plus one exact unique find/replace against current provider-owned runtime bytes; it never chooses a repository path and never emits Python source.
- Current runtime bytes and the provider override are included in the mutation-context fingerprint, so stale generated-Bloc guidance fails closed.
- The contract supports canonical `patch_scripts` as well as the legacy serialized `provider_lego_scripts` reader during migration.
- New runtime capabilities such as `eval`, `Function`, Node process/require/child_process, Deno/Bun or dynamic import cannot be introduced by a generated Bloc replacement.
- This change is architecture/offline-only. It does not prove any provider repaired and must not trigger a provider Repair/Learning/FORCE run.


### 2026-09-27 — Generated Bloc CI correction / provider-only source boundary

- Brain LLM CI run 36335904761 executed 124 unit tests: the new generated-runtime-Bloc contract itself passed; the only failure was the pre-existing schema test still asserting the former three-scope set. The contract test is updated to include `provider_bloc`.
- Tightened `runtimeMutationSource` to stop before the first `CORE.*` STARTFIX inside the Provider envelope. A generated provider Bloc therefore cannot anchor on Core-owned bytes.
- Generated Bloc guards now reject ownership markers in both `find` and `replace`, preventing the model from selecting or forging STARTFIX/CLOSEFIX/FIXDATA metadata.


### 2026-09-27 — Guidance sanitizer aligned with generated Bloc scope

- The three-family live-proof guidance run exposed a stale workflow-local whitelist: the public Force contract now supports `provider_bloc`, but `niakvio-private-guidance.yml` still allowed only provider_data/provider_patch/provider_js during final artifact sanitation.
- Added `provider_bloc` to that final fail-closed whitelist. This does not weaken mutation validation: schema, mutation guard, current-byte context fingerprint and NiakVIO sandbox validation still apply before publication/acceptance.
- Run 36338401169 started from the preceding workflow SHA and therefore does not contain this workflow correction; its output is inspected before any NiakVIO FORCE trigger.


### 2026-09-27 — Three-family Force timeout diagnosed and bounded

- Targeted guidance run 36339445818 used exact NiakVIO SHA `1b79a1f9944c3ddc392cae14959cfff7935abfb8` and representatives `allwish`, `4khdhub`, `mallumv`.
- Advisor generation succeeded, but concrete Force produced **0 executable mutations**: all three provider calls timed out. This is not a provider-repair success and no NiakVIO FORCE run is justified from that artifact.
- The failure cost was structural: each provider could consume the initial 90-second request plus two 150-second retries, so three systemic timeouts consumed about 20 minutes while repeating the same CPU-bound failure.
- Compact Force source windows are reduced from up to ~12k chars per exact source to bounded head/tail windows (~4k for an existing patch/authored module and ~3k for a new runtime Bloc surface). Exact unique find/replace validation remains unchanged.
- Force now starts with a 512-token / 120-second budget and performs at most one larger bounded retry (768–896 tokens, 180–240 seconds depending on the initial timeout). Malformed/truncated output still fails closed; nothing is auto-salvaged.
- Added safe numeric telemetry `FIELD_BRAIN_FORCE_MODEL` (provider, serialized prompt chars, elapsed seconds, outcome, max token budget) and a regression assertion keeping the synthetic dual-source Force prompt below 10k serialized characters.
- Next validation is to regenerate the same three-family guidance against the unchanged NiakVIO SHA and require actual executable mutations before any live NiakVIO FORCE proof.


### 2026-09-27 — Timeout-fix CI contract alignment

- Brain LLM CI run `36341242374` on `b226ef96e794babce2497b5bf2d1c9655bc1dbe9` failed before any live provider proof because five source-contract assertions still required the superseded Force settings (`timeout_seconds=150`, second `1280` retry, `768/90` workflow budget and `8000/4000` prompt window).
- The observed failures were stale test expectations, not evidence that a generated mutation, provider sandbox or playback check failed.
- Contract tests are aligned to the new bounded CPU path: workflow `512/120`, one computed retry timeout, no `1280` second retry, existing-patch source window `2800/1200`, runtime-Bloc window `2000/1000`.
- No NiakVIO provider run is launched until the corrected Brain CI is green and the same three-family guidance run yields actual executable Force rows.


### 2026-09-27 — Compact Force scope visibility correction

- While the three-family retry was running, audit found that `build_force_prompt_payload` truncated the sorted mutation policy to `allowed_scopes[:3]`.
- Brain currently has four bounded provider scopes. Because the policy list is sorted, this could hide `provider_patch` from Qwen while simultaneously presenting an existing registered Bloc as `mutation_target.scope=provider_patch`, creating a contradictory prompt and unnecessary abstention.
- Compact Force now exposes the complete bounded allowed-scope list (maximum four by contract). Added regression coverage requiring all four scopes to survive while both an existing Bloc target and a generated runtime-Bloc target remain available.
- This is a Brain prompt-contract correction only. Any guidance already running from the preceding Brain SHA remains attributable to that SHA and is not silently relabeled as using this fix.
