# Architecture

## Ownership

### NiakVIO

Owns **reality, execution and proof**:

- provider catalogue, current provider bytes and authored/runtime modules;
- census and live evidence;
- Provider v3 materialization and generated-Bloc persistence;
- isolated candidate sandboxes;
- Deep/playback and identity proof;
- current-byte retest and non-regression gates;
- census persistence and publication.

NiakVIO must not compensate for a weak LLM generator with provider-specific
repair heuristics. It may add only generic execution, validation and proof
primitives needed to evaluate arbitrary Brain candidates.

### NiakVIO-Brain-LLM

Owns **reasoning, structural synthesis and learning**:

- normalize bounded provider evidence;
- derive causal failure classes from census depth;
- retrieve public + sanitized-private experience;
- route deterministic/probe/LLM work;
- choose the provider-owned mutation surface;
- expose exact current-byte structural source windows;
- synthesize the smallest semantic provider-local change;
- deterministically compile that window-local change into an exact globally
  unique bounded mutation;
- reject malformed, ambiguous, syntax-invalid, non-causal and no-op edits before
  NiakVIO spends a sandbox run;
- consume external verification feedback;
- maintain positive/negative/safety learning memory;
- prepare LoRA/SFT data only from explicitly validated outcomes.

The LLM has no publication authority. Brain-LLM has synthesis authority; NiakVIO
has proof/publication authority.

## Structured mutation compilation

Qwen must not solve repository-global text anchoring by itself.

~~~text
current provider-owned source
  -> deterministic exact source_windows with stable window_id + causal focus_offset
  -> Qwen chooses one window_id + exact local semantic find/replace
  -> Brain resolves repeated local occurrences against the causal focus
  -> Brain minimizes unchanged prefix/suffix
  -> if the minimized snippet is globally ambiguous, Brain expands only exact
     unchanged surrounding current bytes around the selected occurrence
  -> syntax / ownership / capability / semantic-no-op validation
  -> bounded validation feedback (at most two materially different corrections)
  -> concrete provider-local mutation
  -> NiakVIO sandbox + proof
~~~

Invariants:

1. A real compact-wire code edit carries a `window_id` selected from the exact
   windows in that request.
2. `find` must be exact current bytes inside the selected window, but it may
   occur more than once. Qwen does **not** own textual uniqueness.
3. Each window carries a deterministic causal `focus_offset`. When `find`
   repeats, Brain selects the occurrence that contains the focus, otherwise the
   nearest occurrence after it, otherwise the nearest occurrence before it. A
   truly tied result fails closed.
4. Global disambiguation may add only unchanged bytes from the same complete
   provider-owned source and stays inside the bounded find/replace limits.
5. Brain minimizes copied enclosing-function context before structural validation,
   so a local change is judged as a local change rather than as an accidental
   partial function rewrite.
6. A deterministic validation rejection may feed back a safe reason code to the
   model for at most two materially different corrections in that same scope.
   Rejected source/mutation content is not echoed back.
7. If causal-focus selection is still ambiguous, the occurrence cannot be made
   globally unique inside the budget, syntax fails, ownership/capability bounds
   are crossed or the change is behaviorally neutral after the bounded correction
   chain, Brain abstains. NiakVIO never guesses.

## Runtime flow

1. Read current NiakVIO evidence from an exact read-only checkout.
2. Build a bounded RepairRequest for each symptomatic provider.
3. Retrieve relevant NiakVIO experiences and documents.
4. Derive the causal prior and mutation/evidence policy.
5. Route the case to skip, deterministic/probe work, diagnosis or provider-local
   LLM repair.
6. Build exact provider-owned structural source windows only for the permitted
   mutation scope.
7. Call the local model only when the route requires it.
8. Compile the model's window-local semantic edit into a concrete bounded
   provider mutation, resolving repeated local anchors by causal focus. Production
   guidance permits one bounded validation-feedback correction inside the shared
   per-provider wall-clock deadline before rejecting unsafe/no-op output.
9. Publish sanitized guidance/mutations with exact Brain and NiakVIO SHA pins.
10. NiakVIO imports the pinned artifact and may execute it only in its existing
    isolated current-byte sandbox.
11. NiakVIO returns verification outcomes; Brain persists only sanitized learning
    records.

## Batch scaling

The batch queue is ordered by current evidence depth. Provider cardinality is
dynamic and must never be frozen as an architecture invariant.

