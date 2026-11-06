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
