## 2026-11-19 — Android TV primary Brain-driven emulator validation

**Android TV is the primary executable proof client**, and the current official NuvioTV emulator is owned by NiakVIO GitHub Actions. Brain-LLM routes source-pinned sanitized TV run observations into bounded diagnostic next actions through `scripts/route_android_tv_emulator_feedback.py`. Complete design, proof rules, and selective Desktop/Mobile/iOS Lego non-regression: `docs/ANDROID_TV_PRIMARY_REPAIR_LOOP.md`. No automatic model repair is authorized by a diagnostic receipt; decoded content/episode/audio and materialized Brain correction remain necessary for FULL.

## 2026-11-19 — User-native client differences are diagnosis hints, never current proof

`automation/user-client-provider-field-observations.json` in the NiakVIO source repository is a bounded field-observation input. The Brain adapter `_provider_user_client_field_observation` only accepts its declared non-authoritative schema and a whitelist of platform/result/BCP47-language fields. It derives actual provider membership from all four manifests in the current checkout and drops user-provided URLs, headers, notes, fixture guesses and unverifiable build/JS assertions. Every observation states `fixtureKnown=false`, `executedJsKnown=false`, `installedManifestKnown=false`, `proofAuthority=false`, `publicationAuthority=false`, `mutationAuthority=false`.

When a **separate source-pinned** current media Retest already justifies `llm_diagnose` and a non-authoritative field report shows Desktop playback but TV absence, routing adds bounded discriminating steps for installed manifest/selection, runtime getStreams execution, network, UI and audio. It does not switch the causal layer to provider, grant mutation scope or count the user report as a current test. A globally absent yet VF-visible provider must remain VF-only unless independent product and activation policy explicitly changes. Neither no-anime variant is silently replaced with anime.

The 2026-11-19 field report is Mac French-Manga one played stream with FR audio, missing in Android TV stream UI, and Sadisflix not observed (client/fixture unknown). `tests/test_user_client_field_observation.py` and `tests/test_routing.py` preserve redaction, source uncertainty and no-promotion. Tests of the machine's actually installed repo, retained enable flag and provider JS hash remain mandatory before claiming a client root cause.

## 2026-11-19 — Healthy live transport must not suppress current identity diagnosis

The first real French-Manga model check exposed an orchestration contradiction: `routing.route_request` correctly escalated current exact-JS `playable>0, verified=0` evidence to `llm_diagnose`, but `live_context_ingest.attach_live_runtime_evidence` then converted the failure to `proof_freshness_gap` because a second preflight saw reachable media. That observation never proved correct work, S/E, duration or decode.

`live_evidence.current_candidate_identity_gap` now shares the same fail-closed detector with routing and live ingestion. For `candidate_replay_gap` with **matching current Retest proof-negative identity**, the preflight preserves the diagnostic despite positive transport; no current proof means ordinary `proof_freshness_gap` still applies. No added provider mutation authority is granted. Regressions in `test_live_playable_proof_refresh.py` and `test_routing.py` cover valid, historical and forged rows.

