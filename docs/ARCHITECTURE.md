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
- provider_patch/provider_js: 320 generated tokens maximum;
- provider_bloc: 448 generated tokens maximum.

The workflow-level token argument is only an upper bound. Brain chooses the lower
scope-specific cap before each model call. This is a performance constraint only:
it does not remove provider_bloc novelty, FULL OK references remain optional, and
NiakVIO proof requirements are unchanged.


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

In particular, a fresh targeted observation whose provider lanes consistently
end in `provider_waf_challenge` with provider-origin 401/403/429 responses and
no playable/verified lane is classified as `transport_environment_gap`.
Provider mutation is withheld until a discriminating browser/native/residential
probe implicates provider-owned behavior.

This prevents the generative Brain from being rewarded for inventing a patch
when the correct causal action is to abstain and gather transport evidence.


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
| provider_patch | 320 | 384 |
| provider_js | 320 | 384 |
| provider_bloc | 448 | 768 |

The workflow hard wall-clock ceiling is 240 seconds per provider, but effective
budgets depend on evidence depth: chain/terminal extraction cases may consume the
full cap, route-proven cases up to 180 seconds, ordinary unresolved cases 150
seconds, and transport/environment cases 120 seconds.

No proof gate is weakened by these budgets. Novel Bloc synthesis remains first-class;
the scheduler only decides how much compute a causally justified attempt receives.


### Deterministic editable units

Compact Force must not ask the model to reproduce exact minified source bytes. Causal source windows remain visible for reasoning, but the deterministic Brain compiler derives a bounded set of exact, statement-sized `editable_units` from current bytes.

For provider patch/JS mutations the model emits only `{scope, path, unit_id, replace}`; for a novel provider Bloc it emits `{scope, family, unit_id, replace}`. Brain resolves `unit_id` back to the exact current-byte statement and offset, expands uniqueness only when required, then performs full syntax, ownership, placeholder/network and no-op validation.

Editable units may not be partial function/class prefixes, unmatched-brace fragments, or mid-token window slices. This preserves model creativity for replacement logic while removing exact-byte copying from the probabilistic part of the pipeline.


### Composite editable units and causal deletion rejection

A single exact statement is sometimes too small for a real route/player/terminal repair, while exposing a whole function gives the model too much byte ownership. Force therefore offers both single statements and bounded adjacent statement sequences. A sequence may span 2-4 statements, is capped at 700 characters, and may only join statements separated by whitespace; braces or other structural delimiters stop composition. The deterministic compiler still owns the exact source bytes and offsets.

For traversal-class failures (`route_proven_gap`, `chain_terminal_gap`, `media_extraction_gap`), the compiler also rejects edits that merely delete existing logic without introducing replacement behavior. It rejects removal of `const`/`let`/`var` bindings that remain referenced nearby before redeclaration. These are pre-sandbox causal guards, not proof shortcuts: any surviving mutation must still pass NiakVIO isolated application, Deep/health, playable-media, identity and non-regression gates.


### Strict structured output and bounded causal functions

Force uses strict JSON-Schema constrained generation when the local OpenAI-compatible backend supports it. This removes malformed-JSON retries from the probabilistic path while preserving deterministic Brain validation as final authority.

Editable-unit granularity is progressive: statement units for local edits, bounded adjacent statement sequences when needed, and bounded causal function units only when a function name matches the current failure-family keywords. A function unit is not a free-form whole-file edit: Brain extracts exact current bytes, requires balanced braces and a bounded size, assigns a stable unit_id, and keeps all downstream syntax, ownership, network-fact, no-op and NiakVIO runtime proof gates unchanged.


### WAF/client differential as a causal routing input

Provider-network failures are not sufficient by themselves to grant or deny provider mutation authority. Brain consumes NiakVIO's current WAF/client differential ledger **and** the stronger full residential provider replay when available.

Evidence precedence is:
1. full residential provider replay;
2. WAF/client-profile differential;
3. targeted network status/HTTP code.

A narrow 401/403/429 is never sufficient by itself to classify a provider as environment-only.

- If full residential provider replay completes identity-safe without a WAF/timeout stage but still ends in provider zero/error, retain the ordinary provider failure class so Force can repair provider logic.
- If browser and residential probes both confirm persistent challenge and no stronger provider replay contradicts that result, classify as `transport_environment_gap` and withhold provider mutation.
- If the failed target becomes reachable with an audited Nuvio-like profile and no stronger full-provider replay has isolated provider-local failure, classify as `client_transport_gap` and route to the harness/client layer.
- Current provider-local zero-result/terminal evidence remains eligible for provider repair.

This ordering is required for fleet-scale operation: hundreds of providers must not spend LLM mutation budget on transport/TLS/IP-reputation failures, but WAF seeds must also not suppress valid provider repair when the complete provider runtime already disproves transport as the sole blocker.
