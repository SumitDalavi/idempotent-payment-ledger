from fastapi import FastAPI, Header, HTTPException, Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

app = FastAPI()
engine = create_engine("postgresql://user:pass@localhost:5432/ledger", isolation_level="SERIALIZABLE")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@app.post("/transfer")
def transfer_funds(from_acct: str, to_acct: str, amount: float, idempotency_key: str = Header(...)):
    db = SessionLocal()
    try:
        # Check idempotency
        cached = db.execute(text("SELECT response FROM idempotency_keys WHERE key = :key"), {"key": idempotency_key}).fetchone()
        if cached: return cached[0]

        # Double-entry ledger logic
        db.execute(text("INSERT INTO entries (acct, amount) VALUES (:f, :am_neg), (:t, :am_pos)"), 
                   {"f": from_acct, "am_neg": -amount, "t": to_acct, "am_pos": amount})
        
        # Verify no negative balances
        balance = db.execute(text("SELECT sum(amount) FROM entries WHERE acct = :f"), {"f": from_acct}).scalar()
        if balance < 0:
            db.rollback()
            raise HTTPException(status_code=400, detail="Insufficient funds")

        response = {"status": "success", "transferred": amount}
        db.execute(text("INSERT INTO idempotency_keys (key, response) VALUES (:k, :r)"), {"k": idempotency_key, "r": str(response)})
        db.commit()
        return response
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
