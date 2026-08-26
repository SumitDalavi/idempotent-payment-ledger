-- Idempotent Payment Ledger Schema

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Accounts table
CREATE TABLE IF NOT EXISTS accounts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    currency    TEXT NOT NULL DEFAULT 'USD',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Double-entry journal: every transaction produces two entries (debit + credit)
CREATE TABLE IF NOT EXISTS journal_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  UUID NOT NULL,
    account_id      UUID NOT NULL REFERENCES accounts(id),
    amount          NUMERIC(20, 6) NOT NULL,  -- positive = credit, negative = debit
    entry_type      TEXT NOT NULL CHECK (entry_type IN ('debit', 'credit')),
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_journal_account ON journal_entries(account_id);
CREATE INDEX IF NOT EXISTS idx_journal_txn     ON journal_entries(transaction_id);

-- Idempotency keys: ensure duplicate requests return the same response
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key             TEXT PRIMARY KEY,
    response        JSONB NOT NULL,
    status_code     INT NOT NULL DEFAULT 200,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours'
);

CREATE INDEX IF NOT EXISTS idx_idem_expires ON idempotency_keys(expires_at);

-- Materialized account balances for fast reads
CREATE TABLE IF NOT EXISTS account_balances (
    account_id  UUID PRIMARY KEY REFERENCES accounts(id),
    balance     NUMERIC(20, 6) NOT NULL DEFAULT 0,
    version     BIGINT NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
