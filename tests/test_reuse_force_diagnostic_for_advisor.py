"""One completed exact-JS diagnosis must not consume a second local model call."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reuse_force_diagnostic_for_advisor.py"
spec = importlib.util.spec_from_file_location("reuse_force_diagnosis", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ExactForceDiagnosisReuseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "providers").mkdir()
        (self.root / "vf").mkdir()
        (self.root / "providers/demo.js").write_bytes(b"actual-in-repo-js")
        self.digest = hashlib.sha256(b"actual-in-repo-js").hexdigest()
        self.manifest = {
            "scrapers": [{"id": "DEMO", "enabled": True, "filename": "providers/demo.js"}]
        }
        (self.root / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        (self.root / "vf/manifest.json").write_text('{"scrapers":[]}', encoding="utf-8")
        self.row = {
            "provider": "demo",
            "ok": True,
            "diagnostic_only": True,
            "provider_mutation_authority": False,
            "diagnostic_exact_bundle_sha256": self.digest,
            "routing": {"mode": "llm_diagnose", "allowed_mutations": [],
                        "target_layer": "unknown"},
            "proposal": {"target_layer": "unknown", "mutations": [], "abstain": False},
        }

    def check(self, **updates):
        return mod.reusable([{**self.row, **updates}], ["demo"], self.root)

    def test_completed_diagnosis_can_skip_duplicate_advisor(self):
        self.assertTrue(self.check())
        self.assertFalse(mod.reusable([self.row], ["demo", "extra"], self.root))
        self.assertEqual(mod.exact_active_digest(self.root, "demo"), self.digest)

    def test_does_not_skip_when_proposal_is_missing_abstaining_or_mutating(self):
        self.assertFalse(self.check(proposal=None))
        self.assertFalse(self.check(proposal={"mutations": [], "abstain": True}))
        self.assertFalse(self.check(proposal={"mutations": [{"scope": "provider_patch"}]}))
        self.assertFalse(self.check(proposal={"mutations": [], "abstain": False},
                                    ok=False))
        self.assertFalse(self.check(diagnostic_only=False))
        self.assertFalse(self.check(provider_mutation_authority=True))
        self.assertFalse(self.check(routing={"mode": "llm_repair", "allowed_mutations": []}))
        self.assertFalse(self.check(routing={"mode": "llm_diagnose",
                                            "allowed_mutations": ["provider_patch"]}))
        self.assertFalse(self.check(probe_only=True))

    def test_does_not_skip_wrong_js_disabled_or_malformed_scope(self):
        self.assertFalse(self.check(diagnostic_exact_bundle_sha256="c"*64))
        self.assertFalse(self.check(diagnostic_exact_bundle_sha256=""))
        self.assertFalse(mod.reusable([self.row, self.row], ["demo"], self.root))
        self.assertFalse(mod.reusable([self.row], ["demo", "demo"], self.root))
        (self.root / "providers/demo.js").write_bytes(b"new-current-js")
        self.assertFalse(self.check())
        self.manifest["scrapers"][0]["enabled"] = False
        (self.root / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        self.assertFalse(self.check(diagnostic_exact_bundle_sha256=
                                    hashlib.sha256(b"new-current-js").hexdigest()))

    def test_cli_does_not_log_sensitive_proposal(self):
        targets = self.root / "targets.txt"
        force = self.root / "force.jsonl"
        targets.write_text("demo\n")
        candidate = {**self.row, "proposal": {**self.row["proposal"],
                     "untrustedText": "Bearer SECRET https://private.example/clip"}}
        force.write_text(json.dumps(candidate) + "\n")
        cmd = [sys.executable, str(SCRIPT), "--force-batch", str(force),
               "--targets", str(targets), "--niakvio-root", str(self.root)]
        good = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("eligible=true", good.stdout)
        self.assertNotIn("SECRET", good.stdout)
        self.assertNotIn("private.example", good.stdout)
        force.write_text(json.dumps({**self.row, "proposal": None}) + "\n")
        bad = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("action=run_advisor_model", bad.stdout)

    def test_workflow_uses_guard_not_unconditional_bypass(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/niakvio-private-guidance.yml").read_text()
        self.assertIn("reuse_force_diagnostic_for_advisor.py", workflow)
        self.assertIn("FIELD_BRAIN_DIAGNOSIS_ADVISOR_REUSE", workflow)


if __name__ == "__main__":
    unittest.main()
