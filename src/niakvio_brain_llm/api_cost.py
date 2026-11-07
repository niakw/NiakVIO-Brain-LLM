"""Optional, fail-closed shared cost guard for explicitly enabled hosted APIs.

No API request is made here. Providers, prompts, credentials and URLs are
never stored in the ledger, only aggregate dollar accounting.
"""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

# Published list prices (USD per million input/output tokens). Cached-input
# discounts are intentionally ignored, making estimates conservative.
RATES = {
    "gpt-6-luna": (Decimal("0.10"), Decimal("0.50")),
    "gpt-6.1-terra": (Decimal("1.00"), Decimal("5.00")),
    "gpt-6.1-sol": (Decimal("2.00"), Decimal("10.00")),
    "gpt-6-astra": (Decimal("10.00"), Decimal("50.00")),
}
MILLION = Decimal(1000000)


def _money(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("invalid hosted API budget ledger value") from None
    if not result.is_finite() or result < 0:
        raise ValueError("invalid hosted API budget ledger amount")
    return result


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    if model not in RATES or type(input_tokens) is not int or type(output_tokens) is not int:
        raise ValueError("unknown model or token count for hosted API cost")
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("negative hosted API token count")
    input_rate, output_rate = RATES[model]
    return (Decimal(input_tokens) * input_rate
            + Decimal(output_tokens) * output_rate) / MILLION


class BudgetLedger:
    """A shared filesystem budget; never a limit on attempts or repairs.

    The caller must ensure all workers share the SAME persistent file. Separate
    CI runners do not share this guard; provider-side billing limits are also
    required to enforce a global spend ceiling.
    """

    def __init__(self, path: str | Path, maximum_usd: Decimal) -> None:
        self.path = Path(path)
        self.maximum_usd = _money(maximum_usd)

    @classmethod
    def from_environment(cls) -> "BudgetLedger | None":
        raw = os.environ.get("NIAKVIO_API_BUDGET_USD")
        if raw is None:
            return None
        path = os.environ.get("NIAKVIO_API_BUDGET_LEDGER")
        if not path:
            raise RuntimeError("hosted budget requires NIAKVIO_API_BUDGET_LEDGER")
        return cls(path, _money(raw))

    @contextmanager
    def _locked(self) -> Iterator[tuple[Any, dict[str, Any]]]:
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(self.path, flags, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "r+", encoding="utf-8") as handle:
                descriptor = -1
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                raw = handle.read()
                state = json.loads(raw) if raw.strip() else {
                    "schemaVersion": 1,
                    "spent_usd": "0",
                    "pending_usd": "0",
                    "requests_reserved": 0,
                    "requests_accounted": 0,
                }
                if not isinstance(state, dict) or state.get("schemaVersion") != 1:
                    raise ValueError("untrusted hosted API budget ledger schema")
                for field in ("spent_usd", "pending_usd"):
                    _money(state.get(field))
                for field in ("requests_reserved", "requests_accounted"):
                    if type(state.get(field)) is not int or state[field] < 0:
                        raise ValueError("invalid hosted API budget counter")
                try:
                    yield handle, state
                except BaseException:
                    raise
                else:
                    handle.seek(0)
                    handle.write(json.dumps(state, sort_keys=True) + "\n")
                    handle.truncate()
                    handle.flush()
                    os.fsync(handle.fileno())
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            if descriptor != -1:
                os.close(descriptor)

    def reserve(self, model: str, request_body: bytes, output_limit: int) -> Decimal:
        if not isinstance(request_body, bytes) or type(output_limit) is not int:
            raise ValueError("invalid request for hosted API budget")
        # Conservative, tokenizer-independent upper estimate: any input token
        # can consume a byte, plus a buffer for protocol-specific tokens.
        reservation = cost_usd(model, len(request_body) + 1024, output_limit)
        with self._locked() as (_, state):
            spent, pending = _money(state["spent_usd"]), _money(state["pending_usd"])
            if spent + pending + reservation > self.maximum_usd:
                raise RuntimeError("hosted API monetary budget exhausted; no request sent")
            state["pending_usd"] = str(pending + reservation)
            state["requests_reserved"] += 1
        return reservation

    def settle(self, model: str, reservation: Decimal, usage: Any) -> bool:
        """Settle only verifiable provider usage. Unknown usage stays reserved.

        A failed, interrupted or malformed request can still be billable; do
        not optimistically refund without an authenticated usage record.
        """
        if not isinstance(usage, dict):
            return False
        in_tokens = usage.get("input_tokens")
        out_tokens = usage.get("output_tokens")
        if type(in_tokens) is not int or type(out_tokens) is not int:
            return False
        if in_tokens < 0 or out_tokens < 0:
            return False
        charged = cost_usd(model, in_tokens, out_tokens)
        with self._locked() as (_, state):
            pending = _money(state["pending_usd"])
            if pending < reservation:
                raise RuntimeError("hosted budget pending reservation mismatch")
            state["pending_usd"] = str(pending - reservation)
            state["spent_usd"] = str(_money(state["spent_usd"]) + charged)
            state["requests_accounted"] += 1
        return True
