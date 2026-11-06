# Brain-LLM branch cleanup audit — 2026-11-06

- Main at audit: `02b82482039f217b98e7cabe5e2a60d2b649e1a7`; 26 branches.
- 17 exact-head **merged** PR branches eligible for deletion with live PR/HEAD/protected checks.
- 8 unmerged/unattributed or active branches **preserved**. No deletion based solely on age.
- No open PR. PR #16 closed unmerged, #3 closed unmerged; their branch refs are preserved for review.
- Merge-history and PR diffs remain on GitHub even after a merged feature branch ref is deleted.

## Preserved candidates

- `codex/niakvio-brain-reliability` — `1969f2dd3e`; no PR attribution
- `fix/brain-observed-media-bridge-contract` — `17e3ca5528`; PR #16 closed/unmerged
- `fix/force-selected-function-envelope` — `2f4b6028c6`; PR #3 closed/unmerged
- `fix/force-skip-advisor-preflight-20261011` — `8b19d5f9ed`; no PR attribution
- `fix/force-skip-legacy-prompt-prefill` — `8b19d5f9ed`; no PR attribution
- `fix/private-chat-redaction-idempotence` — `8b19d5f9ed`; no PR attribution
- `fix/private-memory-homepath-redaction` — `17f1dc8df3`; no PR attribution
- `niakvio-guidance` — `53227dcd09`; no PR attribution

## Verification required

The cleanup workflow validates exact SHA, merged PR state, same-repository source, unprotected branch, absence of open PR and no head movement before deletion. Branches skipped by these guards are **not** considered cleaned. Afterwards verify GitHub remote branch enumeration, then report actual count. The workflow does not touch main, worktrees, provider code, published manifests or Brain evidence.

## Verified cleanup outcome — 2026-11-06

- [Run 42306142613](https://github.com/niakw/NiakVIO-Brain-LLM/actions/runs/42306142613) **SUCCESS**, exact signal `deleted=17, eligible=17, skipped=[]`.
- Re-enumeration after the run: **9 remote branches** (`main` plus eight intentionally preserved unmerged/unattributed lanes).
- Brain CI [42306321066](https://github.com/niakw/NiakVIO-Brain-LLM/actions/runs/42306321066) **SUCCESS** on `4521b8ec`, including unit suite and public-repository privacy audit after Git SHA/phone false-positive correction.
- NiakVIO contribution invitation [Discussion #273](https://github.com/niakw/NiakVIO/discussions/273) published by [run 42305731807](https://github.com/niakw/NiakVIO/actions/runs/42305731807).
- No evidence was deleted from main; merged PR history and comments persist. The eight preserved branches require a separate review before deletion.

## Second-stage exact ancestry cleanup — 2026-11-06

- After 17 merged-PR branch deletions, Git compare against main `d6524f5bd8d04bd2247d02df7e143fa19cfb4253` proves six additional refs are ancestor-only: `codex/niakvio-brain-reliability`, `fix/force-selected-function-envelope`, `fix/force-skip-advisor-preflight-20261011`, `fix/force-skip-legacy-prompt-prefill`, `fix/private-chat-redaction-idempotence`, `fix/private-memory-homepath-redaction`. The comparison result was `ahead` (main ahead of branch) with `behind_by=0` for each, not guessed by age/name.
- Preserve `fix/brain-observed-media-bridge-contract` (diverged, three unique commits) and `niakvio-guidance` (no common ancestor, separate guidance lane). Main is protected.
- Added one-time cleanup with live GitHub compare, exact SHA, protected/open-PR checks and double HEAD check; remote deletion must be confirmed by run and re-enumeration.

## Final remote cleanup proof — 2026-11-06

- [First cleanup run 42306142613](https://github.com/niakw/NiakVIO-Brain-LLM/actions/runs/42306142613): 17/17 exact merged PR branches deleted.
- [Ancestor cleanup run 42307826860](https://github.com/niakw/NiakVIO-Brain-LLM/actions/runs/42307826860): five additional ancestor refs deleted, one already absent from prior partial run (42307493401).
- **Current remote branch inventory is exactly 3:** `main`, `niakvio-guidance`, `fix/brain-observed-media-bridge-contract`. The last two preserve work not demonstrably integrated; no blanket deletion.
- One-shot cleanup scripts, tests, triggers, manifests and two workflows were removed **after successful remote verification** to avoid leaving maintenance scaffolding permanently in production code. Their exact SHA inputs, execution logs and previous versions remain accessible via Git history.
