"""
ACID transaction engine for double-entry bookkeeping.
Every transfer creates two journal entries and updates account balances atomically.
"""
from __future__ import annotations
import uuid
from decimal import Decimal
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


class InsufficientFundsError(Exception):
    pass

class AccountNotFoundError(Exception):
    pass


def get_balance(db: Session, account_id: str) -> Decimal:
    row = db.execute(
        text("SELECT balance FROM account_balances WHERE account_id = :id"),
        {"id": account_id},
    ).fetchone()
    if row is None:
        raise AccountNotFoundError(f"Account {account_id} not found")
    return Decimal(str(row.balance))


def transfer(
    db: Session,
    from_account_id: str,
    to_account_id: str,
    amount: Decimal,
    description: str = "",
) -> str:
    """
    Execute a double-entry transfer atomically under SERIALIZABLE isolation.
    Returns the transaction_id UUID string.

    Raises:
        InsufficientFundsError: if the source account has insufficient funds.
        AccountNotFoundError: if either account doesn't exist.
    """
    if amount <= 0:
        raise ValueError(f"Transfer amount must be positive, got {amount}")

    txn_id = str(uuid.uuid4())

    # Lock both accounts in consistent order (lower ID first) to prevent deadlocks
    ids = sorted([from_account_id, to_account_id])
    for aid in ids:
        row = db.execute(
            text("SELECT balance FROM account_balances WHERE account_id = :id FOR UPDATE"),
            {"id": aid},
        ).fetchone()
        if row is None:
            raise AccountNotFoundError(f"Account {aid} has no balance record")

    # Check sufficient funds
    from_balance = get_balance(db, from_account_id)
    if from_balance < amount:
        raise InsufficientFundsError(
            f"Insufficient funds: balance={from_balance}, requested={amount}"
        )

    # Write double-entry journal entries
    db.execute(
        text("""
            INSERT INTO journal_entries (id, transaction_id, account_id, amount, entry_type, description)
            VALUES
                (:d_id, :txn, :from_acct, :neg_amount, 'debit', :desc),
                (:c_id, :txn, :to_acct,   :pos_amount, 'credit', :desc)
        """),
        {
            "d_id": str(uuid.uuid4()), "c_id": str(uuid.uuid4()),
            "txn": txn_id,
            "from_acct": from_account_id, "neg_amount": -amount,
            "to_acct": to_account_id,     "pos_amount": amount,
            "desc": description,
        },
    )

    # Update materialized balances
    db.execute(
        text("""
            UPDATE account_balances SET balance = balance - :amount, updated_at = NOW(), version = version + 1
            WHERE account_id = :id
        """),
        {"amount": amount, "id": from_account_id},
    )
    db.execute(
        text("""
            UPDATE account_balances SET balance = balance + :amount, updated_at = NOW(), version = version + 1
            WHERE account_id = :id
        """),
        {"amount": amount, "id": to_account_id},
    )

    return txn_id


def get_transaction_entries(db: Session, transaction_id: str) -> list:
    """Retrieve all journal entries for a transaction (for audit)."""
    rows = db.execute(
        text("""
            SELECT je.id, je.account_id, a.name, je.amount, je.entry_type, je.description, je.created_at
            FROM journal_entries je
            JOIN accounts a ON a.id = je.account_id
            WHERE je.transaction_id = :txn
            ORDER BY je.entry_type DESC
        """),
        {"txn": transaction_id},
    ).fetchall()
    return [dict(r._mapping) for r in rows]