One representative provider per causal family should prove a new synthesis
mechanism before portfolio expansion. A workflow success without an executable
candidate is not a family proof.

## Current integration boundary

This repository **is connected to NiakVIO through a bounded, non-authoritative
guidance bridge**.

- Brain reads an exact NiakVIO SHA and publishes sanitized advisor/Force artifacts
  on the guidance branch with Brain/NiakVIO revision pins.
- Brain cannot directly publish provider bytes or update the census.
- NiakVIO may import a compatible artifact, but current-byte sandbox execution,
  playable-media/identity proof, non-regression and publication remain solely
  NiakVIO-owned.
- A rejected Brain candidate is feedback to the synthesis layer, not permission
  to move provider-specific reasoning into NiakVIO.

## Private memory

A private repository may enrich RAG using sanitized NiakVIO-only technical
experiences. Raw conversations never become a runtime dependency and never enter
this public repository.


## Validated implementation reference library

Current FULL OK providers and their already-registered/published Blocs form a
**reference library, not a solution whitelist**.

Brain may retrieve a small number of technically similar examples for the current
causal family. Before a snippet is exposed to the model, Brain removes URLs,
hosts, route literals, provider identifiers and opaque data. The remaining code
is non-authoritative implementation context such as session/fetch handling,
player/iframe traversal, terminal HLS/MP4 extraction, parsing and decoding shape.

The synthesis rule is deliberately open:

~~~text
reference pattern A
reference pattern B
current evidence
       |
       +--> adapt one pattern
       +--> combine patterns
       +--> ignore all references
       +--> invent a genuinely new provider-local mechanism
~~~

A novel script/Bloc is **first-class behavior**, not a last-resort exception.
References must never suppress a new mechanism when current evidence requires
one. Conversely, novelty alone is not evidence: every new mechanism still passes
Brain structural/syntax/ownership guards and NiakVIO's sandbox,
playable-media/identity, current-byte and non-regression proof ladder.

### Bounded structural synthesis and network-fact safety

Force synthesis is deliberately asymmetric: the model may invent **new provider-local algorithms, Blocs and scripts**, but it may not invent network facts. URLs, routes, hosts, tokens and headers must come from current evidence or the model must abstain. Reserved/synthetic hosts are rejected before a candidate leaves Brain.

The model selects a causal source window and proposes a local transformation. Window identity is advisory rather than authoritative: if the exact current-byte `find` is attached to the wrong bounded window, the structural compiler may relocate it across the current causal windows using their deterministic focus metadata. Ambiguous relocation fails closed. This keeps textual targeting in deterministic Brain code instead of asking Qwen to solve repository-global uniqueness.

Each provider has a wall-clock Force budget. Initial synthesis, transport recovery and validation feedback all consume the same deadline. Time remaining bounds every subsequent model call; once exhausted, Brain records a bounded failure and proceeds rather than monopolizing the cohort. Validation retries are surgical and reason-specific, with at most one correction in the production guidance workflow.


### Compact initial Force synthesis

The first Force call must be compact enough to be operationally useful on the local
Qwen runtime. Initial synthesis therefore receives only the causal provider-owned
surface needed for one bounded edit:

- at most 2600 source characters across up to 3 exact current-byte windows;
- at most 2 compact current observations;
- at most 1 short sanitized FULL OK implementation reference;
- no census bulk or unrelated historical/RAG payload.

A validation-feedback retry is narrower still: at most 2200 source characters
across 2 windows and no reference/census bulk.

This is a latency/attention bound, not a creativity whitelist. The model may still
adapt, combine, ignore references, or synthesize a genuinely new provider-local
Bloc/script. Deterministic Brain code owns exact-byte targeting and safety; NiakVIO
owns runtime proof and publication.


### Prompt prefill and KV reuse

Compact Force runs on a local llama.cpp server with prompt caching enabled. Force
requests explicitly set `cache_prompt=true`. Before the constrained edit generation,
the backend may issue a one-token prefill for the exact system+user prompt so the
subsequent generation can reuse the evaluated prefix.

The prefill is not a second unbounded phase: prefill and generation share the same
backend deadline, and all calls remain inside the provider-wide Force deadline.
Production compact Force decoding is capped at 512 tokens because the schema permits
only one bounded edit.

Prompt caching is a performance primitive only. It does not change mutation authority,
proof authority, or acceptance criteria.


### Scope-aware Force generation budget

