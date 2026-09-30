import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "select_niakvio_repair_family_wave.py"
spec = importlib.util.spec_from_file_location("family_wave", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class GuidanceFamilyWaveTests(unittest.TestCase):
    def setUp(self):
        self.old_request = mod.request_from_checkout
        self.old_family = mod.repair_family_descriptor
        self.old_memory = mod.load_memory
        mod.request_from_checkout = lambda _root, provider: SimpleNamespace(provider_id=provider)
        mod.repair_family_descriptor = lambda request: {
            "key": ("a" * 64) if request.provider_id in {"alpha", "beta"} else ("b" * 64)
        }

    def tearDown(self):
        mod.request_from_checkout = self.old_request
        mod.repair_family_descriptor = self.old_family
        mod.load_memory = self.old_memory

    def test_unvalidated_family_uses_one_rotating_representative(self):
        mod.load_memory = lambda _root: {
            "schemaVersion": 2,
            "entries": [
                {
                    "providerId": "alpha",
                    "consecutiveFailures": 3,
                }
            ],
            "validatedFamilies": [],
        }
        selected, report = mod.select_wave(["alpha", "beta", "gamma"], ROOT)
        self.assertEqual(selected, ["beta", "gamma"])
        self.assertEqual(report["repairFamilyCount"], 2)
        self.assertEqual(report["deferredProviders"], ["alpha"])

    def test_previous_generation_timeout_rotates_family_witness(self):
        mod.load_memory = lambda _root: {
            "schemaVersion": 2,
            "entries": [],
            "validatedFamilies": [],
        }
        diagnostics = {
            "schemaVersion": 1,
            "rows": [{
                "providerId": "alpha",
                "scopeTrace": [
                    {
                        "scope": "provider_patch",
                        "outcome": "rejected",
                        "reason": "timeouterror",
                        "errorType": "TimeoutError",
                    },
                    {
                        "scope": "provider_bloc",
                        "outcome": "budget_exhausted",
                        "reason": "provider_budget_exhausted",
                    },
                ],
            }],
        }
        selected, report = mod.select_wave(
            ["alpha", "beta", "gamma"],
            ROOT,
            previous_diagnostics=diagnostics,
        )
        self.assertEqual(selected, ["beta", "gamma"])
        self.assertEqual(report["executionBlockedProviders"], ["alpha"])
        self.assertEqual(report["providerExecutionBurden"]["alpha"], 2)

    def test_validated_replayable_family_fans_out(self):
        mod.load_memory = lambda _root: {
            "schemaVersion": 2,
            "entries": [],
            "validatedFamilies": [{
                "repairFamily": {"key": "a" * 64},
                "mechanismFamily": "balanced-class-container",
                "successCount": 2,
            }],
        }
        selected, report = mod.select_wave(["alpha", "beta", "gamma"], ROOT)
        self.assertEqual(selected, ["alpha", "beta", "gamma"])
        self.assertEqual(report["deferredProviders"], [])
        self.assertEqual(report["validatedReplayableFamilyCount"], 1)

    def test_validated_non_replayable_family_stays_single_rep(self):
        mod.load_memory = lambda _root: {
            "schemaVersion": 2,
            "entries": [],
            "validatedFamilies": [{
                "repairFamily": {"key": "a" * 64},
                "mechanismFamily": "novel-provider-specific-mechanism",
                "successCount": 2,
            }],
        }
        selected, report = mod.select_wave(["alpha", "beta"], ROOT)
        self.assertEqual(selected, ["alpha"])
        self.assertEqual(report["deferredProviders"], ["beta"])
        self.assertEqual(report["validatedReplayableFamilyCount"], 0)


if __name__ == "__main__":
    unittest.main()
