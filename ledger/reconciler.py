"""Balance reconciler — verifies that journal entries and balances are consistent."""
from __future__ import annotations
from decimal import Decimal
from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session


def reconcile(db: Session) -> Dict:
    """
    Reconcile materialized balances against journal entry sums.
    Returns a report with any discrepancies found.
    """
    # Sum journal entries per account
    journal_sums = db.execute(
        text("""
            SELECT account_id, SUM(amount) AS computed_balance
            FROM journal_entries
            GROUP BY account_id
        """)
    ).fetchall()

    discrepancies = []
    for row in journal_sums:
        acct_id = str(row.account_id)
        computed = Decimal(str(row.computed_balance))
        stored_row = db.execute(
            text("SELECT balance FROM account_balances WHERE account_id = :id"),
            {"id": acct_id},
        ).fetchone()
        if stored_row is None:
            discrepancies.append({"account_id": acct_id, "issue": "balance record missing"})
            continue
        stored = Decimal(str(stored_row.balance))
        diff = abs(computed - stored)
        if diff > Decimal("0.000001"):
            discrepancies.append({
                "account_id": acct_id,
                "computed_from_journal": float(computed),
                "stored_balance": float(stored),
                "discrepancy": float(diff),
            })

    # Double-entry check: total of all journal entries must be zero
    total = db.execute(text("SELECT COALESCE(SUM(amount), 0) FROM journal_entries")).scalar()
    total_balanced = abs(Decimal(str(total))) < Decimal("0.000001")

    return {
        "total_accounts_checked": len(journal_sums),
        "discrepancies": discrepancies,
        "double_entry_balanced": total_balanced,
        "journal_sum": float(total),
        "clean": len(discrepancies) == 0 and total_balanced,
    }