Compact Force output is intentionally asymmetric by mutation surface. Local edits
should not pay the same generation ceiling as a genuinely new runtime Bloc.

- provider_data: 192 generated tokens maximum;
- provider_patch/provider_js: 640 generated tokens maximum;
- provider_bloc: 448 generated tokens maximum.

The workflow-level token argument is only an upper bound. Brain chooses the lower
scope-specific cap before each model call. This is a performance constraint only:
it does not remove provider_bloc novelty, FULL OK references remain optional, and
NiakVIO proof requirements are unchanged.


### Existing provider surface before novel Bloc fallback

Force spends the first repair attempt on the narrowest existing provider-owned surface
that can express the failure: registered provider patch first, then authored provider
module/data when available. A novel `provider_bloc` remains the invention fallback
after that surface abstains or is structurally rejected.

This ordering is not a novelty restriction. The model may still synthesize a new
mechanism when existing code is insufficient; it simply avoids spending most of a
bounded provider budget rewriting broad generated-runtime helpers before the
provider-authored implementation has been tested. Every scope remains subject to the
same deterministic compiler and NiakVIO proof gates.


### Fast abstention is not repair proof

The compact Force system protocol intentionally removes prose already enforced by
the schema/compiler. This materially reduces local-model latency, but operational
completion or fast abstention is never counted as a repair.

Force telemetry must distinguish:
- model timeout/rejection,
- bounded abstention with a sanitized reason,
- structurally executable mutation,
- later NiakVIO runtime proof.

Only the third state may enter NiakVIO sandbox evaluation; only NiakVIO proof may
change provider/census state.


### Evidence readiness before provider mutation

A provider status alone is not sufficient mutation evidence. Current targeted
provider evidence may override a generic census failure class when it proves the
failure belongs to transport/environment rather than provider code.

In particular, a fresh targeted observation whose provider lanes explicitly
end in `provider_waf_challenge` is transport evidence even when the challenge
page or script returns HTTP 200. Provider mutation is withheld until a stronger
browser/native/residential replay disproves the challenge classification or
otherwise implicates provider-owned behavior.

For provider-local zero-result/parser failures, targeted evidence may also carry
a bounded `shape` per network observation. Brain accepts only a second sanitized
view: validated JSON schema-key names and coarse types/buckets, or bounded
HTML/JavaScript element/function counts plus a closed marker vocabulary. Raw
response bodies, values, cookies, headers and query secrets are never admitted
to prompt context. Shape evidence can justify *where* to edit, but never grants
publication authority.

This prevents the generative Brain from being rewarded for inventing a patch
when the correct causal action is to abstain and gather transport evidence, while
giving real parser/schema failures enough causal structure to avoid blind edits.


### Adaptive quality/compute allocation

Force does not use one uniform budget for every provider. Uniformly constraining all
cases would make the system fast by lowering repair quality; uniformly granting the
maximum budget would not scale to hundreds of providers.

The scheduler therefore separates three concerns:

1. **causal readiness** — transport/WAF or insufficient-evidence cases abstain rather
   than spend provider-mutation compute;
2. **surface complexity** — ordinary provider_data/patch/js edits receive a compact
   primary generation budget, while a new provider_bloc receives more room;
3. **quality recovery** — only a deterministic structural rejection (syntax,
   truncation, anchor mismatch, etc.) unlocks a larger focused correction budget.

Current generated-token ceilings are:

| scope | primary | structural recovery |
| --- | ---: | ---: |
| provider_data | 192 | 256 |
| provider_patch | 640 | 768 |
| provider_js | 640 | 768 |
| provider_bloc | 448 | 768 |

The workflow hard wall-clock ceiling is 240 seconds per provider, but effective
budgets depend on evidence depth: chain/terminal extraction cases may consume the
full cap, route-proven cases up to 180 seconds, ordinary unresolved cases 150
seconds, and transport/environment cases 120 seconds.

No proof gate is weakened by these budgets. Novel Bloc synthesis remains first-class;
the scheduler only decides how much compute a causally justified attempt receives.


### Deterministic editable units

Compact Force must not ask the model to reproduce exact minified source bytes. Causal source windows remain visible for reasoning, but the deterministic Brain compiler derives a bounded set of exact statement/sequence units plus bounded causal whole-function units from current bytes.

