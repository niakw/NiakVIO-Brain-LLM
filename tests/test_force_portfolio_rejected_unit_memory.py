from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "plan_batch_from_checkout.py"
SPEC = importlib.util.spec_from_file_location("force_portfolio_memory", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class ForcePortfolioRejectedUnitMemoryTests(unittest.TestCase):
    def test_rotated_exact_unit_hashes_survive_portfolio_without_source_bytes(self):
        first = "a" * 64
        second = "b" * 64
        observations = [
            {
                "stage": "force_validation_feedback",
                "reason": "no_op",
                "rejected_unit_sha256": first,
                "rotate_unit": True,
                "private_source": "MUST_NOT_SURVIVE",
            },
            {
                "stage": "force_validation_feedback",
                "reason": "causally_empty_deletion",
                "rejected_unit_sha256": second,
                "rotate_unit": True,
            },
            {
                "stage": "force_validation_feedback",
                "reason": "no_op",
                "rejected_unit_sha256": first,
                "rotate_unit": True,
            },
            {
                "stage": "force_validation_feedback",
                "reason": "syntax_error",
                "rejected_unit_sha256": "c" * 64,
                "rotate_unit": True,
            },
            {
                "stage": "force_validation_feedback",
                "reason": "no_op",
                "rejected_unit_sha256": "d" * 64,
                "rotate_unit": False,
            },
        ]
        hashes = mod.force_rejected_unit_hashes(observations)
        self.assertEqual(hashes, [first, second])
        rows = mod.force_portfolio_rejected_feedback(hashes)
        self.assertEqual([row["rejected_unit_sha256"] for row in rows], hashes)
        self.assertTrue(all(row["rotate_unit"] is True for row in rows))
        self.assertTrue(all(row["reason"] == "no_op" for row in rows))
        encoded = repr(rows)
        self.assertNotIn("MUST_NOT_SURVIVE", encoded)
        self.assertNotIn("private_source", encoded)

    def test_malformed_hashes_never_become_portfolio_memory(self):
        self.assertEqual(mod.force_portfolio_rejected_feedback([
            "", "x" * 64, "a" * 63, "a" * 65
        ]), [])
        self.assertEqual(mod.force_rejected_unit_hashes([
            {
                "stage": "force_validation_feedback",
                "reason": "no_op",
                "rejected_unit_sha256": "not-a-sha",
                "rotate_unit": True,
            }
        ]), [])


if __name__ == "__main__":
    unittest.main()
