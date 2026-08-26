"""Idempotent Payment Ledger — FastAPI application."""
from __future__ import annotations
import os
from decimal import Decimal
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel, condecimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from ledger.idempotency import check_idempotency_key, store_idempotency_key
from ledger.transaction import transfer, get_balance, get_transaction_entries
from ledger.transaction import InsufficientFundsError, AccountNotFoundError
from ledger.reconciler import reconcile

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/ledger")
engine = create_engine(DATABASE_URL, isolation_level="SERIALIZABLE", pool_size=10)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI(title="Idempotent Payment Ledger", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: Decimal
    description: str = ""


class AccountRequest(BaseModel):
    name: str
    currency: str = "USD"


@app.post("/api/v1/accounts", status_code=201)
def create_account(req: AccountRequest, db: Session = Depends(get_db)):
    row = db.execute(
        text("INSERT INTO accounts (name, currency) VALUES (:n, :c) RETURNING id, name, currency, created_at"),
        {"n": req.name, "c": req.currency},
    ).fetchone()
    db.execute(text("INSERT INTO account_balances (account_id) VALUES (:id)"), {"id": str(row.id)})
    db.commit()
    return dict(row._mapping)


@app.get("/api/v1/accounts/{account_id}/balance")
def get_account_balance(account_id: str, db: Session = Depends(get_db)):
    try:
        balance = get_balance(db, account_id)
        return {"account_id": account_id, "balance": str(balance)}
    except AccountNotFoundError as e:
        raise HTTPException(404, str(e))


@app.post("/api/v1/transfers")
def create_transfer(
    req: TransferRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    # Check idempotency: return cached response if already processed
    cached = check_idempotency_key(db, idempotency_key)
    if cached:
        status_code, response = cached
        if status_code >= 400:
            raise HTTPException(status_code=status_code, detail=response)
        return response

    try:
        txn_id = transfer(db, req.from_account_id, req.to_account_id, req.amount, req.description)
        response = {"transaction_id": txn_id, "status": "completed", "amount": str(req.amount)}
        store_idempotency_key(db, idempotency_key, 200, response)
        db.commit()
        return response
    except InsufficientFundsError as e:
        db.rollback()
        err = {"error": "insufficient_funds", "detail": str(e)}
        store_idempotency_key(db, idempotency_key, 402, err)
        db.commit()
        raise HTTPException(402, err)
    except AccountNotFoundError as e:
        db.rollback()
        raise HTTPException(404, str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Transfer failed: {e}")


@app.get("/api/v1/transactions/{transaction_id}")
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    entries = get_transaction_entries(db, transaction_id)
    if not entries:
        raise HTTPException(404, "Transaction not found")
    return {"transaction_id": transaction_id, "entries": entries}


@app.post("/api/v1/reconcile")
def run_reconciliation(db: Session = Depends(get_db)):
    return reconcile(db)


@app.get("/health")
def health():
    return {"status": "ok"}