Real [run 44510697687](https://github.com/niakw/NiakVIO-Brain-LLM/actions/runs/44510697687) proved both initial and FORCE-stage routing retained `llm_diagnose` and one actual 3B model call was made. FORCE subsequently timed out on provider bloc and abstained on provider patch, producing **zero accepted mutation and zero verified playback**. That failure must become negative experience for causal reasoning/tooling; the model is not to be treated as having repaired French-Manga. The next structural step is to persist diagnostic-only outputs (when mutation is disallowed) and grant executable scopes only after identifying Core vs provider vs media-validation responsibility.

## 2026-11-19 — Exact-JS Retest evidence → Brain causal escalation and experience retention

`niakvio_adapter.request_from_checkout` reads `automation/provider-retest-brain-evidence-latest.json` for **current-census + exact executed provider JS SHA-256** diagnostics and imports `automation/provider-retest-brain-evidence-history.json` as up to four **historical-only same-bundle** observations. The latter never earns `proofAuthority`, `publicationAuthority` or `nativePlaybackAuthority`. No signed stream URLs, cookies, sensitive headers or private user content may enter the exported receipt or generated guidance.

The provider Brain family scheduler remains quick-win-first. For `candidate_replay_gap`, a current exact-bundle, executed Retest showing `playable>0` but `verified=0` and `insufficient_identity_metadata` / `duration_incomplete_hls` now escalates to `llm_diagnose` (no mutation authority). This escapes the prior-only no-op deterministic advisor loop **only when proof is current**. The model must distinguish genuine provider-owned title/season/episode source lineage from missing Core projection and HLS incomplete-duration artifacts; request-derived TMDB UI labels never supply independent identity. A historical negative, mismatched JS, fabricated authority, empty stream or currently verified result cannot trigger this escalation.

Later corrective generation, when its causal owner and required evidence are established, still must pass Brain compilation, application/rematerialization, exact executing bytes, decoded correct work/episode playback, client audio/quality/headers, non-regression and persisted experience before promotion. Diagnostic CI green is not a repaired provider. Relevant tests: `tests/test_current_retest_brain_evidence.py`, `tests/test_retest_history_memory.py`, `tests/test_routing.py`; exporter history in NiakVIO has its own contract tests.

## 2026-11-19 — Zero-LLM deterministic replay still needs bounded planner arguments

The fast-first lane can select a current candidate's no-mutation replay (`candidate_replay_gap`) instead of an LLM repair. In private guidance, `plan_batch_from_checkout.py` always parses `--timeout-seconds` / `--force-provider-budget-seconds` even when `route_request` needs no model. Resolve the validated model **profile and numeric budget arguments** for any non-ready deterministic FORCE preflight, while keeping local model cache/weights/download/start and inference conditional on `llm_needed=true`. Missing model args must never block a cheap already-observed provider candidate; model availability must not turn a deterministic verification into a provider failure.

This is an orchestration/harness contract, not a media proof or a provider-local patch. The first source-pinned French-Manga run `44497329484` exposed the contract via empty timeout, and its correction must be proven with a fresh end-to-end deterministic replay. Regression: `tests/test_private_guidance_model_escalation.py`.

## 2026-11-19 — Quick-win-first Brain repair execution order (proof-neutral)

The Brain's explicit RepairQueue/family-wave selection now prioritizes **work that can be qualified fastest**, based only on the source-pinned census and previous sanitized execution feedback. It does not rank providers by brand/name, invent an available stream, or change the authorized cohort. The first pass is one representative per unresolved causal family, with validated reusable families allowed to fan out and previous LLM execution timeouts rotating witnesses.

Order: (1) `CANDIDATE OK` / `PARTIAL OK` and existing media candidates — **first validate terminal playback, work/season/episode identity, duration, headers, quality and audio languages**; (2) local terminal extraction where the chain is reached; (3) zero-result route/search/ProviderBase gaps; (4) upstream HTTP errors and provider timeouts; (5) WAF/harness/environment evidence, which cannot authorize provider mutation without an independent transport oracle. This order represents *estimated next-test cost*, not functional status. A `playable_unverified` or historical positive is never `FULL OK`, and no generated patch is promoted without exact-byte application, decoded playback, non-regression and persistence.

Canonical selection: `scripts/select_niakvio_repair_family_wave.py` adds `quickWinOrder`, `selectedQuickWins` and an explicit `censusRunIdForPlanningOnly` to its sanitized report; `repair_family.select_family_wave` accepts optional evidence-derived ranks after the fail-closed execution-block check. `select_niakvio_guidance_page.py` still covers the entire authorized cohort across pages. Tests: `tests/test_guidance_family_wave.py` and `tests/test_repair_family.py`. The rank and legacy census are **planning-only**, never stream validation, Reactivation, Repair or publication authority.

## 2026-11-18 — FORCE CPU prompt must receive current-byte residential execution before diagnosis

The cross-network WAF profile is an independent transport oracle, not an alternative provider media source. A full residential provider replay is available as causal evidence only when its executed provider JS SHA-256 matches the exact current Global/France-published bundle; the adapter emits `residentialReplayCurrentBundle` only for that equality. Previous full residential replays of a different provider generation remain historical context. Interactive challenge persistence is not a code defect.

Previously, FORCE prioritized up to four structural/census observations and could silently omit `waf-client-differential-current`; the CPU prompt compactor then reduced observations to one. Thus a live, SHA-matched Sekai replay that returned `provider_zero_before_provider_network` was never necessarily seen by the LLM. The current `_current_residential_provider_replay` builds a dedicated, bounded, privacy-safe `current_residential_provider_replay` payload field independent of the generic observation-selection cap. It carries only lane, runtime stage, stream counts, identity-safety bit and coarse browser transport outcomes. It excludes URLs, cookies, challenge tokens, response bodies and residential IP; it explicitly sets `playbackProofAuthority=false`. Only exact-SHA, non-stale results are admitted.

The compact generator explicitly treats `provider_zero_before_provider_network` as a request-invocation/search/route selection or fixture-mapping hypothesis to inspect *before* any WAF strategy. This is **not** proof of a fix or permission to manipulate challenge behavior. Negative examples must stay reusable, and a repaired provider still needs Brain-generated accepted change → isolated sandbox → materialized exact bytes → real decoded correct-media/identity → non-regression → persisted experience. Contract tests: `tests/test_waf_residential_bundle_provenance.py`, `tests/test_waf_residential_prompt_contract.py` (exact CI `44414547175` SUCCESS on Brain `b80cc13`).

## 2026-11-18 — Residential network evidence requires matching executed provider bytes

NiakVIO's existing GitHub Actions WAF lane can run a second, independently sourced network observation through an authorized Tailscale residential exit, without MacBridge/Desktop Commander tool calls. This isolates GitHub egress reputation from a real provider failure; it does not solve interactive challenges or grant access to restricted media. A browser reaching HTML 200 is an observation, **not** a decoded stream or correct episode.

A full residential provider replay is a stronger causal input than a narrow URL/WAF seed only when it was executed against the **same materialized JS bundle** currently published for that provider. The NiakVIO canonical replay wrapper computes `provider_artifact_sha256` from exact Global/VF bundle bytes, carries that digest through sanitized replay evidence, and refuses a mismatch with census `providerArtifactSha256`. Brain's `_provider_waf_observation` repeats this exact bundle-digest requirement before including full provider replay as current evidence. Outdated or unpinned replay remains background memory, never a positive current repair signal. Browser/OkHttp/HTTP transport matrix stays advisory independent of this gate.

This is an infrastructure/harness/Brain provenance boundary. It must not be repaired with per-provider overrides, synthetic media or shell access to a personal Mac. Canonical proof remains real source pin → generation → isolated apply → rematerialized executed bytes → independently decoded media → correct identity and no regression → persistence.

## 2026-11-18 — Preserve terminal-producing paths in generated provider Blocs

A `provider_bloc` exact-unit edit may be syntactically valid and still destroy playback: the private source-pinned Sekai replay `44400985137` generated a body that replaced nested player-resolution and crawling branches with only an episode-identity guard, dropping every existing `streams.push(...)` producer in the selected block. It was **generated/compiled only**, never proven in decoded playback. The actual failed edit is a negative learning example, not a provider fix.

The Brain compiler now rejects route/media-gap edits that remove multiple terminal stream append operations without preserving an alternate producer, assignment, or return. This is a generic causal invariant on exact current JS bytes; an identity check should wrap or supplement terminal traversal, not replace it. It is enforced before `provider_bloc` compilation and covers bounded `function_unit` and `block_unit` edits. Regression: `tests/test_force_terminal_producer_preservation.py`. Only NiakVIO's isolated materialization, current network execution, terminal media decode, episode identity, and non-regression can validate a repair.

## 2026-11-18 — Current network observation before private FORCE synthesis

The private-guidance workflow historically supplied source-pinned NiakVIO catalog + census, existing public Markdown, private historical ChatGPT mirror and learning experiments to FORCE, but omitted its already implemented `--live-evidence` ingress. A successful route census or old conversation cannot substitute for exact current network responses and function calls. In particular, a generated `no_op`/function-identity edit against an outdated HTML assumption is not a repair, no matter how many alternatives are attempted.

For **one explicit representative provider**, when an LLM Force attempt is necessary and deterministic repair is not already ready, the Brain worker now launches the pre-existing NiakVIO `scripts/capture_brain_live_context.py` inside the exact source checkout (not HEAD by coincidence). It bounds Node/npm bootstrap and preflight, validates provider identity, full source SHA, preflight non-publication authority and network-evidence schema, and passes the **same ephemeral file** via `--live-evidence` to the repair generator and the advisor. `live_context_ingest` then enforces source pinning and separates current transport/harness/fixture failures from real provider parser failures. This observation does not mutate providers or grant candidate publication authority.

For a multi-provider guidance page, no fleet-wide probing is inferred from the first provider's evidence: the workflow omits the single-provider file instead. An unavailable, blocked, timed-out or malformed preflight reports a bounded failure reason, suppresses stale evidence and keeps the existing conservative path. Raw provider network observations, model batches and private project memory remain ephemeral and are explicitly deleted; public guidance contains only already-sanitized diagnostics/mutations. Follow-up acceptance still requires NiakVIO sandbox current-byte application, materialized JS verification, executable media, decoded terminal stream and exact episode/season/TMDB/language/quality validation.

Provenance: Brain `338edd52`, contract `b183fcc2` (CI and real preflight outcome must be recorded in `MEMORY.md`). Earlier Sekai run [44396679503](https://github.com/niakw/NiakVIO-Brain-LLM/actions/runs/44396679503) had real 4-unit source graph rotation but no current live preflight, no executable mutation; it does **not** establish provider correctness.

## 2026-11-18 — FORCE rejection provenance and evidence-gated route call-graph expansion

A compact FORCE `unit_id` is a positional identifier for *selected exact source bytes*, not a stable identifier independent of context. The same structural focus (current live functions and limited retrieved historical/memory tokens), window size and unit budget MUST be passed unchanged through (1) prompt edit-unit rendering, (2) JSON-schema unit enumeration, (3) deterministic current-byte converter and (4) tagging of rejected edits. Recomputing an unsuccessful unit without memory focus can silently attribute its negative result to the wrong function or to no function. Negative feedback is hashed from the **exact selected current unit** and sanitized before it enters the next correction or portfolio hypothesis.

A failed `no_op`/deletion correction is useful causal learning even when it produces no successful proposal row: the correction chain returns a bounded list of exact SHA-256 unit identities, and the portfolio carries these plus prior failed-unit identities without retaining source bytes or private model output. Hard rejection is immediate within the correction chain. Across later hypotheses, previously rejected units are de-prioritized relative to fresh current causal units and can be reopened only as a last resort for a different edit/mechanism; no candidate gains publication authority this way.

For `route_proven_gap`, the default CPU proposal remains a strict two-function dispatcher/parser call-graph seed. Only when *two distinct exact current units* have been rejected as no-op or causally empty deletion, the Brain can widen source-backed selection to a bounded four-unit, two-window graph. This condition applies equally to prompts, constrained JSON schema and converter. It does not override existing evidence-pinned admission selectors, grant access to the global Core, synthesize private data or waive exact-source, Node, NiakVIO materialization, playback and identity gates. The expansion is a strategy after proved exhaustion, not proof of successful repair.

**Evidence**: Sekai private-guided [44393628384](https://github.com/niakw/NiakVIO-Brain-LLM/actions/runs/44393628384) confirmed `rejected_units_carried=2` and abstention when both units were excluded, but **0 executable mutations**. The bounded expansion is a follow-on hypothesis requiring a new source-pinned guided replay and canonical sandbox validation. Do not promote Sekai from successful workflow status alone.

## 2026-11-18 — Structured provider construction memory reuses the existing ExperienceStore

The canonical NiakVIO repair-prior document contains two distinct knowledge layers: explicit historical repair cases and a per-provider structured knowledge map derived from NiakVIO-owned ProviderBase/DATA/Lego state. Brain already imported the first layer. It now imports the second layer into the **same ExperienceStore** rather than creating another memory database.

A `provider-structured-knowledge` row is a historical same-provider construction prior only. Its permitted projection is deliberately narrow: provider ID, strategy class, owned Lego basenames, route-family names, recipe roles/methods/response classes, media types and boolean recipe-capability flags. It excludes domains/hosts, route templates, request URLs/bodies/origins, opaque IDs, credentials and raw JavaScript/Python. This means an old manual reverse can tell FORCE *what kind of mechanism NiakVIO previously built* without telling it that an old endpoint or old implementation is still valid.

Compact FORCE reserves at most one matching row with `ExperienceStore.same_provider_structured_priors()` and projects it as `retrieved_structured_provider_memory`. The row always carries `prior_only=true`, `proof_authority=false`, no current execution/network proof and a same-provider boundary. It cannot authorize mutation, bypass current-source unit selection, override negative execution memory, or satisfy playback/identity gates. Current exact bytes and live provider evidence remain authoritative.

This channel complements, rather than replaces, existing memory planes: Markdown/evidence documents, explicit historical reverse cases, private historical ChatGPT RAG, accepted-program memory and executed-negative experiments. Their provenance remains separate so a model can combine prior knowledge while the deterministic pipeline can still distinguish memory from evidence.

## 2026-11-18 — Existing multi-source memory is prior context; exact live evidence owns repair authority

NiakVIO Brain does **not** use a newly invented parallel memory store. FORCE reuses the existing knowledge planes:

- `DocumentStore`: repository Markdown and evidence documents, including `MEMORY.md` and architecture/census ledgers;
- `ExperienceStore`: historical reverse-engineering/repair cases plus retained experiment results;
- optional read-only private ChatGPT Project memory from `niakvio-private`, sanitized before retrieval;
- exact-SHA hosted executed-negative experiences and FORCE experiment memory.

All retrieved memory is planning context only (`proof_authority=false`). A historical conversation, successful old recipe, Markdown statement or failed mutation cannot override current provider bytes, current network observations, current work/episode identity or playback validation. Private memory is never required by the public hosted repair path and raw private content is not persisted into public repair artifacts.

The authority order for provider mutation is therefore:

`exact current bytes + exact current preflight > current census/runtime state > recent durable memory/evidence > historical/private strategy priors`.

A complete exact-current preflight that is `healthy`, covers every required fixture, returns at least one playable stream per fixture and reports **zero identity contradictions** invalidates a stale provider-local repair diagnosis. Brain reclassifies that situation as `proof_freshness_gap`, routes it to Core/proof refresh, and gives provider mutation policy no writable scopes. This does **not** grant FULL/decoded/native proof; it only prevents rewriting provider bytes that current evidence already shows are functioning.

The public/private memory A/B and live FORCE runs must be interpreted under this boundary: retrieval can improve hypothesis selection, but only generated → compiled → applied → materialized → executed → identity-correct → terminal-playable evidence can establish a repair.

## 2026-11-18 — Causal no-op rejection before provider materialization

FORCE rejects edits that differ textually but leave the causal terminal traversal unchanged. In route/chain/media-extraction gaps, the planner canonicalizes syntax-checked JavaScript formatting and stream **presentation-only** assignments (`name/title/language/provider/player/sourceLabel/sourceName`) while retaining URLs, selectors, request parameters, `url` fields and control flow. If the remaining causal program is identical, the proposal is a `causally irrelevant no-op` and the selected exact unit is rotated before NiakVIO spends a materialization/replay budget.

This guard was added after a real Papadustream FORCE candidate changed pretty-printing and display labels while leaving its player traversal unchanged. Metadata remains editable for failure classes that actually target metadata; this no-op rule is limited to route/terminal/media-extraction repair families.

## 2026-11-18 — Complete control-block edit units for oversized provider runtimes

Some provider-owned terminal helpers exceed the 1,800-character whole-function edit ceiling. Exposing only a truncated 320-character statement may force the local model into unsafe deletions or abstention without a complete syntactic edit surface. FORCE now offers selected `block_unit` candidates: a fully balanced `if (condition) { body }` whose source bytes are cut from the exact current provider function and bounded to 1,400 characters. The candidate is considered only within an oversized provider helper for relevant route, chain or media extraction failures; current execution function names and causal tokens determine the limited offer. This is a generic local edit surface, not a patch for Frenchstream.

The model generates **only replacement body statements**. The Brain converter keeps the exact existing if-condition and braces, resolves the same `unit_id` against current bytes, enforces unique anchors and current source ownership, validates the reconstructed JavaScript, and preserves existing mutation-policy, Node, media/identity replay, no-op and publication gates. Large helpers and nested JavaScript do not bypass syntax, actual source execution or terminal proof. A test with a long synthetic extractor proves a complete unit can be offered, a body edit preserves its if-envelope, and malformed JavaScript is rejected. The Frenchstream live oracle, cross-family transfer and production playback are still required.

## Executed frontier memory across taxonomy refinement

A sandbox frontier is execution evidence, not positive provider proof. Brain may carry that frontier across a later provider-local taxonomy refinement (for example `search_gap` to `media_extraction_gap`) only when the Repair report still identifies the same provider progress, execution memory records `executionObserved=true` with `exploration_progress_nonpublishable` and explicit `sandbox_diagnostic_progress`, and the failure labels remain inside the bounded provider-local family. When the census epoch also changed, the exact current published provider SHA-256 must match the progress-producing parent bytes and current provider-owned network evidence must independently confirm execution. The explicit `provider-frontier:` reason may restore allowlisted pipeline stages such as `player` when the older summary stage lags behind. None of this grants route, terminal-media, identity, mutation-acceptance or publication authority.

## Same-provider execution prior boundary

NiakVIO already persists provider-local execution recipes in `automation/brain-repair-experience.json`. Brain may reuse those recipes as a **historical implementation prior** for the same provider instead of rediscovering an already observed request topology from zero.

The projection is deliberately narrower than the stored experience. It retains bounded method/role/media/response metadata, identifier-free generic endpoints and parameterized routes/body templates. It removes hosts, response bodies, credential-bearing headers, literal fixture/cache IDs and opaque player/embed identifiers. Generic historical RAG remains route-free; this channel is same-provider only.

This prior has `proofAuthority=false`, `executionAuthority=false` and `publicationAuthority=false`. It can guide advisor/FORCE synthesis only. Current provider-owned network evidence, canonical application/materialization, terminal playable media, identity checks, non-regression and normal publication gates remain mandatory before any repair can be accepted.

## Global+France publication authority for NiakVIO guidance

NiakVIO's executable provider authority is a projection union: Global providers are referenced by `manifest.json`, while strict France-only providers remain first-class executable identities in `provider_catalog.json` with `projections.general=false` and `projections.vf=true`. Brain-LLM must not infer current-provider scope from the Global manifest alone.

`provider_context.published_projection_rows()` is the common read-only authority for current published identities. The private-guidance cohort resolver, RAG/current-byte provider context and FORCE publisher all reuse this union. Duplicate Global/France-only identities fail closed. Active-cohort selection excludes `enabled=false`; read-only context can still inspect an explicitly requested published row when appropriate.

This only grants current-byte context and cohort membership. It does not grant mutation, publication or playback proof. FORCE candidates still require exact owned bytes, mutation-policy validation, canonical NiakVIO application/materialization, terminal identity replay and downstream publication gates.


## 2026-11-10 — Quick candidate versus verified provider; event mini-series alias as a search hypothesis

NiakVIO Learning run [42740261560](https://github.com/niakw/NiakVIO/actions/runs/42740261560)
exposed a **real difference between network progress and media identity**:
UHDMovies Quick `route_transition_graph_v6` returned 2 endpoint-playable
streams against 0 before and logged `provisional_quick_runtime_improvement`,
but separate native-reader evidence found an identity mismatch on *Avatar*;
the candidate reconstruction count stayed **0**. Source URI/media URLs were
never positive proof. NiakVIO has now separated exploratory Quick acceptance
from `provider_base_change_authorized` and `accepted_runtime_program`, and
its proposal builder requires explicit strict playable identity before proposing
any executable patch. A sanitized observation is stored as a negative oracle
under `tests/brain_oracles/uhdmovies/provisional_42740261560.json`, never
as a repaired provider or a validated positive learning event.

The new Brain-LLM `quick-media-identity-proof-gap` taxonomy routes this
signature to Core/pipeline. Required checks cover exact-SHA candidate
replay, independent work/season/episode identity, subtitles, program
compilation, application, materialization, execution and persistence.
Neither an HTTP 200 nor a Quick `healthy` label permits provider mutation.

**Special series and event split**: TheTVDB identifies Spartacus
`S00E01` as *Past Transgressions* (21 January 2011) in *Gods of the
Arena*, while independent catalogues offer the same six-episode prequel
as standalone *Spartacus: Gods of the Arena* with `S01E01`.
References:
https://thetvdb.com/series/spartacus/seasons/official/0
and https://www.tvmaze.com/shows/358/spartacus-gods-of-the-arena/episodes
These listings establish a **catalogue-mapping possibility only**. They do
not authorize rewriting any user S00 request into S01/S02 without verifying
the upstream work identity, episode title and original air date, real playable
media and subtitle identity. The new generic
`event-miniseries-catalogue-split` strategy has explicit independent
crosswalk and negative no-numeric-fallback requirements. It applies to any
event/separate-mini-series family; no Spartacus-specific production override
or media URL was introduced.

This change remains *structural capability*. There is no new Brain-generated,
fully materialized, actually decoded episode/subtitle repair confirmed by
this policy update. Continue representative real provider replay.
## 2026-11-10 — Inverse provider oracle to Brain failure-chain diagnosis

The Brain must not treat successful *test-oracle code* as a production repair. A
representative failure was reproduced from NiakVIO's **real shared anime
runtime generator** (`scripts/provider_patches/anime_catalogue_runtime_common.py`)
in a deterministic local API harness. Its `season = Number(...) || 1`
loses S00, and fallback to `seasons[0]` / `eps[0]` silently substitutes
the wrong episode. A retained reference-only fixed provider in
`NiakVIO/tests/brain_oracles/animevost_fr/provider_repaired_oracle.cjs`
selects the exact season/episode and rejects foreign-episode subtitle URLs.
The oracle is not imported into the published provider, not a Brain accepted
program, and does not establish actual network playback.

The upstream animevost-fr JSON search endpoint returned HTTP 200 but an
empty `results` collection for the observed title. Transport status or the
offline oracle cannot be promoted to an actual repair. The reverse-chain
findings are:

1. Observation and causal layer: absent S00 identity and foreign captions are
   **Core/shared-runtime** signatures; an empty live upstream search is
   separately **provider catalogue/transport** evidence.
2. Brain source context: the provider wrapper imports a shared generator,
   but formerly `build_provider_context` exposed only the wrapper and a
   template *path*, not the code that coerced season zero. The new bounded
   `shared_episode_identity_risk` scans the actual owned shared renderer,
   records its SHA-256 and source path, and supplies *diagnostic-only*
   structural risk indicators to the compact model prompt. It is generic to
   source patterns and applies to new renderer families, not a provider-ID
   exception. No proposed code mutation is authorized by the signal alone.
3. Brain routing/policy: `episode-coordinate-loss` and
   `subtitle-episode-association-gap` map to Core/pipeline ownership with
   required oracle, compiler, publication and real-media validation checks.
   Their `mutation_policy` remains fail-closed for provider-local edits.
4. Accepted programme compiler in NiakVIO: `{binding:season}` and
   `{binding:episode}` were rejected or silently filtered, even though the
   materialized ProviderBase route executor already knows these coordinates.
   They are now representable on episodic lanes with provider-ID/slug binding,
   and invalid bindings yield explicit compilation rejection reasons.
5. Execution proof remains distinct: accepted proposal → compiled route →
   materialized bytes → exact client invocation → terminal media decoded →
   correct work/episode and subtitles → persistent positive memory. None of
   these steps may be inferred from a healthy HTTP status, source tests or a
   GitHub Actions green conclusion alone.

CI tests `test_episode_oracle_causal_policy.py` and
`test_shared_episode_renderer_risk.py` validate ownership, no provider
mutation authorization, correct source evidence flow and fail-closed prompt
semantics. The current Brain programme has **not** autonomously produced a
verified new playable provider repair from this experiment. Continue with the
same run and exact SHA when downstream network evidence allows replay; retain
this case as a *negative/diagnostic* learning example until that point.

# Architecture

## Family-first prioritization without cohort truncation

For hundreds of hub providers, the Brain-LLM guidance request has **two distinct scopes**: (a) the authoritative full list of current RepairQueue/variant-debt providers, and (b) a prioritized witness from each unresolved causal family. The witness list changes **order** only; it never filters the authoritative request set. `select_niakvio_guidance_page.py` tracks all requested providers across exact NiakVIO/Brain SHAs, with bounded 1–12 provider pages and automatic continuation. Even an unadvised/abstained provider must remain visible as processed but unvalidated. A validated family pattern can be proposed across siblings, but every sibling still needs its own current-byte playback/identity proof. External guidance is explicitly prior-only; it cannot publish a provider or upgrade the census.

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

## Private memory and current-source FORCE retrieval

The project already has one coherent memory system: canonical current Census,
Repair/FORCE evidence ledgers, 34+ historical reverse/repair solution classes,
Markdown/architecture `DocumentStore` RAG, `ExperienceStore` RAG, and a
read-only, sanitized `niakvio-private` conversation index. Do not build a
parallel store or imply historical chat text is training truth.

The authenticated private-guidance workflow uses `NIAKVIO_PRIVATE_READ_TOKEN`
to index only the NiakVIO ChatGPT Project, scope-checked by Project ID. Raw
transcripts never enter this public repository; the private JSONL is ephemeral,
excludes tool messages, and has `private_memory=true`,
`proof_authority=false`. The public hosted FORCE sandbox intentionally has
only public Markdown and experience data, not this private credential.

The actual FORCE path previously queried Markdown/chat RAG but did not include
most document hits in its compact model prompt, and its historical top-six
experience ranking could exclude exact provider executed-negative results.
The unified fix uses the *existing* stores: reserve at most one
provider-mentioned private-chat document in `BrainPlanner._prepare`, exclude
private notes about other providers, preserve the ordinary public Markdown
ranking, and reserve up to two same-provider, actual materialized+executed
failed candidate records alongside causal historical cases. The compact FORCE
prompt receives at most one redacted private-chat and one public Markdown
excerpt, plus bounded negative mechanism identifiers. It carries no private
conversation path, credentials, full raw snippet, replay authority or
publication authority. The context is optional and trimmed before any exact
editable JS unit is clipped if CPU budgets are tight.

The full private project contract has now been tested against 202
conversations, 167 indexed technical conversations and 6,620 documents.
The current-source FORCE preparation probe asserts a real provider-specific
old-chat hint reaches the compact prompt. This is retrieval/integration proof,
**not** a learned model weight, an applied provider repair or decoded playback.
Current network observation, exact executed bytes, terminal identity,
languages/audio/quality, non-regression, and NiakVIO proof gates always override
historical memory.


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
| provider_bloc | 512 | 256 |

The production private-guidance workflow grants a bounded 600-second Force budget
per provider. Effective budgets still depend on evidence depth: chain-terminal,
media-extraction and route-proven structural cases may consume up to that 600-second
cap; ordinary unresolved cases remain capped at 150 seconds, provider-transport
cases at 300 seconds, and transport-environment cases at 180 seconds.

Within that provider-wide budget, the first non-speculative `provider_bloc`
candidate for a current CHAIN/ROUTE structural gap may consume up to 300 seconds.
Later speculative hypotheses keep their short reserved slots, so one difficult
provider cannot turn every portfolio candidate into a long model call.

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

Model-call timeout and total provider budget are separate controls. The production workflow passes `--timeout-seconds 300`. A non-speculative structural `provider_bloc` primary call may therefore use up to 300 seconds; other primary calls remain capped at 180 seconds. Transport retries remain capped at 180 seconds, while validation-feedback calls keep their smaller scope-specific ceilings (up to 150 seconds for `provider_bloc`).

Chain-terminal, media-extraction and route-proven providers may consume up to the workflow's 600-second provider budget. That larger provider deadline is shared across the portfolio; it does not grant 300 seconds independently to every hypothesis.

This distinction prevents long but structurally valid function replacements from being cut off solely by a hard-coded model ceiling while retaining a finite provider-level compute budget.

## Executable FORCE guidance lane

The GitHub `niakvio-private-guidance.yml` workflow is the canonical executable-advisor producer. It runs current Brain in provider `repair` mode before advisor-only generation, sanitizes concrete mutations through `publish_niakvio_force_mutations.py`, and publishes them with exact NiakVIO/Brain SHA and mutation-context fingerprints.

Structural generation uses a single Qwen 7B slot with a 512-token primary `provider_bloc` ceiling, a 300-second structural Bloc model-call ceiling and a 600-second per-provider Force budget. The candidate scheduler reserves time for later hypotheses, so those are not equivalent to four independent 300-second calls. These limits match the current compact Force planner and are intentionally larger than advisor-only guidance.

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

An older Fast Repair sandbox frontier may be reused across census epochs only as **diagnostic causality**, never as positive proof, when all of the following hold: the current published provider artifact SHA256 exactly matches the parent bytes of the historical generated attempt; the current targeted-regression artifact belongs to the current census and contains a successful provider-owned HTTP observation (TMDB-only traffic is insufficient); the historical memory independently records actual sandbox execution/progress; and the resulting observation is rebound to the current census with `reuseAuthority=exact-byte-current-evidence`. Changed bytes, failed/challenged current provider transport, or a shallow frontier fail closed. In particular, a `NO PROOF` row may bypass another recognition-only cycle only when the rebound frontier actually reached provider player logic; lookup-only progress remains probe-only.

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


### Deterministic coverage-before-cap compiler

For a current variant_coverage_gap, FORCE no longer depends on model latency when the exact runtime proves a narrower safe transformation. Brain may defer a premature global out.length quota break only when that break is inside a source/variant loop that already carries an independent explicit numeric iteration bound. The loop bound, identity checks, playback validation and final return remain unchanged. Unbounded source loops fail closed.

This compiler is provider-agnostic and current-byte bound. It emits provider_bloc family bounded_variant_enumeration_before_cap through the same exact-anchor, syntax and sandbox gates as any other FORCE mutation.


## Dense per-server fan-out

Variant completeness is hierarchical: a provider may expose a small number of servers/players while each server exposes many legitimate terminal variants. The deterministic FORCE compiler may therefore widen bounded player traversal separately from aggregate stream retention when current runtime evidence is a high-risk variant-coverage truncation and the function delegates to the shared media crawler.

The current bounded envelope is 16 player/server rows and 32 aggregate terminal streams. This is intentionally provider-shape agnostic: provider-local runtimes still own how their own HTML/JSON names and locates servers, while the Brain only removes proven truncation from exact current bytes. Isolated sandbox acceptance still requires no runtime/identity/playback regression plus a verified completeness dimension gain.


## 2026-11-07 — HTTP 404 : distinguer origine catalogue et terminal

La classification causale des échecs HTTP de `live_evidence.py` sépare désormais explicitement les étapes **provider lookup** (`search`, `catalogue`, `content_lookup`, `detail`, `episode`) de **player/source/media**. Un 404 sur une page lecteur, un CDN, un segment média ou une étape inconnue n'est **pas** une preuve que le domaine du provider est à remplacer. Le Brain ne peut déplacer en tête la stratégie `provider_data`, ni déclasser un ancien FULL/PARTIAL sur le seul fondement de tels 404.

`_failed_fixture_lookup_404s` requiert que chaque fixture réellement échouée dispose de sa propre trace 404 limitée aux étapes de recherche/catalogue ; une trace mixte 200/404 ou une erreur aval invalide cette attribution précise. `apply_verified_live_failure` garde le statut historique inchangé quand la preuve ne satisfait pas ce contrat. `domain_reference_focus` utilise le même oracle, sans accorder d'autorité de publication à une référence externe.

Tests : `tests/test_live_preflight_policy.py` et `tests/test_public_domain_references.py`, dont un scénario film + `Spartacus S00E01`. Ces scénarios testent la **cohérence de classification** sur données synthétiques représentatives ; ils n'établissent ni la bonne identité d'un épisode joué, ni un stream terminal valide, ni une réparation complète d'un provider. Les observations live et le catalogue restent des autorités distinctes.

### Current-byte FORCE anchor boundary (2026-11-10)
The public Brain-LLM FORCE bridge checks every generated `provider_bloc` find for
exactly one occurrence in the manifest-selected, provider-owned *current runtime*
bytes before calling it canonical-apply eligible. Missing, duplicate, stale or
Core-only anchors are rejected without editing providers. The authoritative
NiakVIO apply, materialization, terminal playback and content identity gates
still must pass. Source-family diversity is not equivalent to playback proof.

### Canonical CPU challenger pipeline (2026-11-10)
The real-source CPU challenger explicitly requests `BrainPlanner.plan(...,
compact_force=True)` instead of the raw-model-only probe. This exercises the
production FORCE constrained grammar/current-unit converter before the exact
current-provider anchor preflight and external NiakVIO sandbox materializer.
The raw-model path remains benchmark-only; it cannot establish executable repair.

### Independent source-family witnesses
The read-only canonical CPU challenger carries an isolated four-provider matrix
(download HTML, anime API/player, HTML player, film/series API). Each job owns
its sandbox, its exact source SHA, its provider-scoped canonical apply and Deep
check, and its separate artifact. A single case or an inferred family topology
cannot establish another provider's media/identity success.


### Hosted model choice and GitHub retirement (2026-11-10)

GitHub Models was **fully retired on July 30, 2026**, including its inference
API and BYOK surface. A GitHub Actions `GITHUB_TOKEN` cannot be treated as a
free hosted model endpoint. Source: https://docs.github.com/en/github-models
and https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-july-30-2026/

The public runner benchmark uses checksum-pinned local Qwen3.5-9B on CPU and
is **read-only**; a passing diagnostic run does not establish a repaired stream.
The existing `HostedResponsesBackend` (or a compatible separately provisioned
hosted inference service) requires explicit credentials, bounded cost, and
sanitized source/secret handling. Do not silently enable cloud calls, presume
GPU availability on GitHub-hosted CPU runners, or use Copilot as an undocumented
substitute for the retired GitHub Models inference API. Keep the common
compiler/materializer/playable-media validation regardless of model chosen.


### Hosted model evaluation is intentionally not wired into GitHub Actions

The source challenger supports an explicit `--backend hosted` CLI path using
the existing budgeted `HostedResponsesBackend`. It requires a paid-API opt-in,
a manually provided credential and a shared budget ledger. No GitHub workflow
receives an API key or enables paid calls; the pre-existing repository contract
(`tests/test_no_paid_api.py`) forbids this. GitHub Actions' hosted-API check
remains deliberately disabled. The stronger model experiment is **not run**
and requires a separate operator-controlled deployment and spending consent.
No provider publication is possible from the benchmark.


### Public-RAG parity in read-only real-source challenger (2026-11-10)
The canonical four-family CPU challenger imports production public experience and
documentation with the same importer scripts used by the normal FORCE workflow.
Empty, missing or unusable corpora cause a fail-closed diagnostic rather than a
fake representative model test. The model planner and post-generation classifier
receive the same retrieval store. Reports contain record counts only; private
project memory remains unavailable in this public CI and must not be assumed
equivalent to the full production Brain context. The generated candidate still
requires exact anchor / canonical apply / materialize / real media identity.


### Brain benchmark baseline and reproducibility gate (2026-11-10)
A single playable result after a generated patch is not causal repair. The
isolated FORCE challenger must now replay the exact source baseline, apply and
materialize the candidate, then perform two independent candidate Deep probes.
Only an improvement over a non-healthy baseline on comparable exact
provider/fixture identities, with no per-fixture regression and identity-matched
playback in both candidate passes, can set `validated=true` in the **sandbox
diagnostic**. Actual NiakVIO publication and production acceptance remain
separate, requiring their own current-SHA proof.


### RAG → FORCE generation continuity (2026-11-10)
Loading memories is insufficient if synthesis receives only the causal prior.
The compact FORCE prompt now includes up to two bounded, same-failure-class
strategy hints with safe normalized labels, non-authoritative proof markers and
explicit revalidation requirements. Raw recovered routes, domains, secrets,
source files and historical claims of terminal playback are not transferred.
Numeric-only telemetry reports how many exact editable units, prior strategies
and same-provider field facts were supplied. Mutation and current-content
validation policy remains independent of the LLM and prior lessons.


### Current provider live-preflight ingestion shared across Brain (2026-11-10)
Production `plan_batch_from_checkout` and the four-source CPU challenger use the
same exact SHA/provider-bound `attach_live_runtime_evidence` adapter. A NiakVIO
read-only preflight must first execute immutable type-correct media fixtures and
project bounded network/HTTP/GraphQL response **structure** and active function
names. No raw responses or private credentials are passed to the prompt or
uploaded. Missing/incomplete preflight fails closed. The shared adapter may
refine the causal failure and prioritize actually executed provider-owned
functions before the FORCE scope cascade, but cannot grant source authority,
media/episode identity, playback or publication. Baseline vs candidate vs
confirmation remains the separate post-mutation proof.


### Sanitized current causal signatures (2026-11-10)
The Brain synthesizer now sees a compact, typed description of current
provider-executed HTTP/GraphQL/HTML/player/media **observation** signatures.
Each signature explicitly has no publication/media identity authority; it
cannot invent a working host, correct episode, valid stream or mutating policy.
The identical pure classifier serves production live FORCE context and
four-family read-only model comparison. When the worker never issues a request,
the next action is same-byte Nuvio-vs-Deep invocation diagnosis, **not** an
automatic provider parse patch. Actual model output and replay are independently
required; synthetic signature tests never count as fixes.


### Cross-repository exact-SHA source challenger, TMDB-authenticated preflight (2026-11-10)
The benchmark is a reusable workflow: the NiakVIO caller supplies immutable
Niak source and Brain model SHA inputs and passes its own existing TMDB
credential via GitHub Actions secret scope. Checkout commit identity is
asserted before execution; the Brain publisher records the Brain checkout
commit, never the caller GitHub SHA. Keyless preflights fail closed as
`missing_tmdb_credential` instead of falsely diagnosing zero-request
provider behavior. Credentials are not exposed to the model, reports or
artifacts. This is **not** a new paid LLM endpoint: pinned local Qwen remains
the generator and the same exact-source canonical Deep and identity proof is
still required to accept a candidate.