For provider patch/JS mutations the model emits only `{scope, path, unit_id, replace}`; for a novel provider Bloc it emits `{scope, family, unit_id, replace}`. Brain resolves `unit_id` back to exact current bytes and offsets, expands uniqueness only when required, then performs full syntax, ownership, placeholder/network and no-op validation. Statement/sequence replacements remain capped at 640 characters; a supplied `function_unit` may use up to 1800 characters so the replacement can remain structurally complete.

Editable units may not be partial function/class prefixes, unmatched-brace fragments, or mid-token window slices. This preserves model creativity for replacement logic while removing exact-byte copying from the probabilistic part of the pipeline.


### Composite editable units and causal deletion rejection

A single exact statement is sometimes too small for a real route/player/terminal repair, while exposing a whole function gives the model too much byte ownership. Force therefore offers both single statements and bounded adjacent statement sequences. A sequence may span 2-4 statements, is capped at 700 characters, and may only join statements separated by whitespace; braces or other structural delimiters stop composition. The deterministic compiler still owns the exact source bytes and offsets.

For traversal-class failures (`route_proven_gap`, `chain_terminal_gap`, `media_extraction_gap`), the compiler also rejects edits that merely delete existing logic without introducing replacement behavior. It rejects removal of `const`/`let`/`var` bindings that remain referenced nearby before redeclaration. These are pre-sandbox causal guards, not proof shortcuts: any surviving mutation must still pass NiakVIO isolated application, Deep/health, playable-media, identity and non-regression gates.


### Strict structured output and bounded causal functions

Force uses strict JSON-Schema constrained generation when the local OpenAI-compatible backend supports it. This removes malformed-JSON retries from the probabilistic path while preserving deterministic Brain validation as final authority.

Editable-unit granularity is progressive: statement units for local edits, bounded adjacent statement sequences when needed, and bounded causal function units when the function body carries current failure-family evidence. Function names are not required to encode the failure; generic/minified names therefore remain repairable. Function-unit selection is diversified across causal helpers so one rejected micro-anchor cannot monopolize every choice. A function unit is not a free-form whole-file edit: Brain extracts exact current bytes, requires balanced braces and a bounded size, assigns a stable unit_id, and keeps all downstream syntax, ownership, network-fact, no-op and NiakVIO runtime proof gates unchanged.


### WAF/client differential as a causal routing input

Provider-network failures are not sufficient by themselves to grant or deny provider mutation authority. Brain consumes NiakVIO's current WAF/client differential ledger **and** the stronger full residential provider replay when available.

Evidence precedence is:
1. full residential provider replay;
2. WAF/client-profile differential;
3. targeted network status/HTTP code.

A narrow 401/403/429 is never sufficient by itself to classify a provider as environment-only. Conversely, an explicitly detected interactive challenge is transport evidence even when the HTTP status is 200. NiakVIO's targeted probe may classify bounded HTML/JavaScript responses as `provider_waf_challenge`; Brain must not turn that explicit challenge back into provider mutation authority merely because the request succeeded at the HTTP layer.

- If full residential provider replay completes identity-safe without a WAF/timeout stage but still ends in provider zero/error, retain the ordinary provider failure class so Force can repair provider logic.
- If current targeted regression evidence explicitly reports `provider_waf_challenge` and no stronger replay disproves it, causal routing moves to the transport/harness diagnostic layer with `compare_browser_native_residential_profiles_without_provider_mutation`; provider mutation scopes are empty.
- If browser and residential probes both confirm persistent challenge and no stronger provider replay contradicts that result, classify as `transport_environment_gap` and withhold provider mutation.
- If the failed target becomes reachable with an audited Nuvio-like profile and no stronger full-provider replay has isolated provider-local failure, classify as `client_transport_gap` and route to the harness/client layer.
- Current provider-local zero-result/terminal evidence remains eligible for provider repair.

This ordering is required for fleet-scale operation: hundreds of providers must not spend LLM mutation budget on transport/TLS/IP-reputation failures, but WAF seeds must also not suppress valid provider repair when the complete provider runtime already disproves transport as the sole blocker.

## Targeted shape deduplication

Compact Force treats repeated response structures as one causal observation. When several current targeted routes share the same method, host, HTTP status and sanitized response shape, Brain keeps one representative route and a bounded `sameShapeRoutes` count instead of repeating equivalent structures in the prompt.

Rows without a response shape are not deduplicated by this rule because distinct failed routes/hosts can still discriminate transport ownership. The optimization reduces prompt evaluation cost only; exact-byte mutation compilation and NiakVIO playback/identity proof remain unchanged.

