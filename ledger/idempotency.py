"""Idempotency key store — ensures duplicate payment requests return the same response."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Optional, Tuple, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


from fastapi import HTTPException

def check_idempotency_key(db: Session, key: str) -> Optional[Tuple[int, Any]]:
    """
    Check if an idempotency key was already processed.
    Returns (status_code, response_body) if found and not expired, else None.
    """
    # First, try to fetch an existing completed or processing request
    row = db.execute(
        text("""
            SELECT response, status_code FROM idempotency_keys
            WHERE key = :k AND expires_at > CURRENT_TIMESTAMP
        """),
        {"k": key},
    ).fetchone()
    if row and row.status_code is not None:
        return (row.status_code, row.response)
    if row and row.status_code is None:
        # A request is currently processing this key
        raise HTTPException(status_code=409, detail="Concurrent request processing")

    # Reserve the key
    try:
        db.execute(
            text("""
                INSERT INTO idempotency_keys (key, status_code, response, created_at, expires_at)
                VALUES (:k, NULL, NULL, CURRENT_TIMESTAMP, datetime('now', '+24 hours'))
            """),
            {"k": key},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrent request processing")
    
    return None


def store_idempotency_key(db: Session, key: str, status_code: int, response: Any):
    """Store the response for an idempotency key (called after successful processing)."""
    db.execute(
        text("""
            INSERT INTO idempotency_keys (key, status_code, response, created_at)
            VALUES (:key, :code, :resp, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET
                status_code = EXCLUDED.status_code,
                response = EXCLUDED.response
        """),
        {"key": key, "code": status_code, "resp": json.dumps(response)},
    )


def cleanup_expired_keys(db: Session) -> int:
    """Remove expired idempotency keys. Run periodically."""
    result = db.execute(text("DELETE FROM idempotency_keys WHERE expires_at < NOW()"))
    return result.rowcount
