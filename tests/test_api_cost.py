from __future__ import annotations

import json
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from niakvio_brain_llm.api_cost import BudgetLedger, cost_usd


class HostedBudgetTests(unittest.TestCase):
    def test_verified_per_model_price_estimator(self):
        self.assertEqual(cost_usd("gpt-6-luna", 6000, 1200), Decimal("0.0012"))
        self.assertEqual(cost_usd("gpt-6.1-terra", 6000, 1200), Decimal("0.012"))
        self.assertEqual(cost_usd("gpt-6.1-sol", 6000, 1200), Decimal("0.024"))
        self.assertEqual(cost_usd("gpt-6-astra", 6000, 1200), Decimal("0.12"))
        with self.assertRaises(ValueError):
            cost_usd("unknown", 1, 1)
        with self.assertRaises(ValueError):
            cost_usd("gpt-6-luna", -1, 1)

    def test_explicit_opt_in_for_budget_persistence(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(BudgetLedger.from_environment())
        with patch.dict(os.environ, {"NIAKVIO_API_BUDGET_USD": "0.02"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "LEDGER"):
                BudgetLedger.from_environment()
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {
                "NIAKVIO_API_BUDGET_USD": "0.02",
                "NIAKVIO_API_BUDGET_LEDGER": str(Path(folder)/"budget.json"),
            }, clear=True):
                self.assertEqual(BudgetLedger.from_environment().maximum_usd, Decimal("0.02"))

    def test_atomic_budget_reservations_and_usage_settlement(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"ledger.json"
            guard1=BudgetLedger(path, Decimal("0.005"))
            guard2=BudgetLedger(path, Decimal("0.005"))
            reservation=guard1.reserve("gpt-6-luna", b"{}", 2048)
            # A second worker sees the first reservation immediately.
            with self.assertRaisesRegex(RuntimeError, "budget exhausted"):
                guard2.reserve("gpt-6-luna", b"x"*15000, 8192)
            self.assertTrue(guard1.settle("gpt-6-luna", reservation, {
                "input_tokens": 6000, "output_tokens": 1200,
            }))
            row=json.loads(path.read_text())
            self.assertEqual(Decimal(row["spent_usd"]), Decimal("0.0012"))
            self.assertEqual(Decimal(row["pending_usd"]), Decimal("0"))
            self.assertEqual(row["requests_accounted"], 1)
            self.assertTrue(row["requests_reserved"] == 1)
            # Even if free generations are numerous, only dollars are capped.
            for _ in range(3):
                amount=guard2.reserve("gpt-6-luna", b"{}", 1024)
                guard2.settle("gpt-6-luna", amount, {"input_tokens": 1, "output_tokens": 1})

    def test_unknown_api_usage_keeps_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"ledger.json"
            guard=BudgetLedger(path,Decimal("0.003"))
            amount=guard.reserve("gpt-6-luna",b"short",2048)
            self.assertFalse(guard.settle("gpt-6-luna",amount,None))
            self.assertFalse(guard.settle("gpt-6-luna",amount,{"input_tokens":"10","output_tokens":10}))
            row=json.loads(path.read_text())
            self.assertEqual(Decimal(row["pending_usd"]),amount)
            self.assertEqual(row["requests_accounted"],0)

    def test_corrupted_or_suspicious_ledger_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"ledger.json"
            p.write_text('{"schemaVersion":1,"spent_usd":"-10","pending_usd":"0","requests_reserved":0,"requests_accounted":0}')
            guard=BudgetLedger(p,Decimal("5"))
            with self.assertRaises(ValueError):
                guard.reserve("gpt-6-luna",b"abc",1024)


if __name__ == "__main__":
    unittest.main()
