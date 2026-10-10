## 2026-10-10 — Critical global early-exit in multi-provider FORCE removed

- Confirmed by exact source inspection of `scripts/plan_batch_from_checkout.py`: `--stop-after-first-mutation` is a **whole batch** exit, not a per-provider limit. With `--workers 1`, the first provider to yield any mutation sets `stopped_after_first_mutation=true`, records all remaining page providers as `earlyPublishDeferredProviders`, and `break`s out of the `for census_row in selected` loop. This is a direct source-level cause of one-provider-at-a-time progress even when the requested cohort is large.
- Full-cohort workflow mistakenly passed that switch alongside `--max-hypotheses 4` and `--workers 1`. Brain infrastructure commit **`d3d2d901`** removes the flag from `.github/workflows/niakvio-private-guidance.yml` while retaining per-provider bounded portfolio budgeting. The CLI fast-exit option remains available for explicitly scoped quick experiments, not global cohort mode. Regression **`ce8beb1c`** updates `tests/test_niakvio_force_workflow.py` to fail on reinsertion of the flag.
- Exact **Brain LLM CI `38068914976` SUCCESS on `ce8beb1c`**: 264 tests passed, privacy audit OK, private guidance workflow contract passed. Earlier CI on `d3d2d901` failed the stale test assertion until test update (not a runtime proof).
- Old guidance `38068530840` pinned Brain `cdd06f98` with first-mutation exit and was still generating when the new trigger was pushed. New trigger **`4e779474`**, exact NiakVIO source `d06d4cf6`, all **16 repairQueue**, retry 38, starts Private-Guided Advisor run **`38068986993`** with full-page iteration; separate NiakVIO FORCE `38066889059` remains active and pinned old Brain. Full provider terminal identity/playback validation and updated census still unproven.

## 2026-10-10 — Partial deterministic FORCE preflight must not starve a full page

- Found generic 800-provider scaling bug in `.github/workflows/niakvio-private-guidance.yml`: preflight marked `ready=true` on `executable > 0` (one deterministic Force provider), then bypassed Qwen for the **entire requested guidance page**, leaving siblings without model advice. This is a Brain workflow/control-plane fault.
- Workflow commit `197d4efc` changes this to `executable == page_count` before allowing deterministic-only bypass. Partial pages produce `FIELD_BRAIN_DETERMINISTIC_FORCE_PARTIAL ... action=run-model`; no unsafe provider publication. Test `a5046672` rejects the old partial preflight gate. **Brain LLM CI `38068478774` SUCCESS on `a5046672`: 264 tests plus privacy OK.** Earlier transient `197d4efc` CI failed because old workflow contract test still asserted the deliberately replaced greater-than gate; test was updated.
- Fresh full **16-provider** guidance trigger commit `cdd06f98` pins NiakVIO source `24f7a92aa9dc0cc87737e06eff31adfc202533c4`, excludes obsolete anime-ultime, and leaves `require_deterministic_force=false` so genuinely missing deterministic candidates can escalate to Qwen. **Private-Guided Advisor run `38068530840` dispatched successfully** on the trigger SHA. Its output/model calls are not yet validated. Separate NiakVIO FORCE `38066889059` runs on an older pinned advisor and must not inherit this run's proof.

## 2026-10-10 — End-to-end model-call regression for exhausted advisor

- Commit `63d92f83` adds `test_exhausted_advisor_calls_model_without_provider_mutation`: a same-executor three-distinct-executed-negative history routes to `llm_repair`, invokes the backend exactly once through `BrainOrchestrator.run`, retains exact strategy/provider identity, and returns **zero mutations** even when the request nominally lists provider_patch. This validates routing-to-actual-model invocation rather than only inspecting a routing flag.
- **Brain LLM CI `38068191061` SUCCESS on `63d92f83`**, with **264 unittest successes** and public-repository privacy audit **OK**. This is a model-call integration test using a stubbed backend; not yet a live Qwen generation or provider-playback proof. Preserve the distinction from existing Learning `38066889059` started on older Brain-LLM revision.

## 2026-10-10 — Real advisor exhaustion must reach Qwen, not 24 more knob rotations

- In NiakVIO Learning `38064727894` (pinned advisor `2ac7ed09`), the model routing summary reported **11 deterministic advisors and 0 LLM calls**, even though the live repair memory already holds three or more distinct failed executed fingerprints for multiple provider/strategy families. `routing.py` kept selecting another combinatorial experiment from `advisor_experiments._generic_variants` (24 permutations). This was a Brain-LLM routing inefficiency, not a directly proven provider-specific code problem.
- Brain-only commit `f3036a03` adds a per-strategy, provider-local *executed-evidence* exhaustion gate: after >=3 distinct SHA256 advisor experiment fingerprints from failed, `executionObserved=true` samples on the same known executor profile, escalate `advisor_only` to `llm_repair`, with `allowed_mutations=[]` (advisory only). Historical, unexecuted, duplicate or unrelated-profile negatives do not count, and healthy/NO PROOF/harness precedence remains intact. This is not automatic provider publication.
- Commit `4dba0502` tests both true exhaustion and negative counterexamples. First CI `38067942482` ran **261 tests green** but failed on the public privacy scanner's ten-consecutive-digit false positive in a hardcoded hex alphabet. Commit `6289f203` uses `c.isdigit() or c in "abcdef"` (same validation) to avoid this privacy false positive. **Brain LLM CI `38068006729` on `6289f203`: SUCCESS; 263 tests, privacy audit OK.**
- Existing full-16 FORCE `38066889059` was already started on NiakVIO SHA `64ed44fd` and pinned the **older** advisor revision before this new commit; its result must never be attributed to `6289f203`. Next fresh Learning/Repair must resolve and pin new Brain LLM main SHA and prove model-call route, genuinely novel executable strategy, compilation, application, exact bytes, correct title/episode terminal playback and persistent negative/positive memory.

# NiakVIO Brain LLM — Durable Memory

## 2026-10-10 — Recover all-17 model guidance and non-starving family-first pages

- Current NiakVIO `main` at trigger creation: `15cada89cc1191a4744ccb3fda6651051cfd118e`. Census **21 FULL / 46**, **17 active RepairQueue**, recent Fast `38013788179` validated **0/12**. Evidence from its real artifact: many providers exhaust route/transport profiles without new network observations or accepted compiled programs, so additional automatic 7B retries alone have no playable-media proof.
- Critical independent Brain-LLM coverage failure: `niakvio-guidance` published just **3 hypotheses for Moviebox**, `providerCount=1`, from an obsolete `sourceNiakvioSha=f1a37c99...`; main trigger `.github/triggers/niakvio-guidance.json` had **only `moviebox`** since Oct 6. Fast `38013788179` explicitly logged `FIELD_PROVIDER_FAST_REPAIR_EXTERNAL_LLM_GUIDANCE imported=true providers=1` for a 12-provider Repair run. Thus most current providers did not receive a new external LLM hypothesis.
- Brain-LLM commit `4fc64fac86b95428b91b2506185ab2200d510411` replaced stale Moviebox-only trigger with the exact **17-provider current RepairQueue**. Advisor run `38015349690` successfully checked out pinned NiakVIO SHA and resolved all 17 targets; model guidance itself remains unproved until published and retested. CI `38015349659` SUCCESS.
- Second generic pagination bug: the advisor selected one representative per unresolved failure family, then passed **only those selected IDs** to the paging state's `--targets`. Once the representatives were processed, the page incorrectly considered its reduced cohort complete and could never visit all 17 siblings. Brain-LLM commit `b180febaa358cd5f9afe4a4af25dda3febb73150` separates **priority representatives** from **full cohort authority**: `--targets` now receives all requested providers, `--priority-targets` orders family witnesses first. All siblings must eventually receive individually attributable guidance/proof. Regression tests cover 17 providers, moving family priorities and bounded **800-provider** paging without omission/duplication. Brain-LLM CI `38015517226` SUCCESS on the exact commit.
- At this checkpoint prior 17-provider advisor `38015349690` still runs older `4fc64fac` generation; *its complete selection cannot yet prove complete paging*. Next publication/replay must run on the new `b180feba` full-cohort page implementation, verify per-provider `attempted / advisory / deterministic / deferred` counters, then replay accepted model-authored programs on exact NiakVIO current bytes with title, season/episode, terminal stream and non-regression gates.
- These are **Brain orchestration and memory corrections only**; no provider was manually changed or marked FULL. Network WAF/HTTP timeouts still require fresh eligible observations/authorized client-browser traces, not unbounded profile retries.

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


### 2026-09-27 — Semantic no-op Force guard

- Hardened three-family guidance run `36346051449` completed successfully as a workflow, but the merged Force artifact retained only one provider mutation: MalluMV.
- Inspection showed that mutation changed `if (!best || bestScore < min) ...` into the same condition plus `|| 0`. In JavaScript this is behaviorally identical, so the candidate has zero causal repair value and must not consume a NiakVIO Deep sandbox run.
- Compact Force now rejects obvious boolean identity edits (`|| false`, `|| 0`, `&& true`, `&& 1`) when normalizing them makes find/replace equivalent. This applies to existing provider_patch/provider_js edits and generated provider_bloc edits.
- Added regression tests for both existing-Bloc and generated-Bloc semantic no-ops.
- Separate evidence from NiakVIO run `36345982243` requalified `vostfree` as FULL OK via residential replay with one raw stream, one playable stream, one verified stream and `identitySafe=true`; that overlay reduced the effective repair queue from 14 to 13, although the failed MalluMV Force prevented canonical census persistence.


### 2026-09-27 — Force retry latency cap after three-family wall-time audit

- The validation-feedback design was correct but its wall-time ceiling was still excessive: workflow Force used a 150-second first call and the retry helper could grant up to 240 seconds **per scope**. A provider failing both existing-Bloc and generated-Bloc validation could therefore monopolize more than ten minutes even before any NiakVIO Deep proof.
- Prior corrected three-family runs showed successful compact generations commonly returning in roughly 47–63 seconds. The first Force budget is reduced to 105 seconds.
- Retry timeouts now distinguish failure type:
  - deterministic validation rejection: 90–120 seconds (105-second workflow budget yields 120),
  - actual timeout/truncation: 120–150 seconds (105-second workflow budget yields 150).
- There is still at most one retry per scope and no guard/proof weakening. The change only caps wasted CPU time before the existing scope cascade moves on.
- Contract tests pin both timeout formulas and the 105-second workflow budget.


### 2026-09-27 — Durable synthesis/proof boundary + structured anchor compiler

- Three-family run 36350734425 completed operationally on Brain cd9c4c901f1b08266827c643113b0e4bcaac295c but published **0/3** executable Force mutations. MalluMV ended on a structurally incomplete function anchor; 4KHDHub and AllWish ended on non-unique provider_bloc anchors.
- Durable ownership decision: these failures belong to **Brain-LLM synthesis/compiler structure**, not to provider-specific NiakVIO Repair logic. NiakVIO remains the execution/proof authority and must not accumulate heuristics that guess what a malformed LLM edit meant.
- Compact Force source windows now carry stable request-local ids plus exact offsets. Real model wire schemas require window_id for provider_patch/provider_js/provider_bloc edits.
- Qwen only has to select one exact source window and express a local semantic find/replace that is unique inside that window. It no longer owns repository-global uniqueness.
- The Brain compiler resolves the selected occurrence against full current bytes, minimizes unchanged prefix/suffix copied by the model, and deterministically expands exact unchanged surrounding bytes only when global uniqueness requires it. If bounded uniqueness cannot be established, the mutation fails closed.
- Minimization occurs before partial-function structural validation. This allows a valid local expression change to survive even if Qwen copied an enclosing function prefix, while true incomplete/neighbor-smashing edits remain rejected.
- docs/ARCHITECTURE.md is updated from its obsolete 'future integration' description to the real pinned guidance bridge and explicitly records Brain synthesis versus NiakVIO proof ownership.


### 2026-09-27 — Structural compiler CI hardening

- CI run `36352593062` proved the new window-local compiler resolves a globally non-unique local anchor and can minimize copied partial-function context before validation, but legacy tests still expected the pre-compiler rejection behavior.
- The compiler now preserves already-globally-unique non-function snippets instead of unnecessarily minimizing them, while still minimizing ambiguous or function-prefixed model edits.
- Generated `provider_bloc` candidates now receive a full post-application JavaScript syntax check before the mutation can leave Brain-LLM. This closes a gap where a locally plausible replacement could leave the surrounding provider runtime syntactically broken.
- Contract tests now pass an explicit `window_id` for real compact-wire generated-Bloc edits and accept any fail-closed structural/syntax rejection reason rather than requiring the superseded pre-compiler message.


### 2026-09-27 — FULL OK patterns are references, not a whitelist

- Brain-LLM now builds a bounded implementation reference library from **current FULL OK providers** and their registered/published provider Blocs.
- References are selected by technical overlap with the current causal family and target source. Before model exposure, URLs, hosts, route literals, provider identifiers and opaque blobs are removed.
- Reference snippets carry no proof/publication authority and are explicitly marked `pattern_reference_only`.
- The model contract explicitly permits four outcomes: adapt a known pattern, combine several patterns, ignore all references, or synthesize a **genuinely new provider-local mechanism/Bloc/script**. Existing code is useful prior art, never a whitelist or ceiling on repair capability.
- New mechanisms retain the same bounded structural compiler and NiakVIO proof requirements. Novelty does not bypass syntax, ownership, no-op, sandbox, playback/identity or non-regression validation.

### 2026-09-28 — Three-family proof exposed model-owned window anchoring as the remaining compiler defect

