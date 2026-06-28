-- postgres/init.sql
-- Ejecutado automáticamente por PostgreSQL en el primer arranque.

CREATE TABLE IF NOT EXISTS consumer_accounts (
    account_id    SERIAL PRIMARY KEY,
    premise_id    TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    tariff_rules  JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_tariff_gin
    ON consumer_accounts USING GIN (tariff_rules);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id             SERIAL PRIMARY KEY,
    account_id             INTEGER REFERENCES consumer_accounts(account_id),
    billing_period_start   DATE,
    billing_period_end     DATE,
    consumption_kwh        NUMERIC,
    base_charge            NUMERIC,
    energy_charge          NUMERIC,
    regulatory_surcharge   NUMERIC,
    time_of_use_adjustment NUMERIC,
    total_amount           NUMERIC,
    status                 TEXT DEFAULT 'PENDING'
);
