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


### 2026-09-27 — Generated Bloc compact-wire schema correction

- Audit found the compact Force response grammar required `scope + path` for every non-null edit even though the public `provider_bloc` contract intentionally has no repository path and only carries `family + find + replace`.
- The wire grammar now requires only `scope`; scope-specific completeness remains fail-closed in `_compact_edit_to_mutation` and the mutation guards. Existing file edits still require a registered path at local validation time, while generated Blocs no longer receive a contradictory grammar requirement.
- Added regression coverage preventing `scope,path` from becoming a universal compact-wire requirement again.


### 2026-09-27 — Family-targeted exact Force source windows

- Audit of the three representative existing runtime Blocs found the naive head/tail budget hid the likely causal code on all three: AllWish relevant filter/watch/resolve logic sits mainly in the middle of an ~8.6k source; 4KHDHub detail/HubCloud/resolve logic spans the middle of ~11.9k; MalluMV confirm/internal/m3u8/resolve logic spans roughly 6.8k–14k of ~15.8k.
- Compact Force no longer concatenates a synthetic `...<middle-clipped>...` marker into an apparent source string. It now emits up to four **exact current-byte source windows** totaling at most 4k characters.
- Window selection is generic by causal family: transport primitives for `provider_transport_gap`, route/detail/player primitives for `route_proven_gap`, and confirm/internal/terminal-media primitives for `chain_terminal_gap`. Unknown families fall back to generic resolver/fetch/search/player primitives; if no keyword exists, exact head and tail windows are used separately.
- Qwen is explicitly forbidden to join across windows. Its `find` must fit wholly inside one exact slice and is still validated for exact uniqueness against the complete unabridged source before any mutation can be published.
- Added regression coverage for middle-of-file chain-terminal code, exact-window semantics, total source budget, and both existing-Bloc and generated-Bloc prompt surfaces.


### 2026-09-27 — Force target cascade and truncation guard

- Three-family guidance run `36342073213` on Brain `12a5631bc28e905f297097f0e31571c3620deac4` / NiakVIO `1b79a1f9944c3ddc392cae14959cfff7935abfb8` completed, but it is **not** a repair proof.
- All three 512-token first calls timed out at ~120s; the single 768-token retries returned in ~22–63s. Force planning yielded two non-error rows, but only one mutation survived publication. `4khdhub` was rejected as placeholder/synthetic. MalluMV produced no publishable mutation.
- The only published candidate was AllWish and is visibly malformed: it replaces multiple helper declarations with a suffix-like fragment. It must not be treated as a valid repair merely because the guidance publisher accepted its bounded diff.
- Root cause audit: compact Force was still presenting an existing registered Bloc and a generated-Bloc runtime surface in the same prompt. On the real representatives that kept serialized prompts around 10.9k–13.5k characters and made target selection ambiguous.
- Force planning now uses a deterministic **target cascade**. It presents exactly one existing mutation surface first (registered Bloc, else authored module, else provider DATA). Only if that scoped attempt abstains or is rejected does it retry against `provider_bloc` when current provider-owned runtime bytes are available. At most one concrete mutation is returned per provider.
- `build_force_prompt_payload` now respects scoped `allowed_scopes`: a provider-patch-only attempt does not include generated-Bloc bytes, and a provider-Bloc-only attempt does not include existing patch/module/DATA bytes.
- Added a generic compact-edit guard for suffix/prefix-style truncation and silent helper-function removal. Small replacements inside a helper remain allowed when the helper signature is preserved.
- Telemetry now records the scoped target and explicit `FIELD_BRAIN_FORCE_SCOPE_{SELECTED,ABSTAIN,REJECTED}` events.
- No NiakVIO live FORCE is launched from run 36342073213. Regenerate the same three-family guidance with this cascade first.


### 2026-09-27 — Scoped cascade run result and scope-specific wire grammar

- Scoped three-family guidance run `36343881731` (Brain `60684885471dcef279708ca0d843dafce5c49d8c`, NiakVIO `1b79a1f9944c3ddc392cae14959cfff7935abfb8`) completed with **0 executable Force mutations**. No NiakVIO live FORCE was launched.
- The target cascade itself worked: MalluMV patch abstained then tried `provider_bloc`; 4KHDHub patch was rejected then tried `provider_bloc`; AllWish patch abstained then tried `provider_bloc`.
- Prompt sizes fell from the previous ~10.9k–13.5k chars to 6.5k–9.4k chars. AllWish no longer timed out on either scoped request. MalluMV/4KHDHub still crossed the 120-second initial timeout, but their retries returned only ~9–21 seconds later, showing the 120-second cutoff was causing duplicate requests near completion.
- 4KHDHub's final generated-Bloc rejection was `compact Force provider_bloc edit is missing or oversized`. The generic compact wire grammar only required `scope`, so Qwen was not grammatically required to emit `family/find/replace`.
- Compact Force now uses a **scope-specific minimal JSON schema**. Provider patch/module edits require `scope+path+find+replace`; generated Blocs require `scope+family+find+replace`; provider DATA requires `scope+operation+path`. Path is constrained to the exact visible target when available.
- Safe rejection telemetry now emits a bounded reason code (missing/oversized, placeholder, non-unique anchor, no-op, truncated fragment, helper removal, forbidden capability, wrong scope, missing source) without exposing source/private prompt text.
- Initial Force timeout is raised from 120s to 150s while keeping the same 512-token cap; this is intended to avoid the redundant retry observed just 9–21 seconds after the former cutoff. Retry remains bounded/fail-closed.