- Guidance run `36354867920` on Brain `28a485b07f210ba9552752937c27a0bf8e8f37db` completed operationally but published **0/3** executable Force mutations for `mallumv`, `4khdhub` and `allwish`.
- The staged feedback path worked: every first invalid edit received deterministic `force_validation_feedback`. Final failures were MalluMV `forbidden_capability`, 4KHDHub `no_op`, and AllWish `non_unique_anchor`.
- This proves the transport/retry fix was real but insufficient. The remaining common defect was architectural: Qwen still effectively owned window-local textual anchoring, so repeated snippets could defeat synthesis even though Brain already owned global uniqueness.
- Durable correction: exact source windows now carry a deterministic causal `focus_offset`. Qwen chooses a window and local transformation; Brain resolves repeated local occurrences against that causal focus, then expands unchanged current bytes only as needed for global uniqueness.
- The compact Force contract no longer requires model-owned uniqueness inside the selected window. A repeated exact snippet is valid input to the compiler.
- Validation correction is now a bounded chain of at most **two** deterministic corrections per scope. This covers real sequences such as `truncated_fragment -> forbidden_capability` or `truncated_fragment -> no_op` without allowing an unbounded repair loop.
- FULL OK references remain optional prior art. Causal-focus compilation and validation correction apply equally to adapted known patterns and genuinely novel provider-local Blocs/scripts.
- Brain LLM CI run `36356184279` is green on `24039ff307c85cfef984110bd727e2c260b20a35`. This validates the compiler/test contract only; a fresh three-family generative proof is still required before any NiakVIO Deep execution.


## 2026-09-28 — Three-family focused retry proof: 1/3 exposed structural + safety gaps

- Guidance run `36358296711` tested Brain SHA `c015cbc610d8feba1b99fe5a3637db1551285603` against NiakVIO SHA `b570076d299d1871437d0065aec63caef768dd3e` for `allwish`, `4khdhub`, and `mallumv`.
- Workflow completion was **not** repair proof: only **1/3** executable Force rows were published. `mallumv` remained syntax-invalid after focused retries; `4khdhub` ended on a source-window/find mismatch; `allwish` produced a structurally accepted Bloc mutation that invented `https://invalid.local/` and is therefore reclassified unsafe/non-causal rather than usable evidence.
- Brain now rejects synthetic/reserved network endpoints in generated provider data/Blocs/patches, including reserved `.example`, `.invalid`, `.localhost`, `.local`, and `.test` hosts. Novel code remains allowed; invented network facts do not.
- Structural compilation now owns cross-window relocation: when an exact current-byte `find` is attached to the wrong `window_id`, Brain searches the bounded causal windows, deterministically relocates a unique best causal occurrence, and still fails closed on ambiguity.
- Validation feedback is reason-specific for syntax, window mismatch, ambiguity, synthetic endpoints, truncation, and neighbor absorption instead of collapsing to generic `ValueError`.
- Force cost is now bounded per provider. The private guidance workflow passes `--force-provider-budget-seconds 180`; every model timeout is capped by remaining provider budget and only one validation correction is allowed. This prevents a single provider from consuming the previous ~15-17 minute worst-case cascade.
- CI is green on Brain SHA `93217a4c0747c466687def9aae243ba1ab4aaaee`. This validates structure/tests only; a fresh three-family Qwen proof is still required before NiakVIO Deep.


## 2026-09-28 — Bounded three-family proof exposed initial Force prompt cost

- Guidance run `36360823219` tested Brain `c62db332ab055667056f728ae4fe94afb6f55c7b` against NiakVIO `43f53c6e7bc0af44bb0746f3245528ce345d2d83` for `allwish`, `4khdhub`, and `mallumv`.
- The wall-clock provider budget worked exactly as intended: each provider stopped around the 180-second Force ceiling instead of monopolizing the cohort for 15+ minutes.
- The run still published **0/3 executable Force mutations**. The common cause moved earlier in the pipeline: each initial provider_patch prompt was still ~10-13k characters and timed out at 120 seconds before structural correction could do useful work.
- Durable correction: compact Force **initial synthesis** is now causal and bounded too. Initial source windows are capped at 2600 characters / 3 windows, observations at 2, FULL OK implementation references at 1 short optional snippet, and census bulk is omitted. Validation feedback is tighter still at 2200 characters / 2 windows with no reference/census bulk.
- This does not reduce generative freedom: FULL OK patterns remain optional inspiration only and novel provider-local Blocs/scripts remain first-class. The change removes irrelevant prompt mass, not capabilities.
- Structural compiler protections remain active: synthetic network endpoints are rejected, exact finds may be relocated across bounded causal windows, and one production validation correction remains available inside the provider deadline.
- Brain CI is green on `a50e951dccb91f0fbcd4716b2ecf113a776550d5`. A fresh three-family Qwen proof is required before any NiakVIO Deep execution.


## 2026-09-28 — Compact prompt proof exposed prefill/cache opportunity

- Guidance run `36369813714` on Brain `f8a7fe053b8dee0df7b450bd4cf1c81683cf9b83` against NiakVIO `1ba50c4e3d79ca68c6b61306cdb4976d3d3ecfa5` still published **0/3** executable Force mutations.
- Initial Force prompt size fell materially from ~10-13k characters to ~6.1-7.4k, proving the compact-context change worked.
- The remaining latency pattern was highly asymmetric: first identical calls timed out at ~120s, while immediate retries on the same prompt returned in ~22-45s for MalluMV/4KHDHub. This indicates prompt/KV reuse is operationally valuable on the local llama.cpp server.
- Force backend now sends `cache_prompt=true` explicitly and supports a bounded one-token prefill before constrained generation. Prefill + generation share one backend deadline, so caching cannot silently exceed the per-provider wall-clock budget.
- Production Force generation is capped at 512 tokens. The compact schema permits only one local edit; 768-token decoding was unnecessary overhead.
- CI is green on Brain `92971e26af8d11c71fed0b384fe7d3dbfd090a32`. A fresh three-family proof is required before any NiakVIO Deep execution.


## 2026-09-28 — Force protocol + generation budget compacted by scope

- Cached/prefilled three-family proof `36370919531` remained **0/3 executable mutations**. Prefill/cache and a global 512-token ceiling improved infrastructure reuse but did not remove the 120-second provider_patch timeouts.
- Compact Force system instructions were reduced to the strict mutation protocol only; deterministic Brain schema/guards remain authoritative for scope, syntax, ownership, synthetic-network facts and exact-byte compilation.
- Generation output budget is now mutation-scope aware instead of paying the same ceiling everywhere:
  - `provider_data`: 192 tokens,
  - `provider_patch`: 320 tokens,
  - `provider_js`: 320 tokens,
  - `provider_bloc`: 448 tokens.
- This preserves extra room for genuinely new provider-local Bloc synthesis while making ordinary local edits materially cheaper on the CPU Qwen runtime.
- The workflow-level `--max-tokens 768` remains an upper ceiling; the planner applies the lower per-scope cap internally.
- Brain CI is green on `65ad59f86830a5555823aed30fe101118c9d3bd8`. Live three-family latency/mutation proof is still pending and must not be inferred from CI.


## 2026-09-28 — Compact Force system protocol proved latency, not repair quality

- Three-family guidance run `36382599941` on Brain `8831e5efaa6a1f9fc716f1fc5b97ffcb1f73b183` against NiakVIO `1ba50c4e3d79ca68c6b61306cdb4976d3d3ecfa5` completed operationally with **0/3 executable mutations**.
- Unlike the preceding 105–120 second timeout-heavy proofs, every model call completed: MalluMV ~40s + 35s, 4KHDHub ~33s + 31s, AllWish ~31s + 30s for provider_patch/provider_bloc respectively.
- Therefore compacting the Force system protocol is a real latency win. It does **not** by itself prove synthesis quality: Qwen abstained on all six scopes.
- Durable distinction: performance proof and repair proof are separate. A fast abstention is preferable to malformed code, but it is not a repaired provider.
- Abstention observability is now explicit: `FIELD_BRAIN_FORCE_SCOPE_ABSTAIN` carries a bounded sanitized `reason=` so future runs distinguish insufficient causal bytes, unavailable network facts, incompatible scope, or other model reasons without retaining raw private/model content.
- The next live proof adds scope-aware generation caps (192 data / 320 patch+js / 448 new Bloc) on top of the compact protocol. NiakVIO Deep remains blocked until complete 3/3 executable coverage is published.


## 2026-09-28 — Fresh targeted evidence reclassifies WAF outside provider mutation

- NiakVIO targeted diagnostic run `36383608344` tested exactly `allwish`, `4khdhub`, and `mallumv` on NiakVIO `cb5146437fbe801ccdb53a3ff40ab25f04a93cb1` and persisted its verdict on main as `bfb4a4c1a1902cb26f764826cc09a03d75f0f40e`.
- AllWish current evidence is unambiguous transport/WAF evidence: movie and TV both reach TMDB 200, then `all-wish.me /filter` returns HTTP 403 with debug stage `provider_waf_challenge`. No playable or verified lane exists.
- This does **not** justify a provider-local mutation. Brain now reclassifies fresh targeted WAF-only evidence with 401/403/429 into `transport_environment_gap`, withholding provider mutation authority until browser/native/residential evidence implicates provider-owned code.
- 4KHDHub remains a provider-local route-to-terminal case: provider root responds 200 but both lanes end `provider_network_zero_result`.
- MalluMV remains a provider-local terminal-extraction case with a fresh observed chain through MalluMV search/detail/internal pages into `vik1ngfile.site /f/...`, its custom asset, and `vikingfile.com /fast-download/...`, all returning 200 but still no terminal playable stream.
- The previous three-family proof contract using AllWish as a required mutation representative was causally wrong. A valid family proof must use provider-local representatives for mutation synthesis and treat justified non-provider outcomes as abstention/diagnostic evidence, never force a patch.
- Brain CI `36383933144` is green for the fresh-WAF reclassification contract.


## 2026-09-28 — Adaptive Force quality budget for portfolio scale

- Local Mac execution is now part of the development loop only: Python 3.12 runs the full Brain suite in about 0.3-0.4s, while GitHub Actions remains the immutable remote proof authority.
- Uniformly shrinking Force budgets would trade away repair quality. The production contract is now progressive instead:
  - compact first attempt for cheap provider-local edits,
  - larger validation-recovery output budget only after a structurally promising rejected candidate,
  - more room for genuinely novel provider_bloc synthesis than ordinary patch/js edits.
- Scope caps: primary data/patch/js/bloc = 192/320/320/448 tokens; validation recovery = 256/384/384/512 tokens.
- Transport retry does not receive the quality-escalation token budget because it repeats the same synthesis after a transport/timeout failure; escalation is reserved for deterministic structural feedback.
- Provider wall-clock budget is evidence/status aware under a hard workflow cap of 240s: CHAIN REACHED / chain-terminal / media-extraction cases may use the full cap; ROUTE PROVEN is capped at 180s; ordinary unresolved cases at 150s; transport/environment cases at 120s.
- These are compute allocation rules, not acceptance relaxations. Syntax, ownership, exact-byte compilation, synthetic-network rejection, novelty freedom, NiakVIO sandbox/playback/identity and non-regression gates are unchanged.
- This is the intended several-hundred-provider scaling model: cheap abstention for causally unsupported cases, bounded local edits for ordinary cases, and expensive synthesis only for evidence-rich hard cases.


## 2026-09-28 — Force exact-byte ownership moved fully to deterministic Brain compiler

- Three-family adaptive proof `36388332434` remained 0/3 even with correct causal windows and bounded compute. AllAnime, MalluMV and 4KHDHub abstained cleanly because the model could not guarantee exact safe bytes.
- Local reproduction proved the causal windows were correct; the defect was the editable-unit layer. Previous units could expose structurally incomplete fragments such as function prefixes or mid-token snippets.
- Force wire contract is now `unit_id + replace` for provider_patch/provider_js and `family + unit_id + replace` for provider_bloc. Qwen no longer copies or invents `find` bytes.
- Brain deterministically derives exact current-byte statement units from the causal windows, rejects partial function/control fragments and token-edge truncation, and resolves the selected unit back to exact bytes/offsets before syntax/ownership/mutation validation.
- Real-unit inspection after the change produced complete causal statements for AllAnime, MalluMV and 4KHDHub (for example `if(!raw)continue;`, `if(!best||bestScore<c.minIdentityScore)return null;`, `var q=req(a);`) instead of truncated function prefixes.
- This is a quality improvement, not a safety relaxation: the model reasons about what logic to replace, while deterministic Brain owns where/current bytes; NiakVIO remains the runtime proof/publication authority.
- Local Mac suite: 150/150 tests green after the migration. Fresh remote three-family proof is still required.


## 2026-09-28 — Local M1 Force proof: composite units and causal deletion guards

- Running the same Qwen2.5-Coder-3B Q4_K_M model through llama.cpp/Metal on the M1 materially accelerates iteration versus GitHub CPU while GitHub remains final CI/proof authority.
- Exact-SHA local cohort AllAnime/MalluMV/4KHDHub on NiakVIO `9363614e3d5ac9b918ac7264c0f8459c2ad1467b` produced 2 selected sandbox mutations (AllAnime and 4KHDHub) versus 0/3 on GitHub CPU. NiakVIO isolated candidate evaluation accepted 0/2: AllAnime remained `no_streams`; 4KHDHub remained `provider_unreachable`. No provider mutation was published.
- Root lesson: exact statement units fixed malformed-byte ownership but were sometimes too atomically local to express a causal traversal repair. Brain now exposes bounded adjacent statement sequences (2-4 statements, <=700 chars, whitespace-only gaps, never crossing braces) alongside single-statement units.
- A second local cohort with composite units showed AllAnime and MalluMV still tending toward no-op/abstention; 4KHDHub produced a candidate that merely removed `normalized = _embeddedText(text)` and had no runtime improvement.
- Deterministic compiler guards now reject (a) removal of a local binding that is still referenced nearby before redeclaration and (b) pure-deletion repairs for `route_proven_gap`, `chain_terminal_gap`, or `media_extraction_gap`. This blocks byte-changing but causally empty edits before NiakVIO sandbox time is spent.
- Local Brain suite after these changes: 153/153 tests green. Fresh three-family model proof is still required before claiming any provider repair.