## Force model timeout versus provider budget

Model-call timeout and total provider budget are separate controls. `--timeout-seconds` can now grant up to 180 seconds to a primary or transport-retry generation; the workflow's existing 120-second argument therefore preserves its prior default, while a local hard-case run may explicitly grant more time.

Route-proven providers may consume up to 360 seconds of an explicitly granted provider budget; the current GitHub workflow still grants only 240 seconds. Chain-terminal/media-extraction cases may consume the caller's full bounded provider budget. Validation-feedback calls stay focused and keep their smaller scope-specific timeout.

This distinction prevents long but structurally valid function replacements from being cut off solely by a hard-coded model ceiling while retaining a finite provider-level compute budget.

## Executable FORCE guidance lane

The GitHub `niakvio-private-guidance.yml` workflow is the canonical executable-advisor producer. It runs current Brain in provider `repair` mode before advisor-only generation, sanitizes concrete mutations through `publish_niakvio_force_mutations.py`, and publishes them with exact NiakVIO/Brain SHA and mutation-context fingerprints.

Structural generation uses a single Qwen slot with 768 tokens, a 180-second model timeout and a 360-second per-provider Force budget. These limits match the current compact Force planner and are intentionally larger than advisor-only guidance.

The resulting `niakvio-force-mutations.json` has sandbox authority only. NiakVIO owns baseline/candidate Deep proof, identity validation, negative memory, materialization and publication.

## Provider Bloc invention fallback

`provider_bloc` is not limited to pre-existing repair helpers. It is the bounded provider-local invention surface when registered patches or authored modules do not already contain the needed mechanism.

The Brain must expose complete exact provider-owned functions as candidate edit units even when their names/body do not match failure-taxonomy keywords. Keyword-aligned functions rank first; generic complete functions near the causal focus remain available as fallback. Qwen may replace one such function with a novel provider-local mechanism using only observed current facts.

A generated Bloc replacement is bounded to 1800 characters. The model never owns the exact find bytes or publication. Brain resolves the selected unit to exact current bytes, validates JavaScript syntax and capabilities, then NiakVIO revalidates context and executes the candidate in isolated baseline/candidate sandboxes before any persistence.

## Causal evidence precedence: full provider replay over seed WAF

A targeted WAF/challenge seed is narrower evidence than a current full-provider residential replay. If the full replay is identity-safe, contradiction-free, non-timeout and its provider debug stage is not itself a WAF/transport failure, Brain must preserve the provider-layer failure taxonomy rather than reclassify the request to harness.

This precedence is applied consistently in both NiakVIO adapter failure classification and Brain causal-prior construction. A seed-level challenge may route to harness only when stronger full-provider replay has not disproved that causal layer. Real persistent WAF evidence remains non-provider mutation territory.

## FORCE evidence freshness contract

Provider mutation must be backed by fresh provider-local evidence, but freshness must not depend on a single auxiliary artifact.

A current targeted-regression observation may authorize synthesis when it contains provider debug/network evidence. If that artifact is stale or absent, the authoritative current census may authorize synthesis only when the provider row is `testedThisRun=true` and contains provider proof already incorporated into that census: route proof, candidate proof, residential provider replay evidence, or explicit route/chain evidence depth.

A standalone WAF/browser/replay file without a source census/SHA pin is never used by itself as mutation-freshness authority. It may inform causality, but current census integration is required before it can unlock provider mutation.

## Guidance publication monotonicity

The `niakvio-guidance` branch is a current-state transport, not an eventually-consistent log. Publication must be monotonic in Brain history. A run whose Brain SHA is an ancestor of the Brain SHA already published is stale and must not overwrite the branch or dispatch another page. Divergent Brain histories fail closed. `force-with-lease` remains a byte-level race guard but is not sufficient by itself because a stale run can legally refetch a newer branch immediately before pushing.

Continuation is permitted only after the current page reports `published=true`. Detailed routing decisions are retained as workflow artifacts so a deterministic/probe/LLM decision can be audited without relying on incomplete live job logs.

## Dedicated runtime precedence inside FORCE

Structural failure does not imply that the generic generated runtime is the best first mutation surface. When a provider already has a registered patch whose source contains the provider-runtime resolver contract (`NIAKVIO_PROVIDER_RUNTIME_RESOLVER_V1` or `__niakvioProviderRuntimeResolverV1`), that authored provider-local runtime is causally narrower than the generic runtime Bloc.

