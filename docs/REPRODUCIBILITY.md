# Reproducible model runtime

Model benchmarks and production releases must eventually pin exact model artifacts.

## Current bootstrap

Benchmarks use a model repository plus a quantization selector such as Q4_K_M. This is sufficient for exploration, but not for a promoted Brain release.

## Promotion requirement

A promoted model version must record:

- upstream family/model ID;
- exact upstream revision or immutable artifact digest;
- quantization format;
- llama.cpp revision/build identity;
- prompt/schema version;
- NiakVIO memory-corpus version;
- golden-benchmark version.

## Brain version identity

A future Brain release should be reproducible from a manifest containing brain version, model ID, immutable revision, quantization, model SHA-256, llama.cpp revision, prompt/schema version and benchmark version.

NiakVIO integration should consume a Brain release/version, not an unpinned moving model target.