## 2026-09-28 — Strict Force JSON and bounded causal function units

- MalluMV malformed JSON was isolated to permissive model response formatting, not provider reasoning. The local OpenAI-compatible backend now requests strict json_schema responses; MalluMV no longer emits malformed JSON and instead cleanly abstains when it cannot express a repair.
- Brain CI is green for the strict JSON change.
- Statement and small statement-sequence units were still too local for some chain repairs. Force now also exposes exact bounded function_unit candidates only when the function name matches the active failure-family causal keywords (for example confirm/internal/resolve for chain-terminal gaps).
- Function units are exact current bytes, brace-balanced, size-bounded, and selected only by unit_id. All normal mutation/syntax/network/no-op/NiakVIO proof gates remain authoritative.
- The causal-function extraction test now passes; CI is green on Brain SHA 89cae9f8f4088c0351c1cb3926613be3e4faeba4 before the focused MalluMV proof trigger.
- Focused MalluMV proof run 36408982707 tests trigger SHA 6b4740af9e7a7551b249ab40033de4e86fb77222 against NiakVIO SHA d17f241726180d727152dd4e460cfafd7a725d4f. Do not treat this run as proof until its Force artifact is inspected.
- Local Mac is no longer required for correctness. It accelerated diagnosis of JSON serialization and edit-unit expressiveness; GitHub remains proof authority.


## 2026-09-28 — Fleet-scale Force paging and fresh-evidence bridge

- Full 14-provider repair cohort was paged as 8 + 6 with exact source/Brain SHA state and no starvation.
- The first continuation exposed a real orchestration bug: `cancel-in-progress: true` allowed a self-dispatched next page to cancel the page that had just published state. The guidance workflow now serializes continuation pages with `cancel-in-progress: false`.
- `tests/test_guidance_paging.py` now proves exact, duplicate-free coverage of a 250-provider cohort at page size 8.
- Force policy correctly refuses provider mutation when `targeted-regression-current` evidence is missing. The full 14-provider run proved the workflow previously stopped at that guard for most providers instead of collecting evidence.
- NiakVIO targeted recovery run `36412614349` was triggered for all 14 providers and persisted fresh network/debug evidence on NiakVIO main. Brain must replan from that newer NiakVIO SHA rather than treating checkout-only census evidence as sufficient.
- GitHub CPU remains the expensive path for the small subset that genuinely needs Qwen synthesis. Prompt context is now deduplicated from exact editable-unit bytes: editable units are still derived from the wider causal windows, while the displayed context window is smaller.
- Scale principle: healthy providers never enter LLM repair; the Brain operates on the repair queue. For large catalogues, NiakVIO already has sharded targeted recovery (8 shards, up to 20 probe workers each); Brain guidance paging is independently bounded and resumable.
- Current validation state at this checkpoint: paging/orchestration improvements are CI-backed; the fresh-evidence 14-provider Force replan is still running and must not be recorded as repaired until NiakVIO current-byte validation succeeds.


## 2026-09-28 — WAF/client differential is now causal Brain input

- Fresh targeted recovery on the current repair queue proved that census/provider-network errors alone are insufficient to decide provider-code ownership.
- Brain now ingests `automation/provider-waf-browser-session-latest.json` alongside targeted regression evidence.
- If a provider-origin 401/403/429 persists across ordinary browser and residential evidence with no content profile reaching the target, the failure remains `transport_environment_gap` and provider mutation authority is withheld.
- If the same failed target is reachable through an audited Nuvio-like profile (UA browser, direct HTTP approximation, or OkHttp JVM), Brain classifies the differential as `client_transport_gap`; this maps to the harness/client layer and forbids provider mutation.
- This prevents false provider patches for transport/TLS/client-profile failures while still allowing real provider-local zero-result/terminal-extraction failures to enter Force.
- Current NiakVIO targeted evidence run `36415009826` covered all 13 providers still in the repair queue after Vostfree became FULL OK. The current provider-code queue must be derived from this evidence, not from census status alone.


## 2026-09-28 — Residential provider replay outranks narrow WAF seeds

- WAF automation is operational: Browser Session diagnostics ran the targeted repair cohort through GitHub-hosted and Tailscale residential paths, and full residential provider replay recovered Vostfree to FULL OK.
- A causal bug was found in Brain routing: a targeted provider-origin 401/403/429 could classify a provider as `transport_environment_gap` before considering the stronger full residential provider replay.
- Evidence priority is now explicit: full residential provider replay > WAF seed/client-profile probe > targeted network status.
- If residential full-provider replay finishes identity-safe with no WAF/timeout stage but still produces zero/error, Brain keeps the ordinary provider failure class (route/chain/provider gap) so Force may repair provider logic.
- Only persistent WAF confirmed across browser and residential evidence may route to `transport_environment_gap`; client-transport routing remains reserved for audited Nuvio-like reachability when no stronger full-provider replay has isolated provider-local failure.
- Brain CI is green on SHA 34941459752f5f820df7f794b577cc484503cf57; clean 13-provider replan trigger SHA c017874390e8630bc0cad0e66cb8017b7768dc6e is running against NiakVIO 6f3beaad1f6fc47f55f63edad06c4a1d2365a95b.


## 2026-09-28 — Local FORCE evidence persistence rule

- Local Mac experiments are development evidence only until their durable verdict is written to repository memory/corpus and their candidate outcome is externally verified by NiakVIO.
- The 2026-09-28 reboot removed ephemeral `/tmp/niakvio-*` raw artifacts. The durable conclusions were already recorded in this `MEMORY.md` (including the AllAnime/MalluMV/4KHDHub local cohorts and 0/2 isolated NiakVIO acceptance), but raw temp bytes were not recoverable.
- Going forward, any local FORCE batch that materially changes learning must persist a sanitized result/ledger under repository-owned data or `MEMORY.md` before the local session is considered complete. `/tmp` alone is never an accepted learning store.
- Existing local dirty changes were audited against current `main`; causal family edit-unit priority was the only still-useful missing behavior and was reintroduced on current HEAD with a regression test, without reverting newer compact-context changes.


## 2026-09-28 — Durable local FORCE 13-provider evidence

- Local Qwen FORCE ran the complete current 13-provider repair cohort against NiakVIO a218aaecb1764a74f9e2f26c10f2a10a7c8955f6 with Brain b1fc86b4652417795590f6650c8194202461a813.
- The sanitized Force bridge accepted 6 sandbox-authority candidates: mallumv, 4khdhub, animesultra, vidfast, yflix, allwish.
- 6 providers abstained cleanly: allanime, moviebox, anime-ultime, animesalt, animevost-fr, flemmix.
- moviesmod ended in a bounded local timeout and remains unresolved.
- Evidence is persisted under evidence/local-force/2026-09-28/; these results must be reused before generating a new cohort from scratch.
- Candidate status is NOT repair proof. Each accepted local candidate still requires current-byte NiakVIO sandbox evaluation, playable-stream/identity validation and relevant non-regression before publication.
## 2026-09-28 — FORCE context diversity and authored-surface priority

- ROUND3 negative-memory replay proved a generic Brain limitation rather than a MalluMV-specific provider bug: several providers spent their budget on repeated micro-units, no-op/syntax corrections or broad generated-runtime Blocs and produced no publishable candidate.
- MalluMV's compact provider-patch context was initially four variants of the same already-rejected `confirm_links` area. Brain now derives bounded causal whole-function units from exact provider-owned bytes and reserves space for diverse causal helpers; current MalluMV context exposes `resolveCandidate`, `resolve`, `plausible` and `internalFrom` instead of one repeated micro-anchor.
- Function-unit selection uses causal evidence in the function body, not semantic function names, so generic/minified helper names remain eligible. Exact-byte ownership, brace/syntax checks, provider ownership, network-fact guards, no-op guards and NiakVIO sandbox proof are unchanged.
- Existing provider-owned surfaces are now attempted before a novel `provider_bloc`; new Bloc synthesis remains available as the fallback after abstention/rejection. This avoids burning bounded compute on broad generated-runtime helpers before the authored provider implementation has been tested.
- Statement/sequence replacements remain capped at 640 characters. A supplied bounded `function_unit` may replace up to 1800 characters, with strict JSON schema widened accordingly; provider_patch/provider_js generation budgets are now 640 primary / 768 structural recovery tokens so structurally complete replacements can actually be emitted.
- Local focused MalluMV run after context diversification still abstained on provider_patch and provider_bloc. This is not a provider repair and must not be promoted as one.
- Focused Brain regression suite is green: 47 tests across prompting, compact Force retry, generated runtime Bloc contract, planner, batch concurrency and provider context; `git diff --check` is clean.

## 2026-09-28 — Same-census evidence continuity and HTTP-200 WAF routing

- NiakVIO targeted run 36461136076 refreshed only MalluMV but had overwritten a same-census 13-provider snapshot, which made the other 12 providers appear `not-probed` to Brain. NiakVIO commit `471d652dbebe487f6418218211f6b5d44ec2cc24` now retains untouched provider rows for the same `sourceCensusRunId` and starts fresh only on a new census epoch.
- Brain current-byte replanning must consume the cumulative same-census targeted snapshot instead of treating a one-provider targeted run as the whole fleet state.
- MalluMV current targeted evidence is `provider_waf_challenge` despite HTTP 200 responses. The terminal Viking handoff is an interactive Turnstile gate, so this is transport/WAF evidence rather than provider-code mutation authority.
- Brain keeps the descriptive failure as `provider_transport_gap`, while the causal prior promotes explicit current targeted WAF evidence to the harness/transport diagnostic layer with `compare_browser_native_residential_profiles_without_provider_mutation`.
- On the restored 13-provider evidence snapshot, MalluMV, MoviesMod and AllWish route without provider mutation; 4KHDHub, AnimeSultra, VidFast and YFlix retain provider-repair eligibility from their non-WAF targeted evidence; AllAnime and MovieBox retain chain-terminal provider repair.
- Stronger identity-safe full residential provider replay can still override a narrow WAF seed and return a provider to ordinary repair.

## 2026-09-28 — Response-shape evidence bridge

- Post-fix local Qwen validation against NiakVIO same-census evidence produced no accepted mutation: AllAnime abstained on both authored provider patch and generated Bloc; 4KHDHub abstained on the authored patch and exhausted the Bloc provider budget. These are not repaired providers.
- The remaining seven provider-repair lanes had current request/status evidence but no persisted response structure; historical `provider_value_trace_v18/v21` is null for these specific current providers, so simply importing that trace would not resolve the evidence gap.
- NiakVIO `a2ff1ef592a7a164ec46ddf6af628df317c0c593` now emits and persists a bounded response-shape summary: sanitized JSON schema keys/types or fixed HTML/JavaScript counts/markers only. It never persists response bodies or values.
- Brain now re-sanitizes targeted `shape` evidence on ingestion before it can enter compact Force prompt context. Unknown fields/markers and unsafe key names are dropped.
- Shape evidence is diagnostic context, not proof or mutation authority. Candidate acceptance still belongs exclusively to isolated NiakVIO current-byte playback/identity/non-regression validation.

## 2026-09-28 — Targeted response-shape deduplication

- Current targeted recovery can contain many routes from the same host/status that expose an identical bounded response shape. Repeating all of them in compact Force wastes prompt evaluation without adding causal structure.
- Brain now deduplicates shape-bearing targeted network rows by method + host + status + sanitized response shape, keeps one representative route, and records `sameShapeRoutes` as a bounded count.
- Shape-less transport failures keep their individual route paths, so distinct unreachable hosts/routes are not collapsed.
- AllAnime current targeted observation shrinks from 2742 to 1708 characters on the same NiakVIO evidence while retaining its current API and HTML shape families.
- This is prompt compaction only; it does not change failure classification, mutation authority, proof gates or provider status.

## 2026-09-28 — Force model timeout made quality-configurable

- A real AllAnime local Force attempt proved the fixed 120s model ceiling was too short for structural output: the cold request timed out, prompt-cache retry was canceled at 533/640 generated tokens, and no model verdict could be parsed.
- The scheduler now lets `--timeout-seconds` raise primary/transport model calls up to 180s. Existing GitHub guidance still passes 120s, so its current default runtime is unchanged.
- Route-proven provider budget may now use up to 360s when the caller explicitly grants that budget; the existing GitHub workflow still passes 240s, so its current production ceiling remains 240s. Transport/environment cases remain capped at 120s.
- Validation correction timeouts remain deliberately smaller (90s patch/JS, 120s Bloc) because their focused prompts are much shorter.
- Local hard-case proofs can therefore use 180s model timeout + a larger explicit provider budget without weakening exact-byte, syntax, ownership, sandbox, playback or identity gates.

## 2026-09-28 — Final local FORCE stop state