FORCE scope precedence for ROUTE PROVEN, CHAIN REACHED and media-extraction gaps is therefore:

1. registered provider-specific runtime resolver, when present;
2. generated `provider_bloc` invention surface;
3. remaining authored JS/data fallback according to mutation policy.

The generic Bloc remains first for structural providers that do not have a dedicated runtime resolver. A mere registered patch is not sufficient to gain first priority: the runtime-resolver contract must be present. This preserves the purpose of Bloc-first recovery while preventing generic helper edits from masking a more specific provider runtime that already owns search/detail/player/terminal traversal.

### Function-unit compilation is surface-invariant

A `function_unit` has one deterministic contract on every executable provider surface: the model generates replacement body/logic, while Brain owns and preserves the exact current function declaration/name/signature. This applies to `provider_patch`, `provider_js` and `provider_bloc`.

The exact selected function may remain an anchor up to the bounded 1800-character function-unit limit. Statement-level edits keep their smaller limits. Brain validates helper identity before minimization, then syntax/ownership/no-op/live-binding constraints after anchor resolution. An authored runtime must therefore never be forced to reproduce or rename a declaration merely to express a structural repair.

### Causal call-neighbor context

For structural provider runtime failures, function proximity alone is insufficient. A selected `resolve` function often delegates the failing work to provider-local helpers such as search/find, player/server selection, link extraction, or terminal traversal.

Within the existing bounded editable-unit budget, FORCE therefore reserves the strongest whole functions and follows one level of exact local function calls. Direct callees are preferred over unrelated nearby statements when their function name/body carries causal route/search/link/player/server/terminal signals. This does not expand mutation authority: every callee is an exact bounded function from the same provider-owned source, and the model still selects only one unit to replace.

## Provider repair ownership rule

NiakVIO-Brain-LLM owns repair synthesis. Provider-specific manual edits are never the terminal solution. They may expose a causal mechanism, but that mechanism must be generalized into a Brain-owned, provider-agnostic capability and replayed through the normal repair pipeline. The assistant may repair only the Brain/infrastructure that prevents this process from executing; it must not substitute for the Brain by shipping hand-written provider code. Acceptance still requires current-byte sandbox, playable proof, identity safety and non-regression.


## Fleet-scale repair-family architecture

NiakVIO must not scale repair cost linearly with provider count. A provider is an
instance of a causal repair family; the expensive unit of reasoning is the family.

Brain computes a provider-independent `repair_family` from current authoritative
failure state plus privacy-safe structural/network evidence. Provider ids, domains,
literal routes, tokens and source bytes are deliberately excluded from family
identity. The same causal shape on two providers should therefore resolve to the
same family even when their implementation bytes differ.

The operating loop is:

1. classify current providers into repair families;
2. spend novel LLM reasoning on a representative only when no validated family
   mechanism is available;
3. persist a successful NiakVIO sandbox result as
   `repairFamily + mechanismFamily`, never as reusable provider bytes;
4. on another provider in the same family, try `family_replay` first;
5. recompile the mechanism against that provider's exact current bytes;
6. run the normal independent NiakVIO sandbox, playable-media, identity and
   non-regression gates;
7. escalate only providers whose current bytes cannot express the validated
   family mechanism.

`validatedFamilies` is deliberately fail-closed. A mechanism enters it only from
an accepted NiakVIO Force sandbox result. It has `autoApply=false`,
`publicationAuthority=false` and `proofAuthority=false`; family memory is a
replay prior, never a substitute for current provider proof.

Fleet health must therefore expose both raw provider count and repair-family count.
The scaling objective for hundreds of providers is that LLM calls track the number
of novel causal families plus exceptional providers, not the total number of
providers.


## Variant-coverage truncation diagnosis

Brain provider context performs a provider-agnostic static diagnosis of registered runtime Blocs for early global output caps such as `if(out.length>=N) break`, first-success returns and capped source lists. The diagnosis records only mechanisms, variant dimensions (quality/language/server/player/source), quality hints and source offsets; it is not proof and cannot mutate bytes by itself.

When present, FORCE source-window selection focuses on the exact quota/loop unit before generic routing tokens. The repair principle is **coverage before final cap**: enumerate distinct quality/language/server variants under the existing bounded execution budget, deduplicate safely, then apply the final global output limit. It must not solve truncation by making loops unbounded or by weakening playable/identity validation.
