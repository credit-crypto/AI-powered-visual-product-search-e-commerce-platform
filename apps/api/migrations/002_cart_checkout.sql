-- Cart / checkout / payment enhancements (apply after 001_catalogue_pgvector.sql).
-- psql "$DATABASE_URL_SYNC" -f migrations/002_cart_checkout.sql

CREATE UNIQUE INDEX IF NOT EXISTS idx_carts_session_token
    ON carts(session_token)
    WHERE session_token IS NOT NULL;

ALTER TABLE carts
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'converted', 'abandoned'));

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS email TEXT,
    ADD COLUMN IF NOT EXISTS cart_id UUID REFERENCES carts(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS payment_provider TEXT NOT NULL DEFAULT 'stub',
    ADD COLUMN IF NOT EXISTS payment_ref TEXT,
    ADD COLUMN IF NOT EXISTS checkout_session_id TEXT,
    ADD COLUMN IF NOT EXISTS reserved BOOLEAN NOT NULL DEFAULT false;

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_checkout_session_id
    ON orders(checkout_session_id)
    WHERE checkout_session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_orders_email ON orders(email);

ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS sku TEXT,
    ADD COLUMN IF NOT EXISTS product_name TEXT,
    ADD COLUMN IF NOT EXISTS currency CHAR(3) NOT NULL DEFAULT 'USD';

-- Idempotent payment webhook / event log
CREATE TABLE IF NOT EXISTS payment_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider        TEXT NOT NULL,
    event_id        TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    order_id        UUID REFERENCES orders(id) ON DELETE SET NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, event_id)
);