- Resource-intensive local Qwen/Force execution was intentionally stopped after it began impacting the host machine/network experience. No `llama-server` or `plan_batch_from_checkout.py` process remains running.
- Brain `main` already contains the response-shape deduplication, configurable model timeout and explicit extended ROUTE PROVEN budget used for this pass.
- 4KHDHub final persisted local result: `ROUTE PROVEN`, repair routing reached provider patch then provider Bloc; both paths abstained after deterministic validation feedback. Final proposal contains **0 mutations** and `abstain=true`.
- YFlix final persisted local result: `ROUTE PROVEN`, provider patch and provider Bloc both abstained after validation feedback. Final proposal contains **0 mutations** and `abstain=true`.
- MovieBox final persisted local result: `CHAIN REACHED`; provider patch was rejected as a no-op, provider Bloc entered validation feedback, then the correction call timed out. No candidate gained publication authority.
- AllAnime began a new pass but was interrupted before a final result. Anime-Ultime, AnimeSultra and VidFast were not executed in this final sequence.
- No provider from this stop-state is to be marked repaired or promoted. Existing NiakVIO playback/census authority remains unchanged.

## 2026-09-28 — GitHub executable FORCE budget aligned

- The authoritative `NiakVIO Private-Guided Advisor` workflow is the executable Brain-to-NiakVIO bridge: it produces sanitized advisor guidance **and** `niakvio-force-mutations.json`, publishes both on the orphan `niakvio-guidance` branch, and grants only sandbox mutation authority.
- Its provider-repair generation budget is now aligned with current Brain contracts: one model worker, 768 max tokens, 180 s model timeout and 360 s total per-provider Force budget.
- This closes the GitHub/local split where current Brain supported 180/360 but the guidance workflow still cut structural provider patches/Blocs at 120/240.
- Publication authority remains false. NiakVIO Recognition must still evaluate every concrete Force mutation in isolated current-byte provider sandboxes, persist negative memory, and require playable/identity-safe improvement before direct application.

## 2026-09-28 — FORCE invention fallback unblocked

- Final executable-guidance cycle on Brain `cf4e6c8e…` completed the full 13-provider repairQueue but produced **0 executable mutations**. Logs showed repeated `No_suitable_editable_unit_found` / `no_suitable_unit_found_to_express_the_repair` for provider-layer ROUTE/CHAIN gaps.
- Root cause was architectural: compact FORCE described `provider_bloc` as a “new mechanism” but still filtered complete functions by failure-taxonomy keywords and explicitly told Qwen to abstain when existing editable units did not already express the mechanism.
- `provider_bloc` is now an actual invention fallback. Generic complete provider-owned functions remain eligible even without taxonomy keyword matches; keyword matches still rank first. The model is instructed to rewrite the nearest complete function with a novel bounded provider-local mechanism when evidence is sufficient, rather than abstaining merely because no existing helper matches.
- Generated Bloc replacement bound is aligned with complete function units at **1800 chars** across planner, Brain mutation guard and NiakVIO application guard. Exact current bytes, syntax checks, dangerous-capability guards, mutation-context fingerprints, isolated Deep sandbox and NiakVIO proof remain mandatory.
- Do not interpret this as provider repair proof. The next authoritative guidance cycle must produce and sandbox concrete mutations before any provider status changes.

## 2026-09-28 — Current provider replay now outranks narrow WAF priors

- A second FORCE routing contradiction was confirmed after the 13-provider zero-mutation cycle: `request_from_checkout()` could correctly preserve a provider-layer `ROUTE PROVEN`/chain failure after identity-safe residential replay, but `build_causal_prior()` independently reclassified the same request to `harness` whenever an older targeted observation contained `provider_waf_challenge`.
- This made repair routing deterministic/non-mutating even though the strongest current evidence showed the provider runtime itself still failed cleanly (including `provider_zero_before_provider_network`).
- The causal prior now checks the current `waf-client-differential-current.residentialReplay` evidence before honoring a narrow targeted interactive-challenge seed. An identity-safe, contradiction-free replay whose debug stage is not WAF/timeout preserves the provider failure taxonomy and allows provider repair synthesis.
- Tests cover both `route_proven_gap` and `chain_terminal_gap` preservation. Brain CI #885 passed on `bfcf26bf752176e2d6c4c96241870e434e182b18`.
- Persistent/current challenge evidence without a clean full-provider replay remains non-provider/harness evidence; this change does not authorize provider code to bypass real WAF.

## 2026-09-28 — FORCE fresh-evidence gate repaired

- Brain executable-guidance runs #138/#139 proved that all 13 current symptomatic providers were provider-layer failures in repair mode (`CHAIN REACHED`, `ROUTE PROVEN`, or provider transport gap), but every scoped FORCE attempt returned immediately with `routing_modes={"probe":...}`, `llm_calls=0` and `FIELD_BRAIN_FORCE_SCOPE_ABSTAIN ... reason=unspecified`.
- Root cause: mutation policy required `targeted-regression-current` for route/chain/provider-transport failures. The targeted artifact is intentionally discarded when its `sourceCensusRunId` differs from the current census, but policy ignored equally authoritative proof already integrated into the current census. This created a permanent no-LLM loop after every fresh census.
- Adapter now carries `testedThisRun`, `residentialProviderReplayClass` and `residentialProviderReplayEvidence` into `census_current`.
- Mutation policy accepts current-census provider proof only when `testedThisRun=true` and the row carries route proof, candidate proof, residential provider replay evidence, or explicit route/chain evidence depth. Stale current-census rows remain fail-closed.
- Tests cover current proof allowed, stale proof rejected, and replay fields reaching policy context. CI #892/#893 passed.
- The standalone WAF/replay artifact remains insufficient freshness authority because it has no census/SHA pin; this fix deliberately does not trust it directly.

## 2026-09-28 — Guidance publication race closed; authoritative cohort is now 14

- Confirmed a publication race on `niakvio-guidance`: a late older guidance run could refetch the branch, satisfy `force-with-lease`, and overwrite a newer Brain/source state. This occurred when the branch fell back to Brain `32244976822e...` / NiakVIO `803ab253...` after a newer cycle had run.
- Current workflow now has semantic stale-publication protection: a candidate Brain revision that is an ancestor of the already-published Brain is skipped, divergent histories fail closed, and stale runs do not launch continuation pages. Contract tests passed; current Brain CI #902 is green at `9cb448519e2a8089219e96cb2620e815b79e1a53`.
- Routing observability is retained in artifacts (`routing.jsonl`, `routing-force.jsonl`) and emits bounded `FIELD_BRAIN_ROUTE` lines with mode/layer/failure/scopes/reason.
- The current NiakVIO census `36484610716` has **14** repairQueue providers, not 13: the prior cohort plus `vostfree`. Any final convergence claim must therefore cover 14/14.
- `vostfree` is currently ROUTE PROVEN but `testedThisRun=false`, reconciled from carried green with a contradictory latest WAF lane verdict. It must receive fresh current evidence before provider mutation authority is granted.


## 2026-09-29 — FORCE #147 completed; helper-identity minimization defect closed

- Authoritative Brain FORCE cycle on `fdda761b006305d3d89ad448ce34a0f385802522` completed all 14 requested providers against NiakVIO `a7c1ad0013394fb010bcc176447554bc53a8f454`.
- It produced 3 executable provider_bloc mutations: `anime-ultime`, `flemmix`, and `moviesmod`. The other 11 providers produced no executable mutation in this cycle.
- All three emitted the same structural rewrite: the selected complete helper `function _routeKind(...){...}` was replaced by `function _extractUrls(...){...}`. This exposed a generic compiler defect, not three independently validated repairs.
- Root cause: `_resolve_structured_anchor()` minimized common function prefix/suffix bytes before running the helper-declaration guard. The full-function rename therefore collapsed to an anchor resembling `routeKind(...) -> extractUrls(...)`, after which declaration identity was no longer visible to the guard.
- Brain now runs `_reject_partial_function_anchor(find, replace, ...)` on the complete selected edit before minimization, while retaining the existing post-minimization guard. A regression test asserts that explicit helper renames fail closed before they can become minimized anchors.
- The 3 mutations from `fdda761b...` have no sandbox/publication authority and must not be applied. Regenerate only those affected providers first on current Brain main; the 11 abstentions remain historical negative evidence rather than being discarded.
- NiakVIO drift after the source SHA was provider-neutral (workflow/evidence/census only). Vostfree subsequently left the repairQueue, which is now 13 providers.

## 2026-09-29 — Dedicated provider runtime outranks generic Bloc

- FORCE #147 and its guarded 3-provider reruns exposed a scope-selection error after the earlier global Bloc-first change.
- Anime-Ultime, Flemmix and MoviesMod already own dedicated registered runtime resolvers, but structural failures were sent to generic `provider_bloc` first. Qwen therefore tried to mutate generic route helpers instead of the provider-specific traversal logic.
- Current repairQueue audit shows 12/13 providers have a registered patch containing `NIAKVIO_PROVIDER_RUNTIME_RESOLVER_V1` / `__niakvioProviderRuntimeResolverV1`.
- Scope precedence is now causal: for structural ROUTE/CHAIN/media gaps, a registered provider-local runtime resolver is attempted first; generic provider_bloc remains the invention fallback after that surface abstains/rejects or when no dedicated runtime exists.
- This does not restore unrestricted patch-first behavior. Ordinary non-runtime patch surfaces do not outrank Bloc merely because a patch file exists.

## 2026-09-29 — Authored function-unit compiler contract repaired

- Dedicated-runtime-first FORCE still produced 0 executable mutations for Anime-Ultime, Flemmix and MoviesMod, exposing a compiler/prompt contradiction rather than provider proof.
- Compact FORCE already instructed Qwen that a selected `function_unit` replacement is body-only, but authored `provider_patch`/`provider_js` compilation did not restore the selected function declaration. Only `provider_bloc` had deterministic envelope preservation.
- A correct body-only authored-runtime proposal was therefore rejected as helper deletion. The authored compiler now preserves the exact selected declaration/signature before structured-anchor resolution, just like generated Bloc.
- Authored function units may now retain a bounded exact anchor up to 1800 chars, matching the existing function-unit replacement bound. This matters for real provider `resolve`/search/terminal functions whose changed body exceeds the old 320-char anchor ceiling.
- Regression coverage includes a provider_patch function unit larger than 320 chars rewritten from a body-only model response while preserving `function resolve(...)`.
- Runtime-surface detection now also recognizes shared runtime patch wrappers via `MANAGED_FIX_ID = "PROVIDER.*.RUNTIME.*"`; this covers AnimeVOST-FR, whose provider patch delegates construction to a shared runtime helper and does not contain the direct resolver marker in the patch file itself.

## 2026-09-29 — FORCE scope diagnostics made durable

- Repeated 0-mutation trio runs showed that final `providerCount=0` is insufficient observability: a provider_patch rejection followed by a provider_bloc abstention collapses to the same external result as two clean abstentions.
- `plan_batch_from_checkout.py` now records a bounded `force_scope_trace` per provider with only scope, outcome, deterministic rejection reason and exception type; no prompt, source bytes, private memory, URLs or credentials are retained.
- The guidance workflow sanitizes that trace into `guidance/niakvio-force-diagnostics.json`, validates that private content/URLs/tokens/cookies are absent, merges it page-by-page alongside advisor/Force artifacts and publishes it with no proof or publication authority.
- This diagnostic file is operational evidence only. NiakVIO sandbox/playback/identity gates remain the sole candidate acceptance authority.

## 2026-09-29 — Clean abstentions proved context-selection debt

- Diagnostic trio run on Brain `e7abe3799cd7922212304b5254bbab82ef70d932` completed 3/3 with 0 mutations.
- Durable diagnostics proved all six scope outcomes were clean abstentions: Anime-Ultime, Flemmix and MoviesMod each abstained on `provider_patch` and then `provider_bloc`; there were no compiler/syntax/anchor rejection codes.
- Deterministic unit audit showed the provider_patch surface was real but too local: Anime-Ultime exposed `resolve + request`, Flemmix `resolveTabs + resolve`, MoviesMod `resolve + request`. Important direct helpers such as Anime-Ultime `search/player` and MoviesMod `candidateDownloadLinks/modLinks` were omitted from the four-unit budget.
- `_force_edit_units` now reserves its strongest whole functions and then follows one level of the exact local JS call graph before filling remaining micro-units. Direct callees are ranked by causal role tokens while keeping the same bounded unit count and exact-byte authority.
- This is context diversity, not a proof shortcut. The model still edits one exact unit; Brain still compiles/validates it; NiakVIO still owns isolated playback/identity/non-regression proof.

## 2026-09-29 — Current FORCE abstentions were generated without current targeted shape evidence

- Current NiakVIO census authority is `36531469863-retest`, while the tracked targeted-recovery snapshot was still pinned to `sourceCensusRunId=36320455627`.
- `request_from_checkout()` correctly discards that stale targeted snapshot. The recent clean FORCE abstentions therefore had current census/residential replay causality but not the bounded current response-shape/network observations added for structural synthesis.
- This is not evidence that the dedicated runtimes are unrepairable. A full 13-provider targeted refresh has been triggered on NiakVIO before the next authoritative FORCE cycle.
- Freshness remains census-epoch based: the persisted targeted artifact is accepted when its `sourceCensusRunId` equals the current census `runId`; it does not need to share the exact later evidence-persistence commit SHA.


## 2026-09-29 — NiakVIO causal queue split reduced provider FORCE cohort to 8

- NiakVIO same-census targeted transport projection reduced the automated provider repair queue from 13 to **8** without promoting any provider status.
- Current provider-mutation cohort: `4khdhub, allanime, anime-ultime, animesultra, animevost-fr, moviebox, vidfast, yflix`.
- Current explicit targeted WAF/transport-owned cohort: `allwish, animesalt, flemmix, mallumv, moviesmod`.
- The five transport-owned providers retain their semantic proof but must not consume provider FORCE budget while `transportRepairEligible=false`; they remain candidates for browser/native/residential transport requalification.
- Plain HTTP 403 is not sufficient to remove provider mutation authority. Anime-Ultime and VidFast remain in the provider cohort because their targeted classification is `provider_network_http_error`, not explicit `provider_waf_challenge`.
- Future FORCE guidance must use the 8-provider census repairQueue rather than replaying the stale 13-provider cohort.


