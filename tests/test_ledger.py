import asyncio
import uuid
import pytest
import os
import sqlite3
from httpx import AsyncClient, ASGITransport
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Register Decimal adapter for sqlite
sqlite3.register_adapter(Decimal, lambda d: str(d))
sqlite3.register_converter("DECIMAL", lambda s: Decimal(s.decode('utf-8')))

from main import app, get_db

# Use a local file DB for tests so threads can share the data
TEST_DB = "sqlite:///./test_ledger.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    from ledger.transaction import text
    db = TestingSessionLocal()
    db.execute(text("""
        CREATE TABLE accounts (
            id VARCHAR PRIMARY KEY,
            name VARCHAR,
            currency VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.execute(text("""
        CREATE TABLE account_balances (
            account_id VARCHAR PRIMARY KEY,
            balance DECIMAL DEFAULT 0,
            version INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.execute(text("""
        CREATE TABLE journal_entries (
            id VARCHAR PRIMARY KEY,
            transaction_id VARCHAR,
            account_id VARCHAR,
            amount DECIMAL,
            entry_type VARCHAR,
            description VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.execute(text("""
        CREATE TABLE idempotency_keys (
            key VARCHAR PRIMARY KEY,
            status_code INTEGER,
            response JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP DEFAULT (datetime('now', '+24 hours'))
        )
    """))
    db.commit()
    yield
    db.execute(text("DROP TABLE accounts"))
    db.execute(text("DROP TABLE account_balances"))
    db.execute(text("DROP TABLE journal_entries"))
    db.execute(text("DROP TABLE idempotency_keys"))
    db.commit()
    db.close()

from httpx import AsyncClient, ASGITransport

# ... (omitting top part since I only want to replace the fixture/client)
@pytest.mark.asyncio
async def test_idempotent_transfer():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create accounts
        acct1_res = await client.post("/api/v1/accounts", json={"name": "Alice"})
        acct2_res = await client.post("/api/v1/accounts", json={"name": "Bob"})
        a1_id = acct1_res.json()["id"]
        a2_id = acct2_res.json()["id"]

        # Fund Alice properly for the test (so reconciler stays happy)
        db = TestingSessionLocal()
        from sqlalchemy import text
        db.execute(text("INSERT INTO accounts (id, name, currency) VALUES ('system-acct', 'System', 'USD')"))
        db.execute(text("INSERT INTO account_balances (account_id, balance) VALUES ('system-acct', -100)"))
        db.execute(text("UPDATE account_balances SET balance = 100 WHERE account_id = :id"), {"id": a1_id})
        db.execute(text("""
            INSERT INTO journal_entries (id, transaction_id, account_id, amount, entry_type, description)
            VALUES 
                (:jid1, 'sys-deposit', :aid, 100, 'credit', 'Test funding'),
                (:jid2, 'sys-deposit', 'system-acct', -100, 'debit', 'Test funding')
        """), {"jid1": str(uuid.uuid4()), "jid2": str(uuid.uuid4()), "aid": a1_id})
        db.commit()

        ikey = str(uuid.uuid4())
        payload = {
            "from_account_id": a1_id,
            "to_account_id": a2_id,
            "amount": "50.00",
            "description": "Test Transfer"
        }
        
        # Fire 5 concurrent requests with the SAME idempotency key
        reqs = [
            client.post("/api/v1/transfers", json=payload, headers={"Idempotency-Key": ikey})
            for _ in range(5)
        ]
        
        responses = await asyncio.gather(*reqs)
        
        for r in responses:
            assert r.status_code in [200, 409, 500]
        
        # Ensure at least one succeeded
        successes = [r for r in responses if r.status_code == 200]
        assert len(successes) >= 1

        # Check balances
        b1 = await client.get(f"/api/v1/accounts/{a1_id}/balance")
        b2 = await client.get(f"/api/v1/accounts/{a2_id}/balance")
        
        assert Decimal(b1.json()["balance"]) == Decimal("50.00")
        assert Decimal(b2.json()["balance"]) == Decimal("50.00")
        
        # Check invariants
        rec = await client.post("/api/v1/reconcile")
        assert rec.status_code == 200
        assert rec.json()["clean"] is True
        assert rec.json()["journal_sum"] == 0.0
