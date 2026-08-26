"""Tests for the idempotent payment ledger."""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ledger.idempotency import check_idempotency_key, store_idempotency_key
from ledger.transaction import InsufficientFundsError, AccountNotFoundError


def make_mock_db(balance_rows=None):
    """Create a mock SQLAlchemy Session with configurable query results."""
    db = MagicMock()
    def execute_side_effect(query, params=None):
        result = MagicMock()
        q = str(query)
        if "account_balances" in q and "SELECT balance" in q:
            if balance_rows is not None:
                row = MagicMock()
                acct = params.get("id", "") if params else ""
                row.balance = balance_rows.get(acct, 100)
                result.fetchone.return_value = row
            else:
                result.fetchone.return_value = None
        elif "idempotency_keys" in q:
            result.fetchone.return_value = None
        else:
            result.fetchone.return_value = None
            result.rowcount = 1
        return result
    db.execute.side_effect = execute_side_effect
    return db


def test_check_idempotency_key_miss():
    db = make_mock_db()
    result = check_idempotency_key(db, "test-key-123")
    assert result is None


def test_reconciler_returns_report():
    from ledger.reconciler import reconcile
    db = MagicMock()
    # Mock journal sums query
    journal_row = MagicMock()
    journal_row.account_id = "acct-1"
    journal_row.computed_balance = 100.0
    db.execute.return_value.fetchall.return_value = [journal_row]
    # Mock balance query
    balance_row = MagicMock()
    balance_row.balance = 100.0
    db.execute.return_value.fetchone.return_value = balance_row
    # Mock total
    db.execute.return_value.scalar.return_value = 0.0

    report = reconcile(db)
    assert "clean" in report
    assert "discrepancies" in report
    assert "double_entry_balanced" in report


def test_transfer_raises_insufficient_funds():
    from ledger.transaction import transfer
    db = MagicMock()
    row = MagicMock(); row.balance = 10.0
    db.execute.return_value.fetchone.return_value = row
    with pytest.raises(InsufficientFundsError):
        transfer(db, "acct-a", "acct-b", Decimal("500.00"))


def test_transfer_raises_account_not_found():
    from ledger.transaction import transfer
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = None
    with pytest.raises(AccountNotFoundError):
        transfer(db, "bad-acct", "acct-b", Decimal("10.00"))