## 2026-09-29 — Residential replay supersedes narrow WAF seeds for four providers

- Fresh NiakVIO WAF/residential evidence run `36541459500` proves that narrow challenged seed requests are not always the causal provider blocker.
- `allwish, animesalt, flemmix, moviesmod`: full provider replay through the residential exit completes identity-safe and stops at `provider_zero_before_provider_network`; keep normal provider failure classification and allow FORCE/Repair.
- `mallumv`: remains transport-owned as `HARNESS/ENV BLOCKED` / `residential-exit-all-challenged`; do not spend provider mutation budget on it until stronger transport evidence changes ownership.
- Current FORCE provider cohort is therefore **12**: `4khdhub, allanime, allwish, anime-ultime, animesalt, animesultra, animevost-fr, flemmix, moviebox, moviesmod, vidfast, yflix`.
- The adapter already implements the required precedence: `targeted_provider_waf && replay_provider_signal` preserves the normal provider failure class rather than forcing a transport gap.


## 2026-09-29 — Adaptive replay sample causality must survive summarization

- NiakVIO residential full-provider replay exposed an evidence-loss bug: the persisted replay row carried only the lane-level `debugStage`, which is the final adaptive fixture's stage, while earlier fixture stages lived only in `samples[]` and were discarded.
- A later `provider_zero_before_provider_network` fixture could therefore make Brain believe a replay was clean even when an earlier fixture had already reached `provider_waf_challenge` or timeout.
- Brain now retains privacy-safe `sampleDebugStages` / `sampleStatuses` from the NiakVIO replay artifact and requires the **entire adaptive sample set** to be free of WAF/timeout before full replay may outrank a targeted WAF seed.
- `build_causal_prior()` and `request_from_checkout()` both enforce this rule. A regression test proves an earlier WAF sample keeps the causal layer on harness even when the final lane stage is pre-network zero.
- Guidance generated from the older summary contract (including the already-triggered `213ebeb...` cycle) has no application authority for providers whose WAF ownership depends on that lost sample history. Re-run after fresh sample-aware residential evidence.


## 2026-09-29 — FORCE context follows second-hop runtime callees

- The earlier call-neighbor fix followed only one local function hop. That is still insufficient for common provider runtimes such as MovieBox, where `resolve()` calls `current()`, and `current()` owns parser/network helpers such as `currentRows()` / `jsonGet()`.
- FORCE editable-unit selection now performs a bounded breadth-first traversal to depth 2 over exact local function calls, while retaining the existing maximum editable-unit budget and exact-byte mutation authority.
- Depth-1 callees remain preferred; depth-2 callees are tagged `causal_call_neighbor_depth2` and are still selected only from provider-owned complete functions already present in the authored runtime.
- Regression coverage reproduces `resolve -> current -> currentRows/jsonGet` and requires at least one second-hop helper to be exposed.
- This is context exposure only. It does not authorize a mutation or provider promotion; NiakVIO isolated playback/identity/non-regression gates remain mandatory.


## 2026-09-29 — Final sample-aware WAF replay restores 13-provider FORCE authority

- NiakVIO follow-up residential replay now contains sample-aware adaptive evidence for the explicit five prior seed-WAF providers.
- AllWish, AnimeSalt, Flemmix and MoviesMod have four adaptive fixtures per active lane, with `sampleDebugStages` containing only `provider_zero_before_provider_network`; MalluMV has one available fixture with the same stage. No persisted adaptive sample shows WAF or timeout.
- The earlier browser/direct/OkHttp challenge seeds remain factual but are not the causal blocker for the current full provider runtime.
- Current authoritative provider-mutation cohort is therefore 13: `4khdhub, allanime, allwish, anime-ultime, animesalt, animesultra, animevost-fr, flemmix, mallumv, moviebox, moviesmod, vidfast, yflix`.
- The older `213ebeb...` 12-provider cycle predates both sample-aware causality and second-hop FORCE context and has no final authority for this cohort.
- Next authoritative FORCE must use current Brain main with second-hop runtime callees and NiakVIO source at or after the sample-aware WAF persistence.


## 2026-09-29 — Structural FORCE reserves one second-hop edit slot

- The first second-hop call-graph implementation discovered depth-2 runtime helpers but still sorted every depth-1 callee ahead of every depth-2 callee.
- With the normal 4-unit FORCE budget (2 strongest whole functions + 2 remaining slots), a dispatcher with several direct callees could therefore consume the whole budget before the parser/player/terminal helper behind an intermediate function was exposed.
- Current Brain main reserves one remaining slot for the strongest `causal_call_neighbor_depth2` on `route_proven_gap` / `chain_terminal_gap` when the normal 4-unit budget is available, then fills the rest by the existing ranking.
- Regression coverage reproduces a crowded `resolve -> current/legacy/decorate/metrics` surface where only `current -> terminalParser` owns the terminal parse and requires that depth-2 helper to survive selection.
- This change does not alter mutation authority, exact-byte anchoring, syntax guards or NiakVIO sandbox proof. The already-running authoritative 13-provider FORCE remains pinned to its earlier Brain SHA; this fix is fallback architecture for a subsequent rerun only if needed.

## 2026-09-29 — FORCE page-1 exposed async drift, scope timeouts and continuation deadlock

- Fast Repair run `36545761845` visited the current 12 deterministic provider-owned Fast cohort and produced **0 candidates / 0 validated repairs**. Stop reason is `experiment_variants_exhausted`, not timeout; all 12 were handed to Learning.
- FORCE cycle pinned to Brain `e2aef03ef3c587b0a0e04f888515a30d96f4e0e5` published page 1/2 for 8 of 13 providers. It emitted one raw mutation for AnimeSalt: changing synchronous `req(a)` into `async function req(a)`.
- That mutation is invalid: AnimeSalt `resolve()` calls `var q=req(a)` synchronously and immediately reads `q.tmdbId`; changing `req` async turns `q` into a Promise. No repair authority was granted.
- Brain now rejects any explicit existing function declaration whose asyncness/name/parameter signature differs from the selected exact function unit. NiakVIO's Force receiver independently compares named function signatures before/after authored file mutations and rejects signature drift, restoring the original file on failure.
- Page-1 diagnostics also showed `provider_bloc` TimeoutError fallbacks on 4KHDHub, AllAnime, AllWish, AnimeSultra and Flemmix. Root cause was budget geometry: workflow/provider cap 360s for route failures and only 120s for provider_transport_gap, while sequential provider_patch/provider_bloc scopes can each need a full model call/retry.
- Current Brain raises the workflow provider budget to 600s, ROUTE/CHAIN provider budget to 600s, provider_transport_gap to 300s and transport_environment_gap to 180s. Page size 8 with 2 workers remains within the 60-minute workflow bound.
- A separate pagination defect was confirmed: continuation pages are pinned to the cycle's Brain SHA, but publication rejected that pinned SHA once Brain main advanced after page 1. The publication guard now allows only **same Brain SHA + same NiakVIO SHA + existing incomplete guidance state** to continue across main advances; unrelated stale cycles remain rejected.
- New authoritative 13-provider FORCE cycle is triggered at Brain `cc710af13cd07943db98b00aafb66975261af9e3` against NiakVIO `7fca1b606f6edc9b31a40bacd6f16e97d2dbf0d2`.


## 2026-09-29 — Fast exhausted; invalid FORCE candidates guarded; stalled continuation bypassed

- NiakVIO Fast Repair run `36545761845` visited the 12 provider-owned Fast targets and produced **0 candidates / 0 validated repairs** with `experiment_variants_exhausted`; this is a real strategy exhaustion, not a timeout. All 12 were handed to Learning.
- FORCE candidate AnimeSalt (`function req -> async function req`) was rejected as invalid because its synchronous caller uses `var q=req(a)`; changing asyncness turns `q` into a Promise. Brain now preserves existing function asyncness/name/parameter signature.
- FORCE candidate AllWish was also rejected: it replaced the complete network helper body (fetch/status/return) with a side-effect-only referer assignment referencing unrelated locals. Brain now rejects network helper rewrites that discard request return semantics.
- The timeout-safe 13-provider cycle published only page 1 and its automatic continuation did not persist a second page. That continuation path is therefore not trusted for the current repair attempt.
- Current workflow default is a single **9-provider page** with a 180-minute job timeout for the remaining cohort. The first four prior-cycle providers are already adjudicated (4khdhub/allanime/anime-ultime abstained; AllWish candidate invalid), so the active FORCE target is: animesalt, animesultra, animevost-fr, flemmix, mallumv, moviebox, moviesmod, vidfast, yflix.


## 2026-09-29 — Provider fixes must be Brain-authored

- NiakVIO briefly hand-edited six provider runtime Lego files while investigating the 13-provider cohort. Those edits were reverted byte-for-byte and are not repair evidence.
- Architectural boundary is explicit: Brain/LLM authors provider-local mutations; NiakVIO owns evidence, isolated application, Deep/Retest, playable/identity proof, non-regression, census and publication.
- Plausible provider-local edits discovered by orchestration are input evidence only. They must be synthesized through the Brain mutation path before they can become a candidate.
- Infrastructure/receiver/harness/Core changes remain allowed when they repair the repair mechanism rather than a specific provider.

## 2026-09-29 — FORCE compiler/call-graph recovery is CI-green

- Last complete 13-provider FORCE on Brain `7f343311...` published diagnostics for all 13 but **0 executable mutations**. Rejections clustered around `helper_declaration_removed`, `causally_empty_deletion`, `no_op`, and one MovieBox timeout.
- Root cause in compact FORCE compilation: a selected exact `function_unit` could be discarded when the small model returned a complete function wrapper using a nearby helper name instead of the selected declaration. Generated `provider_bloc` now treats a single complete syntax-valid wrapper as transport noise, extracts its body, and deterministically reuses the exact selected function identity. Authored `provider_patch` / `provider_js` still fail closed on explicit async/name/parameter signature drift.
- Editable-unit selection now hard-enforces the requested unit budget and, for structural gaps, reserves one strongest causal root instead of consuming slot 2 with an unrelated generic helper.
- The causal call graph now follows both direct calls and named callbacks such as `.then(parser)`, `.map(normalize)`, etc., so second-hop parser/player/terminal helpers remain visible under the normal four-unit prompt budget.
- Guidance workflow contracts are synchronized with current execution: page size 9, structural provider budget 600 s, and four-file guidance publication including FORCE diagnostics.
- Brain CI run `36582057653` / job `109452493685` is **green** at commit `e5bbe01b5725acc70dc9602c02cd97074f805ec1` (189 tests). This validates the repair mechanism only; no provider is marked repaired until a fresh Brain mutation survives NiakVIO isolated playable/identity/non-regression proof.

## 2026-09-29 — Witness strategy: first executable mutation exposed wrong fallback surface

- Fleet-wide 13-provider FORCE is no longer the progress metric. The current milestone is one Brain-authored provider repair surviving NiakVIO sandbox/playback/identity proof; witness provider: `4khdhub`.
- Isolated Brain run `36589827785` produced the first executable FORCE mutation after compiler recovery. This proves the pipeline crossed the prior `providerCount=0` barrier.
- The candidate was intentionally rejected as non-causal: its provider_bloc anchor was generic ProviderBase `_routeKind`, while its replacement body behaved like URL extraction. It did not target 4KHDHub's dedicated runtime.
- Root architecture defect: `runtimeMutationSource` spanned the generic provider base plus provider-local Blocs, so generic helpers could outrank a registered `PROVIDER.<ID>.RUNTIME.*` Bloc even when a provider-specific repair script already owned the runtime.
- Brain now retains exact published provider Bloc bytes internally, maps registered patch-script `MANAGED_FIX_ID` values to their matching materialized Bloc, prioritizes `.RUNTIME.` ownership, and exposes `preferredRuntimeMutationSource` / `preferredRuntimeMutationBlockId`.
- Both FORCE prompting and mutation compilation use that preferred runtime source before generic `runtimeMutationSource`. Tests prove the prompt and minimized mutation anchor cannot fall back to generic `_routeKind` when a dedicated runtime Bloc is available.
- NiakVIO targeted evidence now supplies bounded/sanitized HTML class/id tokens. 4KHDHub current search HTML still exposes `movie-card`, `movie-card-title`, `movie-card-format`, and `movie-card-meta`, while the runtime still ends after the search response with `provider_network_zero_result`. Therefore a blanket “markup classes changed” hypothesis is not supported.
- Targeted DOM structure is additionally surfaced as shallow `structureHints` in the Brain observation so compact FORCE cannot hide it inside deeply clipped network rows.
- Brain CI is green through `1b12a27eb4e28e119e43351b65d64dfd7da94d83`. No provider is repaired yet; the next authoritative run must be a frozen one-provider 4KHDHub cycle followed by NiakVIO isolated proof if a causal mutation is produced.


## 2026-09-29 — 4KHDHub witness: 3B conclusively no-op; FORCE escalated to CI-green 7B

