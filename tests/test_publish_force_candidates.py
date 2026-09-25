import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_niakvio_force_mutations.py"
spec = importlib.util.spec_from_file_location("publish_force", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class ForceCandidatePublicationTests(unittest.TestCase):
    def setUp(self):
        self.old_request = mod.request_from_checkout
        self.old_validate = mod.validate_mutations
        mod.request_from_checkout = lambda _root, _provider: SimpleNamespace(
            provider_context={"registered_patch_scripts": []},
            allowed_mutations=["provider_data"],
        )
        mod.validate_mutations = lambda *_args, **_kwargs: None

    def tearDown(self):
        mod.request_from_checkout = self.old_request
        mod.validate_mutations = self.old_validate

    @staticmethod
    def row(value: str):
        return {
            "ok": True,
            "provider": "demo",
            "failure_class": "chain_terminal_gap",
            "proposal": {
                "provider_id": "demo",
                "target_layer": "provider",
                "strategy": "terminal-media-extractor-with-playback-validation",
                "confidence": 0.96,
                "abstain": False,
                "mutations": [{
                    "scope": "provider_data",
                    "operation": "set",
                    "path": "notes",
                    "value": value,
                }],
                "tests": [],
            },
        }

    def test_single_candidate_is_publishable(self):
        out = mod.sanitize(
            [self.row("candidate-a")],
            niakvio_root=ROOT,
            niakvio_sha="a" * 40,
            brain_llm_sha="b" * 40,
        )
        self.assertEqual(out["providerCount"], 1)
        self.assertEqual(len(out["rows"]), 1)

    def test_multiple_concrete_candidates_require_isolated_sandbox(self):
        with self.assertRaisesRegex(ValueError, "isolated candidate sandboxing"):
            mod.sanitize(
                [self.row("candidate-a"), self.row("candidate-b")],
                niakvio_root=ROOT,
                niakvio_sha="a" * 40,
                brain_llm_sha="b" * 40,
            )


if __name__ == "__main__":
    unittest.main()
