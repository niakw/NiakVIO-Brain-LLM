# LLM routing policy

The local LLM is an escalation path, not the first step for every provider.

## Fast path

No LLM call when deterministic NiakVIO state already decides the next action.

Examples:

- FULL OK / stable PARTIAL OK with no regression: no repair reasoning.
- candidate replay strategy: replay existing same-provider candidate first.
- harness/network/core causal class: run the corresponding diagnostic/retest first.
- API discovery gap with no fresh discovery evidence: perform discovery probe before asking for a patch.
- previously failed identical hypothesis: skip it.

## LLM path

Invoke the local model only when reasoning adds value:

- multiple plausible provider-local hypotheses remain;
- current provider source/data is available;
- a provider-local patch must be synthesized;
- historical experiences disagree or only partially transfer;
- the previous verified attempt failed and a genuinely new hypothesis is required.

## Executed-negative exhaustion and cohort-wide model access (October 2026)

Known high-confidence taxonomy remains a useful initial deterministic route, but it is **not a licence to try every combination of abstract knobs indefinitely**. For `advisor_only` requests, three *distinct* failed experiment fingerprints with `executionObserved=true`, `consecutiveFailures>0` and the **same executor profile** route to `llm_repair` instead of additional generic permutations. Legacy unexecuted rows, duplicates, successes and other profiles never count towards the threshold. The model still has `allowed_mutations=[]` in advisor mode; it supplies hypotheses, not directly publishable code or proof.

Private guidance's deterministic FORCE preflight may bypass Qwen **only when all providers on the current exact guidance page have sanitized executable candidates** (`executable == page_count`). A partial page must continue through the model path for unresolved work; otherwise one deterministic candidate would starve all its siblings. Selection of one representative per failure family is prioritization, not filtering: all requested providers remain tracked across pages and source/Brain SHAs.

The FORCE generator's `--stop-after-first-mutation` switch is a **whole-batch early exit**. It is prohibited in full-cohort `niakvio-private-guidance.yml`, which must iterate every selected provider in every guidance page with bounded per-provider portfolios. The switch remains opt-in for explicitly quick/single-result experiments only. Otherwise, one provider's first candidate would defer all siblings without ever invoking their Brain synthesis.

These routing improvements are tested in the Brain-LLM CI (264 tests, privacy audit) and are **not** a claim of provider functionality. Acceptance requires NiakVIO to compile/validate the generated program, apply it to the exact current source, rematerialize and inspect executed bytes, replay the correct title/episode to terminal playable media, run non-regression and persist outcome fingerprints.

## Expected scaling

For hundreds of providers:

1. census/fast tests classify all providers;
2. deterministic router resolves or schedules most known cases;
3. probes gather missing current evidence;
4. only unresolved provider-local cases enter the LLM queue;
5. LLM candidates are verified independently by NiakVIO.

This keeps intelligence available without paying model inference cost for every routine provider.