- Single-provider witness policy is active: do not expand back to the 13-provider cohort until one Brain-authored provider mutation survives NiakVIO isolated sandbox playback/identity/non-regression.
- Witness evidence for `4khdhub`: TMDB movie/tv metadata returns HTTP 200; `4khdhub.one` search returns HTTP 200 with 42 movie / 31 tv anchors and current structural tokens including `movie-card`, `movie-card-title`, `movie-card-format`, `movie-card-meta`; provider still returns zero streams and no detail-provider request is observed.
- Qwen2.5-Coder-3B Q4 witness runs are now conclusive negative evidence. After compiler/signature/call-graph fixes and prompt contraction, the model completed all attempts without transport timeout but returned only no-op edits across provider_patch/provider_bloc. Do not add more 3B retries for this witness.
- FORCE inference is escalated to `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M` in the Private-Guided Advisor only. Runtime context is 16k, one llama slot, Force max output 512 tokens, timeout 240s.
- `route_proven_gap` compact FORCE now exposes exactly two causal function units (one structural root plus its strongest causal callee); chain/media failures retain their wider/deeper call graph budget.
- Targeted current evidence is compacted for FORCE to debug/status/playable/verified/sampleTitles/structureHints plus a small network summary instead of the full network payload.
- CI is green at Brain `31f71531a4ab8954c80bde2d02c959a1a0d53077` after updating all historical 3B/32k/768-token workflow contract tests. The next witness run must use a Brain SHA at or after this green revision.


## 2026-09-29 — 4KHDHub witness now has evidence-aware DOM repair focus

- Fresh NiakVIO targeted evidence run `36605262984` proved current TMDB + provider HTTP 200 with zero streams and exposed privacy-safe structural facts for the live 4KHDHub search document.
- The page contains the exact class `movie-card` together with a dense prefix family (`movie-card-format`, `movie-card-content`, `movie-card-formats`, `movie-card-image`, `movie-card-meta`, `movie-card-overlay`, `movie-card-title`). NiakVIO's current runtime uses word-boundary class regex helpers, so hyphenated siblings can be overmatched as full cards.
- FORCE previously selected units only from the generic `route_proven_gap` taxonomy. It did not use current structural hints to choose the two route-gap edit units, which allowed the 7B witness to spend its budget on irrelevant/no-op code.
- Brain now derives bounded `structural_focus` from targeted HTML class-prefix collisions and prepends generic DOM helper focus (`classblocks`, `classtext`, selector/class token) plus the observed colliding class token. Source windows and editable-unit ranking consume this focus.
- Lane-prefixed hints such as `movie:classes=...` are explicitly parsed; the initial implementation missed the colon separator and the regression test caught it.
- CI is green at `95e6f01d41c89997bc3bf6e6243a9fadae1e2624`. Regression coverage requires a `movie-card` / `movie-card-*` collision to expose `classBlocks` and `classText` within the two-unit route-gap budget.
- This remains **repair guidance only**. No 4KHDHub provider mutation is validated yet; the next authoritative step is a single-provider 7B FORCE run against the current NiakVIO evidence, followed by NiakVIO sandbox playback/identity/non-regression proof.

### 2026-09-29 — Provider hand-patch prohibition
- Manual/provider-specific source fixes are diagnostic evidence only; they are not an acceptable terminal Brain Repair result.
- When a provider-specific defect reveals a reusable mechanism, the Brain must generalize it into a provider-agnostic profile/strategy/layer, then generate the provider mutation itself.
- Assistant/manual work may modify Brain infrastructure, orchestration, guards, profiles, tests and generic capability code when the Brain cannot execute; it must not retain a hand-written provider patch as the production repair.
- Publication authority remains current-byte sandbox + playable media + identity + non-regression proof. A hand patch that passes locally is still non-authoritative until reproduced through the Brain pipeline.
- This rule exists to keep NiakVIO scalable to hundreds of providers and to prevent repeated assistant-side repairs that bypass learning.


## 2026-09-30 — Balanced HTML class-container synthesis closes the 4KHDHub structural evidence gap

- Historical deterministic FORCE mutation `exact_class_token_boundary` was real and executable, but NiakVIO current-byte FORCE validation rejected it because it still produced zero playable movie/tv streams. It corrected only CSS token-prefix overmatch (`movie-card` vs `movie-card-*`).
- Fresh current evidence exposes a second, generic DOM-parser failure mode: the exact container class itself can occur on multiple nested tag types. 4KHDHub's current `movie-card` facts show count=12, tags spanning `a/div/span`, nested anchors, and only one self href, so slicing a class block at the next same-class start can truncate the parent card before its title/link even after prefix matching is exact.
- Brain deterministic structural FORCE now recognizes that bounded evidence pattern generically and can synthesize `balanced_class_container`: preserve exact class-token matching, then extract the selected element through its balanced matching closing tag instead of ending at the next same-class start. No provider id, route, domain or media fixture is encoded in the mechanism.
- The simpler `exact_class_token_boundary` remains the deterministic fallback when evidence proves only a prefix-family collision.
- Brain CI run `36689581429` is green at `dbddadd5fc17c1a7fb3a3141306b9da194083cf0`: **199 tests passed** plus public-repository privacy audit. Regression coverage includes the mixed-tag/nested-container structural case.
- This is still repair capability, not provider proof. 4KHDHub must be replayed through external guidance and then NiakVIO explicit FORCE current-byte sandbox/playback/identity/non-regression before any census promotion.


## 2026-09-30 — Fleet-scale repair pivots from provider loops to repair families

- The unchanged **27 FULL OK · 2 PARTIAL OK · 13 Repair** census after repeated 7B cycles proved that provider-by-provider synthesis cannot be the scaling model for the planned 700–800-provider fleet.
- Added provider-independent `repair_family` identity derived from failure class, status, media types, allowed mutation surfaces and privacy-safe current structural/network signals. Provider id/domain/route literals are excluded from the family identity.
- Repair batch output now persists `repair_family` and reports `repairFamilyCount`, family histogram and providers-per-family so compute cost can be measured against causal families rather than raw provider count.
- Experience retrieval now strongly prefers sandbox-validated same-family experience across providers. NiakVIO Force artifacts carry `repairFamily` + `mechanismFamily`; accepted sandbox outcomes are persisted into `validatedFamilies` with `autoApply=false` and no proof/publication authority.
- Brain imports those validated family mechanisms as cross-provider experience. For supported deterministic mechanisms, routing now enters `family_replay` before any LLM call, recompiles the mechanism against exact current provider bytes, and still requires the ordinary NiakVIO isolated sandbox/playback/identity/non-regression gates. If deterministic recompilation cannot express the mechanism on the new bytes, only that provider escalates to the LLM.
- This creates the required fleet asymmetry: the expensive work should converge toward **repair families + exceptional providers**, not one full reasoning cycle per provider.
- Current Force memory still has zero accepted mutations, so `validatedFamilies` is initially empty. The new replay path becomes active only after real NiakVIO sandbox acceptance; no historical failure or merely-functional provider is promoted into replay authority.


## 2026-09-30 — Current 13-provider queue collapses to 5 causal repair families

- Fleet-scale validation on the authoritative 13-provider Repair queue confirmed the repaired family taxonomy reduces the current novelty surface from **13 providers to 5 causal families** before any positive family library exists.
- Current family distribution from authoritative census + structural evidence:
  - 7 providers: `route-proven-gap:route-parser`
  - 2 providers: `route-proven-gap:dom-selector-container`
  - 2 providers: `chain-terminal-gap:dom-selector-container`
  - 1 provider: `chain-terminal-gap:terminal-extraction`
  - 1 provider: `provider-transport-gap:provider-transport`
- Family-wave therefore spends novel Force/LLM work on at most one rotating representative per unresolved family and defers siblings. Negative-memory burden rotates the representative; e.g. repeatedly rejected 4KHDHub must not monopolize the DOM family.
- This is an architecture/scaling validation only. The provider census remains **27 FULL OK · 2 PARTIAL OK · 13 Repair** until a representative mutation survives NiakVIO sandbox/playback and is persisted as a validated family mechanism.
- Advisor run `36738108323` is the first live 13-provider run using the coarsened causal taxonomy and exact current NiakVIO source `a2be5abfb32cc3a5bdc3f82031f9611a0e851ce5`.

## 2026-09-30 — Family witnesses now rotate after Brain execution timeouts

- The previous first-valid family cycle published Brain guidance at `35313d64438445ab08d39bfe733a3f1214896257` against NiakVIO `83fa2f956d8a9a12272603257520ba4687fee6e4`, but produced **0 executable mutations**. Its four persisted Force diagnostics were execution failures rather than accepted/rejected provider repairs: AllAnime, Anime-Ultime and MoviesMod timed out on both provider_patch/provider_bloc; AllWish timed out on provider_patch and exhausted its provider budget before provider_bloc.
- Root scaling defect: family witness rotation consumed only NiakVIO provider-failure memory. Brain-side model/runtime timeouts were therefore invisible to the next family wave, so a witness that could not produce a model verdict could monopolize its family again. This is unacceptable for the planned hundreds-provider fleet.
- `select_family_wave()` now accepts a separate `provider_execution_burden`. For an unresolved family, a generation-blocked witness is skipped when an unblocked sibling exists; evidence strength and provider semantic-failure burden rank the remaining executable witnesses. If every sibling is execution-blocked, the least-blocked witness is retried, so the family is never silently suppressed.
- `select_niakvio_repair_family_wave.py` now derives execution burden from the previously published sanitized Force diagnostics (`TimeoutError`, model timeout, or provider-budget exhaustion) without recording those events as provider-code failures. The Private-Guided workflow fetches that prior diagnostic before family selection and persists the family-wave report as an artifact.
- Regression coverage proves both rotation to a fresh sibling and the all-blocked least-burden fallback. Brain CI run `36761626368` completed **SUCCESS** on `aa8ee4f2a855b2540e9d4c1f7be2615ecff72934`.
- Authoritative timeout-aware family cycle: Private-Guided Advisor run `36761626391`, Brain `aa8ee4f2a855b2540e9d4c1f7be2615ecff72934`, exact NiakVIO source `eec281c0d5d0032bb9c3916546ae14e2e96f05fb` (5.21.86). At checkpoint time the exact cohort, family-wave, paging, private-memory build and routing steps had succeeded; 7B inference had not yet completed. No provider repair is claimed from this architecture change.

## 2026-09-30 — Provider family composition architecture is now explicit and RAG-indexed

- NiakVIO now owns `PROVIDER_FAMILY_ARCHITECTURE.md`, a canonical diagram of Provider v3 composition: ProviderBase + provider DATA + reusable provider-family Blocs + provider-personal runtime + ordered CORE Blocs + minimizer + sandbox/proof.
- The document explicitly separates three ownership scopes: **GLOBAL Core**, **FAMILY reusable provider mechanisms**, and **PERSONAL provider DATA/runtime**. A provider repair must not move Core responsibilities (security, identity, HLS integrity, sanitizer, presentation, StreamScore, telemetry) into a provider-local runtime.
- It also separates **runtime/protocol families** from **causal repair families**. Providers may share a repair mechanism without sharing a runtime, and providers sharing a runtime family may have different causal failures.
- Brain public document retrieval now indexes `ARCHITECTURE.md`, `BRAIN_REPAIR_ARCHITECTURE.md` and `PROVIDER_FAMILY_ARCHITECTURE.md` with high authority so future synthesis sees this ownership model directly.
- Family cardinality is **dynamic evidence**, not an architectural constant. Historical/coarsened classification produced a 5-family snapshot, while live Advisor run `36738108323` logged `input=13 selected=4 families=4` on its exact source. Do not hardcode 4 or 5; derive families from the current request/evidence and persist the exact run-local report.
- The scaling invariant remains: expensive synthesis should trend with **novel causal mechanisms + exceptional providers**, not raw provider count. A validated family mechanism is recompiled against each sibling's exact current bytes and still requires that sibling's own playback/identity/non-regression proof.

## 2026-09-30 — Route proof is now projected directly into runtime synthesis

- Root scaling defect confirmed while auditing the unresolved family wave: NiakVIO already stores rich provider route knowledge in `provider-overrides.json` (learned/candidate routes, structured request plans, canonical execution preferences and live-route evidence), but Brain prompt construction previously exposed that data mainly through a clipped serialized override. The advisor view could reduce the override to ~600 characters, and oversized prompts could drop larger provider sources entirely. A provider could therefore be classified `ROUTE PROVEN` while Qwen still had to rediscover the actual route contract from small code windows.
- `provider_context.py` now derives a sanitized, provider-local `route_contract` containing capability, route-data state, learned/candidate routes, structured request-plan method/role/lanes/non-sensitive header names, canonical route preference, and compact live/proven route counts.
- Full URLs are reduced to route paths for this projection; sensitive query fields such as authorization/cookie/token/secret/password/api-key values are redacted. Authorization/Cookie header values are never copied into the contract.
- `prompting.py` now preserves `route_contract` in normal advisor prompts, preserves it through the hard prompt-budget fallback, and injects it as `current_route_contract` in Force synthesis beside exact editable runtime units.
- This changes the critical path from “ROUTE PROVEN -> model rediscovers route from clipped context” to “ROUTE PROVEN -> explicit compact route contract -> provider-local runtime synthesis -> NiakVIO sandbox proof”.
- Regression tests cover context extraction, sensitive-header omission, normal prompt retention, Force prompt retention and retention under the 7.6k-character budget. Brain CI run `36764118314` completed **SUCCESS** on `14d424162e44b2cfcf0a07200fcec6a694e87c9f`.
- This is an infrastructure/Brain fix only. It does not claim any provider repaired until an emitted mutation survives NiakVIO current-byte sandbox, playback, identity and non-regression validation.

## 2026-09-30 — Exact runtime Bloc now precedes generator-level FORCE

