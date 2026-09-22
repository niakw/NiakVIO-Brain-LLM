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

## Expected scaling

For hundreds of providers:

1. census/fast tests classify all providers;
2. deterministic router resolves or schedules most known cases;
3. probes gather missing current evidence;
4. only unresolved provider-local cases enter the LLM queue;
5. LLM candidates are verified independently by NiakVIO.

This keeps intelligence available without paying model inference cost for every routine provider.
