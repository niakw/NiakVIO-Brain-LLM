from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_public_niakvio.py"
spec = importlib.util.spec_from_file_location("import_public_niakvio", SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PublicLocalForceImportTests(unittest.TestCase):
    def test_local_force_corpus_import(self) -> None:
        import tempfile
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "niakvio"
    results = root / "automation" / "local-force-results"
    results.mkdir(parents=True)

    guidance_path = results / "2026-09-26-test-winning-guidance.json"
    guidance_path.write_text(json.dumps({
        "schemaVersion": 2,
        "sourceSha": "a" * 40,
        "publicationAuthority": False,
        "directMutationAuthority": False,
        "proofAuthority": False,
        "rawMutationContentRetained": False,
        "privateContentRetained": False,
        "providerCount": 1,
        "rows": [{
            "providerId": "mallumv",
            "strategy": "terminal-media-extractor-with-playback-validation",
            "experimentFingerprint": "b" * 64,
        }],
    }), encoding="utf-8")

    (results / "2026-09-26-consolidated-corpus.json").write_text(json.dumps({
        "schemaVersion": 1,
        "role": "local-force-consolidated-corpus-index",
        "providerByteEquivalence": {"headSha": "c" * 40},
        "evidenceFiles": [
            "automation/local-force-results/2026-09-26-test-winning-guidance.json",
        ],
        "noProgressSampled": ["moviesmod"],
        "progressWithoutDeepAcceptance": ["allwish"],
        "knownDeepBaselineHealthy": ["anime-ultime", "mallumv"],
        "knownLocalDeepCandidates": ["mallumv"],
    }), encoding="utf-8")

    rows = mod.collect(root)
    local = [row for row in rows if row.get("source") == "local-force-consolidated"]
    assert len(local) == 5, local
    outcomes = {row["result"] for row in local}
    assert outcomes == {
        "no_progress",
        "progress_without_deep_acceptance",
        "baseline_healthy",
        "ambiguous_deep_candidate",
    }
    ambiguous = next(row for row in local if row["result"] == "ambiguous_deep_candidate")
    assert ambiguous["providers"] == ["mallumv"]
    assert ambiguous["strategy"] == "terminal-media-extractor-with-playback-validation"
    assert "baseline_coincident" in ambiguous["signals"]
    assert ambiguous["proof_authority"] is False
    assert ambiguous["prior_only"] is True
    assert all(row["avoid"] == ["treat_local_force_as_production_proof"] for row in local)


if __name__ == "__main__":
    unittest.main()