- Authoritative family wave `36770882785` on Brain `179833dc1a6d49ffff8ff0c4b1865e09b498e4fe` against NiakVIO `23e85730670a513eda2b9a5bf5993434d0a75c04` selected four family witnesses: `allwish`, `flemmix`, `mallumv`, `moviesmod`.
- The route-first guard worked: `allwish` routed to `probe` / Recognition with zero LLM mutation because current status was `NO PROOF`.
- The remaining three providers had sufficient route authority, but the 7B FORCE phase produced **0 executable mutations**. MalluMV consumed its 600 s provider budget across generator/runtime attempts; Flemmix and MoviesMod each returned an initially invalid edit then timed out on validation correction. Published Force diagnostics recorded only abstention/timeouts.
- Root execution defect: structural route/terminal repairs still tried the Python provider generator (`provider_patch`) before the exact materialized provider runtime Bloc, even though `preferredRuntimeMutationSource` already identifies that Bloc as the most causal current-byte runtime surface.
- `scripts/plan_batch_from_checkout.py` now makes exact provider `provider_bloc` the first FORCE scope for structural gaps when `runtime_template_prior.reuseBeforeNovelBloc=true`; generator-level `provider_patch` remains bounded fallback only.
- `prompting.py` now recognizes an exact materialized runtime template and contracts chain/media FORCE to one source window and at most two causal editable units. This preserves the current runtime skeleton and asks Qwen only for the smallest missing hook/logic instead of reconstructing a larger generator/runtime graph.
- Brain CI run `36773724337` completed **SUCCESS** on `32eb8322191cc7019cbc0a63c502dbc499839abc`.
- No provider is claimed repaired from this change. Next proof is a fresh family-wave against current NiakVIO followed by isolated current-byte NiakVIO sandbox if an executable mutation is emitted.

## 2026-09-30 — Recent sandbox negatives now reach deterministic provider-Bloc synthesis

- Family replay after the exact-runtime-first correction still republished the already rejected 4KHDHub `balanced_class_container` mutation. The emitted mutation fingerprint was exactly `c58fcb7a9610234bd647002fc01de4f73657de2028c166b270814f638c9a3989`, already present twice in NiakVIO `automation/brain-llm-force-memory.json` with rejected playable proof.
- Planner-side negative-memory blocking was already extended to `provider_bloc`, but live execution proved the relevant rows never reached the planner. Root cause was adapter truncation order: Force memory is append-oriented, `_provider_force_negative_memory()` returned oldest-first, while `request_from_checkout()` injects only the first four rows into `brain-force-sandbox-memory`. The newest 4KHDHub Bloc rejections sat beyond that prefix.
- `_provider_force_negative_memory()` now walks execution memory newest-first, de-duplicates by mutation/context fingerprint, and retains up to eight recent safe rows. The bounded Repair observation therefore receives the four most recent executed sandbox verdicts, including provider-Bloc mutation fingerprints.
- Regression coverage proves both helper ordering and end-to-end `request_from_checkout` observation injection. Brain CI run `36777402352` completed **SUCCESS** on `547c31a21aaf55b2397a9921126cb36ffd679b74`.
- Fleet execution was also tightened: for structural `ROUTE PROVEN` / `CHAIN REACHED` providers with an exact runtime template, the family wave now tries only the exact materialized provider Bloc in that turn; it no longer falls back to rewriting the Python generator in the same witness attempt. Budgets are capped at 240 s for route-proven gaps and 300 s for chain/media-terminal gaps before witness rotation.
- These are Brain/pipeline corrections only. No provider is repaired until a genuinely new mutation survives NiakVIO exact-current-byte application, rematerialization, playback/identity and non-regression validation.

## 2026-10-01 — FORCE 5.21.90 timeout root cause narrowed; deterministic runtime progression repaired

