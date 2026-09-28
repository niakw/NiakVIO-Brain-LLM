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