### 2026-09-27 — Reject placeholder Bloc families and partial function anchors

- Cascade guidance run `36344970225` / Brain `08c51930c44a5eecc8262089d0792e6e14debdd4` is green operationally but still **not provider proof**. It produced one publishable row, for MalluMV.
- The MalluMV row is rejected by inspection before NiakVIO FORCE: it copied the literal contract placeholder `snake_case_family` as the generated Bloc family and used a `find` that starts a JavaScript function but ends before the function body closes. Applying that prefix replacement could leave the old function tail behind and corrupt runtime source.
- `provider_bloc` now rejects reserved/example family names such as `snake_case_family`; the Force prompt explicitly requires a descriptive concrete mechanism family.
- Compact Force now rejects any provider_patch/provider_js/provider_bloc anchor that begins a function declaration but does not contain a structurally complete function block. Whole-helper replacement remains allowed when the complete helper is anchored and its signature is preserved.
- Added planner and mutation-guard regression tests. No NiakVIO live FORCE is launched from the malformed MalluMV candidate.


### 2026-09-27 — Reject helper absorption, duplicated JS tokens and neutral pseudo-fixes

- Hardened three-family guidance run `36346051449` / Brain `0aa104d6e18c78204319cb5b59ee1ee1a5d25a4f` completed much faster (~4 minutes Force generation) but still produced two unsafe/non-causal provider-patch rows and no 4KHDHub row.
- AllWish candidate introduced `async async function T(...)` and absorbed the following `function Q(...)` into the replacement. MalluMV candidate only changed a boolean condition by adding `|| 0`, a byte change with no behavioral effect. Neither is eligible for a NiakVIO FORCE proof.
- Compact Force now rejects replacement function declarations not already present in the exact `find`, duplicated JS control tokens such as `async async`, and boolean-neutral condition changes (`|| 0`, `|| false`, `&& 1`, `&& true`) when removing the neutral literal yields the original condition.
- For provider-patch edits, the fully updated Python Bloc is parsed with `ast`, its static runtime wrapper (`WRAPPER`/`JS`/`RUNTIME`) is extracted, and every wrapper is validated with `node --check` before a mutation can become a proposal. provider_js edits are also syntax-checked directly.
- Added regression tests reproducing the AllWish neighbor-absorption pattern and the MalluMV boolean-neutral pseudo-fix.
- 4KHDHub still has no executable mutation: provider_patch was rejected as synthetic and provider_bloc as non-unique anchor. It remains the representative blocker for route_proven_gap.


### 2026-09-27 — Deterministic validation-feedback retry

- CI run `36346562380` on `122bfb2a4b3002e7ee2e2a03eb1c72917e10d86b` showed the new syntax validator working, but two legacy planner tests used unrealistic provider_patch fixtures: one valid Python patch without a runtime wrapper and one raw-JS string under a `.py` patch path.
- Provider-patch validation now always parses the updated Python source; when static runtime wrapper assignments (`WRAPPER`/`JS`/`RUNTIME`) exist, they are additionally checked with `node --check`. A legitimate Python-only provider patch is not rejected merely for lacking a wrapper. The helper-signature test now uses a realistic Python wrapper.
- Added a bounded validation-feedback retry inside each Force scope. A deterministic `ValueError` (non-unique anchor, placeholder, syntax rejection, neutral pseudo-fix, etc.) is converted to a safe reason code and prepended to current observations as `force_validation_feedback`.
- Qwen gets one larger bounded retry in the same scope with the instruction to produce a materially different minimal exact unique edit or abstain. Rejected mutation/source text is never echoed back. Only after that correction attempt fails does the cascade move to the next scope.
- Timeout retries remain bounded. Telemetry emits `FIELD_BRAIN_FORCE_SCOPE_FEEDBACK provider=<id> scope=<scope> reason=<code>`.


### 2026-09-27 — Validation-feedback retry CI green

- Brain LLM CI run `36347059351` is green on `0a0cd93fd70cd9aba670590992310996a5d4c1c9`.
- The only preceding failures were test-fixture escaping; the compact Force engine, syntax/semantic guards, scope cascade and deterministic validation-feedback retry now pass the full Brain CI suite together.
- The next three-family proof is triggered from one immutable Brain revision and Brain main must remain unchanged until guidance publication, preventing the split-brain failure previously seen in NiakVIO Learning.