- Authoritative Private-Guided Advisor run `36793222486` (#211) used Brain `27fa6800ca83f696560bab2b6e5262b25dcf6592` against exact NiakVIO `a9eee1bda5b95e1c0bf10e9194e31e9808a48b7c` / release 5.21.90. Family-first selected `4khdhub`, `allwish`, `flemmix`, `moviebox` and published **0 executable mutations**.
- AllWish correctly abstained because current status is NO PROOF. The three synthesis-eligible witnesses were generation-blocked: MovieBox provider_bloc retry timed out at ~120 s, 4KHDHub timed out at ~180 s plus a ~58 s retry, and Flemmix provider_bloc retry timed out at ~120 s.
- 4KHDHub exposed a more specific Brain defect before the LLM fallback: the already rejected balanced-class-container mutation was correctly blocked by recent sandbox negative memory, but deterministic progression logged `class_text_boundary` as missing even though the current registered runtime contains a complete one-line `classText()` helper. The helper includes JavaScript RegExp braces, which the lightweight window/function scanner could misinterpret or clip.
- Brain now scans exact registered current source for complete one-line JavaScript functions before the prompt-window extractor when advancing deterministic class-selector repairs. This scan is full-source, provider-agnostic and accepts no invented network facts. It lets negative-memory progression inspect the next exact provider-owned helper without spending a 7B call merely to rediscover it.
- Internal deterministic synthesis `ValueError` is now isolated and logged as `FIELD_BRAIN_FORCE_DETERMINISTIC_ERROR`; it no longer masquerades as model validation feedback and prematurely sends a provider into the shorter validation-retry budget.
- CPU-bound provider_bloc generation is tightened to 320 primary tokens and 256 retry tokens; retry is genuinely smaller instead of inheriting the larger primary floor. Provider_bloc validation retry timeout is 150 s. The compact Force system contract is shorter and provider_bloc replacement grammar is capped at 1200 chars.
- Regression development exposed and fixed an over-escaped Python regex in the new full-source scanner itself. Final Brain CI run `36795452244` (#1240) is SUCCESS on `726bee69078d552c5e55825660e84021cffac4ea`, including unit tests and public-repository privacy audit.
- No provider repair is claimed from this Brain change. Next authoritative proof is a fresh family-wave against exact NiakVIO 5.21.90, followed by NiakVIO isolated current-byte sandbox/playback/identity/non-regression if a new executable mutation is emitted.

## 2026-10-01 — 4KHDHub witness #212 exposed selector/container ambiguity; deterministic progression disambiguated

- Private-Guided Advisor run `36797012326` (#212) used Brain `0a63804bbddb258fa69aea473d17df690cc62c94` against exact NiakVIO `a9eee1bda5b95e1c0bf10e9194e31e9808a48b7c` / 5.21.90 with **4KHDHub as the only witness**. It still published 0 executable mutations.
- Negative memory worked: the already executed/rejected structural provider-Bloc mutation was blocked. However deterministic progression again logged `FIELD_BRAIN_FORCE_DETERMINISTIC_NEXT_MISSING ... mechanism=class_text_boundary`, then fell back to Qwen 7B and timed out at ~180 s plus a ~58 s retry.
- Root cause was not missing current bytes. The full-source scanner now sees both one-line helpers, but both `classText()` and `classBlocks()` satisfy the generic class-selector signature (class parameter + `.replace()` + `class=`). The progression required a unique candidate, so the valid text selector was rejected as ambiguous with the already-treated container/list extractor.
- `_deterministic_class_text_boundary_mutation()` now excludes clearly container/list-oriented helpers when compiling the **text-boundary** progression: bounded generic signals are `starts=[]`, `starts[i+1].at`, or `out.push({html:`). This is provider-independent and prevents retrying a container extraction mechanism as a text-selector repair.
- Regression coverage uses separate one-line `classText` and `classBlocks` helpers and proves that only the changed `classText` lines receive the negative-lookahead boundary while `classBlocks` remains context-only.
- Brain CI run `36798005400` is **SUCCESS** on `6270d1a9aeee37782d7c75c25ad8b3d774b7920d`, including the full unit suite and public-repository privacy audit.
- No provider repair is claimed yet. Next proof remains a frozen single-provider 4KHDHub Advisor replay on this green Brain SHA, then NiakVIO isolated current-byte sandbox/playback/identity/non-regression if a new executable mutation is emitted.



## 2026-10-01 — Same-run FORCE portfolio budget and feedback closure

- Brain guidance run `36847662221` (#219, Brain `f15037022350affcd56964cae6e1e32e604da400`) proved that 4KHDHub's first deterministic candidate `exact_class_attribute_tokens` was generated immediately, but the requested four-candidate one-shot portfolio collapsed to one published candidate. Candidate 2 spent a 180 s model timeout, then returned a local no-op and consumed another validation timeout; candidate 3 repeated the same no-op/invalid-output path until the shared 600 s provider budget expired, so candidate 4 never started.
- NiakVIO Repair V6 run `36849661755` executed candidate fingerprint `a21eaa643f0c0df30a14cffe8bbb7d3bef3258ea9217de595565902b189eb974` on exact current 4KHDHub bytes, applied and rematerialized the provider, then reproduced `no_streams` on 8 fixtures with 0 streams and 0 runtime errors. The candidate is therefore real executed-negative evidence, not a propagation or harness failure, and is persisted in `automation/brain-llm-force-memory.json`.
- The Brain batch orchestrator now divides the remaining provider wall-clock budget across the remaining hypothesis slots, so one failed candidate cannot consume the time reserved for candidates 3/4. After a same-run candidate has been reserved, provider-Bloc model/validation calls use tighter <=90 s bounds and one validation correction.
- A transport timeout during validation correction no longer overwrites the underlying local rejection such as `no_op`, syntax or window mismatch. That causal rejection is carried into the next hypothesis as focused same-run feedback, while prior portfolio reservations and current census/targeted evidence are retained.
- Portfolio continuation is no longer limited to retryable transport errors: bounded local validation rejection or abstention can advance to the next causally distinct hypothesis. This is a Brain/pipeline correction only; it does not claim 4KHDHub repaired. Production proof still requires Brain-produced candidate(s) to pass NiakVIO current-byte movie + TV playable/identity validation.


## 2026-10-01 — One-shot portfolio replay armed on green Brain

- Follow-up test-contract commit `56eac04b4d25287b3af28b6c649d0e17b3302ee4` is green in Brain CI run `36851018731`: full unit suite and public-repository privacy audit passed.
- The next frozen 4KHDHub guidance replay targets NiakVIO `d6a3d6396b00ee1ea629e723eb83044cd249a261`, whose persisted Force memory already contains rejected executed fingerprint `a21eaa643f0c0df30a14cffe8bbb7d3bef3258ea9217de595565902b189eb974`.
- Success for this Brain replay is not workflow completion alone: logs must prove bounded per-candidate budgets/feedback continuation and the published artifact must contain causally distinct executable candidate(s), after which NiakVIO must apply/rematerialize/sandbox them on exact current bytes.


## 2026-10-01 — Preserve executed-negative memory across one-shot FORCE slots

- Guidance run `36851137203` (#220, Brain `57d809881df6b37c939e6ffbbebf2ac2304a04c0`) proved the new per-hypothesis wall-clock budgeting works: slot 1 was capped at about 150 s after a model timeout and slots 2–4 still executed in the same run.
- The run also exposed a Brain regression before any NiakVIO mutation escaped: `_carry_force_portfolio_feedback()` retained same-run reservations but dropped the `brain-force-sandbox-memory` observation. Slot 1 correctly blocked all previously executed-negative deterministic mechanisms, then slots 2–4 lost that blocker and re-proposed `balanced_class_container`, `class_text_boundary`, and the already rejected `exact_class_attribute_tokens` fingerprint `a21eaa643f0c0df30a14cffe8bbb7d3bef3258ea9217de595565902b189eb974`.
- The public sanitizer correctly failed closed with `providerCount=0`; no mutation was handed to NiakVIO and no provider bytes changed.
- Same-run portfolio feedback and within-candidate validation feedback now both retain `brain-force-sandbox-memory`. This keeps cross-run executed negatives authoritative while adding local rejection feedback. Portfolio telemetry reports `negative_memory_rows` so the next real run can prove the memory survived every slot boundary.
- This is a Brain pipeline correction only. 4KHDHub remains unrepaired until a new Brain-produced mutation survives publication and NiakVIO isolated current-byte movie + TV playable/identity proof.


## 2026-10-01 — Fourth deterministic route-gap hypothesis: optional format gate

- Brain guidance run 36852049405 (#221, Brain d7f57cb2b27be137ea87f47a3427af92ffb7f14f) proved cross-run negative memory now survives every one-shot slot: all previously executed 4KHDHub class-container mechanisms stayed blocked in slots 1–4. The remaining 7B path produced only timeout/no-op outcomes, so no Force mutation was published and NiakVIO provider bytes remained unchanged.
- Current exact 4KHDHub runtime contains a separate hard media-format gate inside the search/detail helper: an empty or unextractable format label rejects every otherwise identity-scored movie/tv card before detail traversal. Current evidence simultaneously reports live HTTP search/HTML structure and zero terminal result, so this is a distinct bounded causal hypothesis from the already rejected class-selector family.
- Brain now has a provider-independent deterministic optional_metadata_format_gate compiler. It only activates on an existing exact helper that already owns classBlocks, classText, anchors, scoreTitle and paired movie/tv format guards. It changes those guards from hard rejection on empty metadata to rejection only when a format value is present and contradictory. It does not change routes, hosts, title scoring, identity thresholds or terminal extraction.
- This is Brain capability, not a manual provider fix. It remains unproven until generated from current bytes, published, applied/rematerialized by NiakVIO, and accepted by isolated movie + TV playable/identity validation.


- Brain CI run 36859121754 on 96e1ec5e0fcf73b07d9cff97061a60bdda1d109a failed only because the new unit test expected the full function guard inside the emitted provider_bloc replacement. The deterministic compiler intentionally shrinks exact provider_bloc edits to the smallest unique structured anchor, so the mutation contained the correct transformed middle span rather than the whole helper. The test contract is aligned to the structured-anchor output; implementation bytes are unchanged.


## 2026-10-01 — Green format-gate Brain replay armed

- Brain CI run `36859284358` (#1292) is SUCCESS on `f380df914a1b75e17144546ccdf11a26c5d46818`: full unit suite and public-repository privacy audit passed after aligning the test with the structured-anchor compiler output.
- Next authoritative 4KHDHub guidance replay remains pinned to unchanged NiakVIO `d6a3d6396b00ee1ea629e723eb83044cd249a261`. The new deterministic `optional_metadata_format_gate` must be generated from exact current provider-owned bytes while all earlier executed-negative class-selector fingerprints remain blocked.
- No repair is claimed until the public Force artifact contains a novel executable candidate and NiakVIO isolated movie + TV playable/identity validation accepts it.


## 2026-10-01 — 4KHDHub Force format-gate executed negative; move to catalogue identity/query

- Brain #222 / guidance run `36859533598` on `b63821990e1eeb02f3edb327b8f84a6a1459e595` generated and publicly published the novel deterministic `optional_metadata_format_gate` candidate from exact NiakVIO `d6a3d6396b00ee1ea629e723eb83044cd249a261`. All older DOM/class mechanisms remained blocked by executed-negative memory across the same run.
- NiakVIO Repair V6 run `36861067528` (#254) applied that exact fingerprint `24c7624590ce10b4fb93bada35bd3b9f3b819dd944fbe334f08d9fd503156e41`, rematerialized 4KHDHub to `providers/4khdhub-ca30fc6ce33cfde8.js`, and reproduced the same real result before and after: 8 fixtures, 0 streams, 0 runtime errors, `content_lookup_completed_no_streams`. It was rejected for `required_category_playable_proof:movie,tv`; no provider mutation was published.
- The negative result is persisted on NiakVIO main `f90341b9d75c411c497b91706dc8291fb596005d`. That persistence commit changes evidence/status only, not accepted provider bytes.
- Current evidence now points above DOM parsing: the runtime searches localized TMDB titles and synthesizes `Season N` for TV, while current live evidence records queries such as `La Colonie 2021` and `Revenant Season 1` with HTTP 200 but no subsequent detail request. The same TMDB payload exposes original title/name fields, and the catalogue is English-oriented.
- Brain now has a provider-independent deterministic `catalog_identity_query_variants` compiler for this route-proven search/detail archetype. It preserves existing media-format, year, season and terminal identity gates, but performs at most six catalogue queries across localized/original title plus season/year/plain variants and scores returned cards against both canonical and original titles. It does not invent domains or relax downstream playable/identity validation.
- This is Brain capability only. It is not a 4KHDHub repair until generated from current bytes, published, applied/rematerialized and accepted by isolated real movie + TV proof.


## 2026-10-01 — Catalogue identity/query replay armed on green Brain

- Brain CI run `36861921020` (#1294) is SUCCESS on `045828f825f2a8a326004444b515bc9d4e0c1c51`: full unit suite and public-repository privacy audit passed for the new deterministic catalogue identity/query progression.
- The authoritative 4KHDHub replay is pinned to current NiakVIO `f90341b9d75c411c497b91706dc8291fb596005d`. That source includes the persisted executed-negative `optional_metadata_format_gate` evidence from Repair V6 #254 but no accepted provider-byte mutation.
- Expected first deterministic progression: all prior DOM/format mechanisms remain blocked, then `catalog_identity_query_variants` is compiled from exact current search/detail bytes. Success still requires public mutation publication followed by isolated current-byte movie + TV playable/identity proof in NiakVIO.


## 2026-10-01 — Bound speculative one-shot LLM slots after first executable candidate

- Guidance #223 (`36862196193`) proved one-shot portfolio control works but exposed avoidable CPU waste: slot 1 generated `catalog_identity_query_variants` immediately, then slots 2–4 each spent two ~90 s provider-Bloc calls after every known deterministic mechanism was already blocked/reserved.
- Once any same-run candidate is reserved, later portfolio slots are now explicitly speculative. Their model call is capped at 60 s, transport retry is suppressed, and deterministic-validation retry is suppressed. They still run deterministic progression first and can emit a distinct executable mutation immediately; only repeated expensive LLM recovery is removed.
- Telemetry `FIELD_BRAIN_FORCE_SPECULATIVE_FAST_FAIL` distinguishes transport- vs validation-retry suppression. This preserves the four-slot one-shot contract while preventing a single already-populated portfolio from spending another ~9 minutes on repeated 7B timeouts.
- NiakVIO sandbox/playback/identity authority is unchanged. This is orchestration latency control only and does not claim any provider repaired.


## 2026-10-01 — Speculative-slot latency CI contract alignment

- Brain CI #1296 (`36864988998`) failed only because two source-contract assertions still required the superseded post-reservation 90-second timeout literal. Runtime/planner tests otherwise passed.
- The stale assertions now pin the intended one-shot behavior: post-reservation speculative calls use the 60-second ceiling and expose explicit transport/validation retry suppression telemetry. No provider logic or proof gate changed in this follow-up.


## 2026-10-01 — Brain learns variant-coverage truncation from runtime structure

- Added provider-agnostic runtime Bloc analysis for premature global output caps, first-success short circuits and capped source lists. It detects affected dimensions (quality, language, server, player, source) and quality hints without treating the static signal as proof.
- FORCE prompt compaction now preserves this diagnosis and prioritizes exact `out.length` / cap / break / quality-language-server code windows. The intended repair family is coverage-before-cap: enumerate bounded distinct variants first, then apply the final global stream cap.
- This directly addresses the newly observed HindMoviez shape (later 720p/1080p/2160p variants can sit behind an earlier source that already fills a global quota) while remaining reusable across providers. No HindMoviez provider bytes were hand-edited here.


## 2026-10-01 — FULL OK no longer hides high runtime variant-coverage debt

- Brain now audits every runtime registered by NiakVIO provider-overrides, not merely providers already in the census repairQueue. Static findings remain non-proof: only the high-risk class can be selected as an explicit FORCE target; review findings stay diagnostic.
- A FULL/PARTIAL provider with high premature-cap evidence is represented as `variant_coverage_gap` with provider-local causal prior `enumerate_stream_variants_before_global_cap`. Ordinary unrequested Repair remains unchanged, so green providers are not mass-mutated from static heuristics.
- The Private-Guided Advisor accepts an explicit provider when it is either in the current repairQueue or in the current exact-checkout high runtime-coverage audit. This closes the HindMoviez blind spot where terminal playability was green while later 720p/1080p/2160p variants could be truncated.
- Required proof remains Brain candidate -> isolated current-byte sandbox -> playable/identity validation -> non-regression -> NiakVIO publication. Static coverage findings alone never mark a provider broken or repaired.


## 2026-10-01 — HindMoviez representative exposed FORCE budget starvation

- Brain guidance #224 successfully admitted census-FULL HindMoviez through the new `variant_coverage_gap` path on exact NiakVIO `d19cf01e1ad17a9711c4f80fd8701513bdf6aebe`, proving the green-provider coverage-debt selection works.
- The run produced zero executable mutations because `variant_coverage_gap` was not classified as a compact structural runtime gap. FORCE therefore tried the larger generator `provider_patch` first and the generic 150-second provider budget was split into four ~37-second candidates; Qwen 7B timed out on all four.
- Pipeline fix: variant coverage now prefers exact materialized `provider_bloc`, receives the same bounded 600-second structural portfolio budget when an exact runtime template exists, and the first unsatisfied candidate is no longer blindly divided by portfolio size. It receives up to 180 seconds while retaining bounded reserve for later hypotheses; later reserved candidates still use speculative fast-fail.
- No HindMoviez provider bytes were changed by #224. The representative must be replayed from exact current NiakVIO bytes and still pass isolated playable/identity/non-regression before this repair family can fan out.


## 2026-10-01 — Deterministic coverage-before-cap compiler after HindMoviez Qwen timeout

- HindMoviez guidance on exact NiakVIO d19cf01e1ad17a9711c4f80fd8701513bdf6aebe correctly classified variant_coverage_gap, but Qwen timed out on provider_bloc and published no executable mutation. Workflow success alone was not accepted as a repair.
- Brain now compiles a narrow generic mechanism directly from exact current runtime bytes: a premature global output-quota break may be deferred only when it sits inside a source/variant loop with an independent explicit numeric iteration bound. That independent bound must remain present after the edit.
- The emitted family is bounded_variant_enumeration_before_cap. Unbounded loops fail closed; identity/playability gates and downstream sandbox authority are unchanged.
- Representative tests model the HindMoviez shape with later 2160/1080/720/480 variants and prove both successful compilation and rejection of an unbounded loop. No HindMoviez provider file was manually edited.


## 2026-10-01 — Coverage compiler nested-call loop-header fix

- Brain CI #1315 failed only the new representative coverage compiler test: the bounded-loop regex stopped at the closing parenthesis of an in-header helper call such as !expired(), so it never reached the real loop-closing parenthesis or the existing k<8 bound.
- The loop-header matcher now consumes minimally until a closing parenthesis followed by the loop opening brace. Numeric-bound and collection-length requirements are unchanged; unbounded loops remain rejected.


## 2026-10-01 — HindMoviez coverage replay after bounded-loop parser closure

- Brain main `b2b815194321ff56ea7d0b83e82f6d0aa0499a87` is green in CI #1316 and fixes deterministic parsing of bounded loop headers containing calls, the remaining compiler gap exposed by HindMoviez.
- Replay targets NiakVIO `728030d68d0f5832cd488f07a7c3851f58802353`. HindMoviez remains FULL OK functionally but exact current runtime contains two early global `out.length>=4` caps while source metadata exposes 480p/720p/1080p/2160p variants. This is coverage debt, not route failure.
- Success requires a Brain-generated bounded coverage-before-final-cap mutation from current bytes. Provider identity/playable validation and execution deadlines remain mandatory; no manual HindMoviez provider edit is authorized.


## 2026-10-01 — Deterministic coverage compiler sees final resolver helpers

- HindMoviez guidance #226 still timed out despite the bounded-variant compiler because the compiler never selected its outer resolve helper. The exact runtime ends with resolve followed by resolver registration/IIFE statements; the old deterministic helper extractor treated everything after the final named function as forbidden trailing text and dropped resolve entirely.
- The extractor now uses a balanced JavaScript function-boundary scanner that ignores strings, comments and regex literals. Final helpers remain selectable even when registration statements follow them.
- A representative regression reproduces the HindMoviez topology: an inner per-source quota remains bounded, while the outer k<8 aggregation loop global out.length>=4 break is removed. This proves the intended repair is coverage-before-final-cap, not unbounded traversal and not a hand-authored HindMoviez patch.


## 2026-10-01 — Coverage-parser regression fixture corrected

- Brain CI #1318 on `a9a6fd2ca63abea760dcc5508e9e0a454c09eac3` reached the new trailing-resolver mutation and failed only at Node syntax validation because the synthetic regression fixture had an IIFE closing tail without a matching opening wrapper.
- Production parser code was not implicated by that error. The fixture now remains valid standalone JavaScript while still preserving the required shape: final named `resolve` helper followed by resolver-registration statements.


## 2026-10-01 — HindMoviez deterministic replay armed on current NiakVIO head

- Brain CI #1319 passed on `8d269c85a318640335877c6a6a92524976d3b286`; the trailing-resolver extractor and representative bounded-coverage test are green.
- Replay targets exact NiakVIO `8cc61b4af6f2003f5e2712d84102b004385b5eed` and HindMoviez only. Expected first candidate is `bounded_variant_enumeration_before_cap`, compiled without 7B from current bytes.
- Acceptance still requires NiakVIO isolated sandbox execution to preserve identity/playability and demonstrate expanded quality coverage. A generated patch alone is not repair proof.


## 2026-10-02 — Hierarchical player → variant fan-out compiler

- User evidence clarified the representative Coflix shape: about two servers, with roughly 10 and 9 terminal choices respectively. Server count is therefore not stream-count completeness.
- The deterministic `bounded_variant_enumeration_before_cap` compiler now recognizes bounded header caps in functions that actually call `_crawlDirectMedia`; it can widen server traversal to 16 and aggregate stream retention to 32 while remaining fail-closed for unrelated loops.
- Positive and negative planner tests were added. No Coflix/PapaDuStream provider bytes were edited manually.
- Next authority step is NiakVIO current-byte all-provider fan-out census, then one Brain-produced representative repair (Coflix first), isolated rematerialization/playback/identity validation, followed by PapaDuStream cross-check before any wider cohort application.


## 2026-10-03 — Advisor-only FORCE prompt budget preserves Coflix coverage guidance

- NiakVIO Learning FORCE run 37090364428 routed Coflix correctly as `variant_coverage_gap`, started Qwen 2.5 Coder 7B at 16k context, but made zero LLM calls because `build_prompt_payload` rejected the advisor request with `advisor prompt payload exceeded bounded context budget`.
- Root cause: advisor-only guidance inherited the mutation policy's `allow_mutations=true`, so prompt compaction retained mutation-sized provider source even though this phase only needs sanitized strategy/experiment guidance and has no direct mutation authority.
- Brain-LLM now treats `advisor_only` as a distinct prompt mode: the model-facing mutation policy is forced to no-mutation and source blobs use the smaller diagnostic/advisor compaction path. Deterministic Force remains the only mutation owner and exact source stays outside the advisor payload.
- A regression test reproduces a Coflix-style hierarchical variant-coverage request with large negative experiment history and verifies the serialized advisor payload remains inside the 7600-character bound while preserving the dynamic variant-coverage signal.
- This is a Brain pipeline correction only; it does not claim Coflix repaired. Coflix must be rerun through guidance -> Learning -> executable candidate/materialization -> playback/identity/completeness proof.
