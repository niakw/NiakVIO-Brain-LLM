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
  -> deterministic exact source_windows with stable window_id
  -> Qwen chooses one window_id + exact local find/replace
  -> Brain locates that occurrence inside the selected window
  -> Brain minimizes unchanged prefix/suffix
  -> if the minimized snippet is globally ambiguous, Brain expands only exact
     unchanged surrounding current bytes around that occurrence
  -> syntax / ownership / capability / semantic-no-op validation
  -> concrete provider-local mutation
  -> NiakVIO sandbox + proof
~~~

Invariants:

1. A real compact-wire code edit carries a `window_id` selected from the exact
   windows in that request.
2. `find` must occur exactly once inside the selected window. It does not need to
   be globally unique; deterministic Brain compilation owns that problem.
3. Global disambiguation may add only unchanged bytes from the same complete
   provider-owned source and stays inside the bounded find/replace limits.
4. Brain minimizes copied enclosing-function context before structural validation,
   so a local change is judged as a local change rather than as an accidental
   partial function rewrite.
5. If the window itself is ambiguous, the occurrence cannot be made globally
   unique inside the budget, syntax fails, ownership is crossed or the change is
   behaviorally neutral, Brain retries/abstains. NiakVIO never guesses.

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
   provider mutation and reject unsafe/ambiguous/no-op output.
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
