from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "publish_niakvio_guidance",
    ROOT / "scripts" / "publish_niakvio_guidance.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class PublishNiakvioGuidanceTest(unittest.TestCase):
    def test_keeps_only_allowlisted_provider_prior(self) -> None:
        rows = [{
            "provider": "Movie_Box",
            "failure_class": "media_extraction_gap",
            "ok": True,
            "routing": {"reason": "private text must never be retained"},
            "proposal": {
                "provider_id": "movie-box",
                "target_layer": "provider",
                "strategy": "proven_request_program_and_terminal_extraction",
                "confidence": 0.94,
                "abstain": False,
                "diagnosis": "secret historical explanation",
                "evidence": ["https://sensitive.example/path"],
                "mutations": [{"scope": "provider_data", "value": "secret"}],
                "tests": ["some test"],
            },
        }]
        result = mod.sanitize(
            rows,
            niakvio_sha="a" * 40,
            brain_llm_sha="b" * 40,
        )
        self.assertEqual(result["providerCount"], 1)
        self.assertFalse(result["privateContentRetained"])
        self.assertFalse(result["proofAuthority"])
        self.assertEqual(result["rows"], [{
            "providerId": "movie-box",
            "failureClass": "media-extraction-gap",
            "targetLayer": "provider",
            "strategy": "proven-request-program-and-terminal-extraction",
            "profile": "player_media_extractor_v1",
            "confidence": 0.94,
            "priorOnly": True,
        }])
        serialized = str(result)
        self.assertNotIn("sensitive.example", serialized)
        self.assertNotIn("secret historical", serialized)

    def test_rejects_abstain_non_provider_and_unknown_strategy(self) -> None:
        base = {
            "provider": "demo",
            "failure_class": "route_proven_gap",
            "ok": True,
        }
        proposals = [
            {"provider_id": "demo", "target_layer": "provider", "strategy": "search_detail_player_terminal_traversal", "confidence": 0.99, "abstain": True},
            {"provider_id": "demo", "target_layer": "core", "strategy": "search_detail_player_terminal_traversal", "confidence": 0.99, "abstain": False},
            {"provider_id": "demo", "target_layer": "provider", "strategy": "invent_unknown_thing", "confidence": 0.99, "abstain": False},
        ]
        rows = [{**base, "proposal": proposal} for proposal in proposals]
        result = mod.sanitize(rows, niakvio_sha="a" * 40, brain_llm_sha="b" * 40)
        self.assertEqual(result["rows"], [])

    def test_requires_exact_source_shas(self) -> None:
        with self.assertRaises(ValueError):
            mod.sanitize([], niakvio_sha="main", brain_llm_sha="b" * 40)


if __name__ == "__main__":
    unittest.main()
