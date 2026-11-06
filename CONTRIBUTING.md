# Contributing to NiakVIO Brain-LLM

Thanks for helping improve the Brain behind [NiakVIO](https://github.com/niakw/NiakVIO)! Contributions and thoughtful reviews are welcome, including from first-time contributors.

## Where help matters

- Better **causal diagnosis** of provider failures, from observed request to terminal media.
- New reusable Brain strategy/Lego types when a family of failures exhausts existing experiments.
- Reliable observation and evidence ingestion (no fabricated selectors or content identities).
- Deterministic mutation compilation, sandboxed application, exact-byte rematerialization and replay.
- Learning/memory that retains both successes and failed proposals without looping forever.
- Thorough regression tests, privacy/security checks and documentation.

## What counts as a repair

A repair is not a model-generated patch or a workflow marked successful. The useful chain is:

`observe → diagnose → synthesize → compile → select → apply → materialize → execute → validate → persist`

A provider is truly functional only when content identity, episode/season, extraction and **decoded, playable media** are evidenced against exact published bytes, with non-regression. Fail closed on unsupported identity or content guesses. An HTTP 200 or a URL is not proof of playback.

## Architecture

Keep the Brain responsible for repair strategies and infrastructure. Do **not** hand-edit generated NiakVIO provider bundles as a durable fix. Improvements to the Brain's tools, prompts, memory, runtime, scoring, selection and verification are in scope. Share reusable strategies instead of one-off fixtures.

The [NiakVIO contributing guide](https://github.com/niakw/NiakVIO/blob/main/CONTRIBUTING.md) explains Provider v3 ownership, Core identity policies and client compatibility.

## Working locally

Use the model/configuration documented in [README.md](README.md) and [config/model.json](config/model.json). Prefer local inference. Do not add paid API calls or network transmission of private observations by default; hosted inference must remain an explicitly configured opt-in.

Run the available Python test suite and privacy checks for changed code. Add one failing regression reproducing the cause before editing whenever practical. Keep all test fixtures non-sensitive.

## Proposing a change

1. Open an issue or a [NiakVIO Discussion](https://github.com/niakw/NiakVIO/discussions) with the failure family, evidence and expected behavior.
2. Keep the PR focused on one shared causal defect (or a clearly scoped set of related defects).
3. Describe inputs, generated proposal, compiled/applied bytes, tests, actual outcome and limits.
4. Include no private API keys, access tokens, cookies, home paths, user data, copyrighted media or unauthorized stream URLs.

Preserve previous negative experiments: deleting evidence to make a test green is not a repair. Avoid stale branches; close, merge and retire finished PR branches after evidence is recorded.

## Security

Please report sensitive vulnerabilities privately, not through public issues or Discussions. Follow [SECURITY.md](SECURITY.md). All GitHub Actions must use explicit least-privilege permissions and pinned actions.
