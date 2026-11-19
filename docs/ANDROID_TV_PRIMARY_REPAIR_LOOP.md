## 2026-11-19 — Distinguish native 25s timeout from QuickJS call-only

Official TV `FIELD_NATIVE_ERROR` with `provider_hard_timeout_ms=25000` must survive the NiakVIO native diagnostic JSON and sanitized per-provider exact-source/JS ledger, independently of `quickJsPhases=["call"]`. Previously the automatic feedback lost this evidence and Brain chose `deterministic_advisor` provider replay for Sadisflix despite a timed-out official call. The adapter now carries `nativeHardTimeoutObserved` plus bounded `nativeHardTimeoutMs`; routing escalates an app-selected native timeout to `llm_diagnose`, owner **unknown**, mutation scopes empty, to discriminate native fetch/WAF, QuickJS Promise completion, Core network bridge, provider route and external environment. An unavailable/currently excluded provider must never be upgraded by the timeout row.

A separate test-owned immediate-vs-awaited synthetic `PluginRuntime` control, run in official NuvioTV without media playback, can yield `bridge_ok`, `promise_delivery_gap` or `baseline_failed`. The latter two route to client-runtime investigation rather than provider patch synthesis. These are negative diagnostic hypotheses only; even positive synthetic results do not certify an HLS stream, correct episode, audio tracks or full playback. Successful routing is not an accepted Brain mutation; the entire compilation, materialization, native replay, independent identity and non-regression sequence remains mandatory.

# Brain-LLM — Android TV-primary repair and native emulator feedback

**Policy:** Android TV is the **primary functional acceptance target**. Existing Desktop macOS, Android Mobile and iOS runtime/Core/ProviderBase/Lego compatibility remains mandatory for selective non-regression; do not implement separate provider variants for each device.

The Android emulator is a GitHub Actions **tool** owned by `niakw/NiakVIO`. It is not part of the LLM weights or a second standalone emulator inside this repository. The Brain chooses experiments, classifies the causal owner, builds programs and evaluates the resulting exact executed bytes. NuvioTV's official runtime supplies the device truth.

## Concrete integration

```text
NiakVIO canonical manifest + exact current JS SHA-256 + failure family
  → fast static/Node/Core diagnostics (cheap)
  → native-corpus-device-targeted.yml (TV API31/x86/1080p, official NuvioTV)
  → native selection + QuickJS + HTTP + terminal player + audio/UI observables
  → diagnose-native-reader.mjs (redacted; no signed URLs)
  → brain-android-tv-emulator-feedback.yml (workflow_run; exact original source/run)
  → ingest_brain_android_tv_emulator.py
  → automation/brain-android-tv-emulator-history.json (10 historical receipts/provider)
  → niakvio_adapter._provider_android_tv_emulator_observations
  → routing.route_request
  → scripts/route_android_tv_emulator_feedback.py (automatic bounded next-action artifact)
  → LLM diagnosis when justified → Brain tools/Lego → compilation and application
  → rematerialized exact code → emulator replay + decoded correctness
  → targeted Desktop/Mobile/iOS non-regression → memory + main publication
```

A route artifact **does not execute the next model call or apply a patch by itself**. A completed feedback workflow demonstrates the observation was routed; an independently observed generator call and successful application are required for actual autonomous repair. A full closed-loop repair has not yet been demonstrated.

## Stage gates and failure owner

- Missing manifest entry: respect the exact Global/VF/no-anime/VF-no-anime installed projection; never silently add VF-only Sadisflix to Global.
- Installed but not enabled/selected/type-compatible: client state and manifest policy, not provider JS.
- QuickJS `call` only: capture completion/error. Do **not** infer zero streams merely from an absent `result`.
- Independent `FIELD_NATIVE_RESULT count=0`: native extraction was empty; correlate official app selection and runtime inputs with macOS/Desktop; the owner remains unknown until causal evidence discriminates Core/runtime vs provider.
- A source-pinned player or fetch failure: classify network, WAF, media extraction, headers/stream, content identity, audio, player, or harness. Never move a platform/harness failure into each provider.
- A correct terminal decoded episode with correct season/title/track metadata: may enter the publication validation chain only after non-regression and proof persistence.

`niakvio_adapter` accepts only whitelisted TV facts from a ledger with `schemaVersion=1`, `authority=official-android-tv-emulator-diagnostic-only`, exact matching active **providerArtifactSha256**, allowed canonical manifest scope, original source SHA and numeric run ID, all four authority fields **false**. `historicalOnly=true` is mandatory. A code change invalidates its use as same-bundle evidence. A success result never becomes FULL just because the emulator app launched.

The `nativeExtractionZeroObserved` and `nativeExtractionPositiveObserved` fields represent distinct independent official native result observations. They are not QuickJS console phases, and neither grants playback/identity authority. The route helper only emits a privacy-safe `mode`, `targetLayer`, `strategy` and bounded next-step category, never raw URLs, cookies, raw logs or executable mutations. Tests: `tests/test_android_tv_emulator_memory.py`, `tests/test_android_tv_emulator_feedback_route.py`, `tests/test_routing.py`.

## Brain-first economics and feedback

Avoid running the 3B/9B model for simple catalogue issues or repeating a diagnostic with no changed evidence. Process the easiest/highest-yield provider representative first, then each distinct family, then cohort. Prefer a deterministic tested Lego; use LLM causal reasoning when exact native evidence resolves an uncertainty that prior deterministic plans could not. Learning should persist positive and negative program fingerprints, exact bundle SHA, native run, failure stage, cause/owner, materialization and replay results. Diagnosing an error or emitting a patch is **not** a repair.

The first user oracle is French-Manga: one macOS Desktop stream with FR audio, no Android TV listing. Official [TV run 44520778916](https://github.com/niakw/NiakVIO/actions/runs/44520778916) recorded app selection true, provider result count 0 and no player, while only the QuickJS call phase was captured. [Feedback 44525039332](https://github.com/niakw/NiakVIO/actions/runs/44525039332) committed its exact-JS diagnostic. The user also reported Sadisflix absent from their stream list; its installed manifest was not established, and the VF-only scope must be retained. These are evidence/unknowns, not permission to hand-edit either provider.

## Operational completeness checklist

The Brain can claim a provider repaired only after: observed failure → owner diagnosis → Brain-produced correction → compile → selection → application → rematerialization → exact executed JS → official Android TV request/route/network → **correct decoded media and episode** → HLS/quality/audio/header/metadata/UI checks → selective cross-client non-regression → source-pinned evidence and knowledge persistence → commit/push verification. If any item is missing, mark it explicitly as `unverified`, `failed` or `blocked`, never `FULL OK`.

**Canonical design reference:** `niakw/NiakVIO/docs/BRAIN_ANDROID_TV_PRIMARY_VALIDATION.md`. Android TV is the primary *proof* target, not justification to delete or disable already implemented Desktop/Mobile/iOS blocks.
