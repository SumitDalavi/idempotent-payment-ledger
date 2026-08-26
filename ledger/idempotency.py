"""Idempotency key store — ensures duplicate payment requests return the same response."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Optional, Tuple, Any
from sqlalchemy import text
from sqlalchemy.orm import Session


def check_idempotency_key(db: Session, key: str) -> Optional[Tuple[int, Any]]:
    """
    Check if an idempotency key was already processed.
    Returns (status_code, response_body) if found and not expired, else None.
    """
    row = db.execute(
        text("SELECT response, status_code FROM idempotency_keys WHERE key = :k AND expires_at > NOW()"),
        {"k": key},
    ).fetchone()
    return (row.status_code, row.response) if row else None


def store_idempotency_key(db: Session, key: str, status_code: int, response: Any):
    """Store the response for an idempotency key (called after successful processing)."""
    db.execute(
        text("""
            INSERT INTO idempotency_keys (key, response, status_code)
            VALUES (:k, :r::jsonb, :s)
            ON CONFLICT (key) DO NOTHING
        """),
        {"k": key, "r": json.dumps(response), "s": status_code},
    )


def cleanup_expired_keys(db: Session) -> int:
    """Remove expired idempotency keys. Run periodically."""
    result = db.execute(text("DELETE FROM idempotency_keys WHERE expires_at < NOW()"))
    return result.rowcount
