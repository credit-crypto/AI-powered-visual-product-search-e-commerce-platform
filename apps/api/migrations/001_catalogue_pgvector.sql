-- Starter catalogue + pgvector schema for Visual Shop.
-- Apply with: psql "$DATABASE_URL" -f migrations/001_catalogue_pgvector.sql
-- Embedding dimension: 768 (SigLIP2 base patch16-224 — verify before production).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Catalogue
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    parent_id   UUID REFERENCES categories(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id     UUID REFERENCES categories(id) ON DELETE SET NULL,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'active', 'archived')),
    attributes      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);

CREATE TABLE IF NOT EXISTS product_images (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    storage_key     TEXT NOT NULL,
    url             TEXT,
    position        INT NOT NULL DEFAULT 0,
    is_primary      BOOLEAN NOT NULL DEFAULT false,
    width           INT,
    height          INT,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'processing', 'ready', 'failed')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_images_product_id ON product_images(product_id);
CREATE INDEX IF NOT EXISTS idx_product_images_status ON product_images(status);

CREATE TABLE IF NOT EXISTS product_variants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku             TEXT NOT NULL UNIQUE,
    name            TEXT,
    price_cents     INT NOT NULL CHECK (price_cents >= 0),
    currency        CHAR(3) NOT NULL DEFAULT 'USD',
    attributes      JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_default      BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants(product_id);

CREATE TABLE IF NOT EXISTS inventory (
    variant_id      UUID PRIMARY KEY REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity_on_hand    INT NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
    quantity_reserved   INT NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT inventory_available_nonneg CHECK (quantity_on_hand >= quantity_reserved)
);

-- ---------------------------------------------------------------------------
-- Visual search embeddings (pgvector)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS image_embeddings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_image_id    UUID NOT NULL UNIQUE REFERENCES product_images(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    model_name          TEXT NOT NULL DEFAULT 'google/siglip2-base-patch16-224',
    embedding           VECTOR(768) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_image_embeddings_product_id ON image_embeddings(product_id);

-- HNSW index for cosine similarity (<=> / cosine distance ops).
CREATE INDEX IF NOT EXISTS idx_image_embeddings_hnsw
    ON image_embeddings
    USING hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- Shopping / analytics stubs (minimal columns for later milestones)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    role            TEXT NOT NULL DEFAULT 'customer'
                        CHECK (role IN ('customer', 'admin')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS carts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    session_token   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cart_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id         UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    variant_id      UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity        INT NOT NULL CHECK (quantity > 0),
    UNIQUE (cart_id, variant_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'paid', 'fulfilled', 'cancelled', 'refunded')),
    total_cents     INT NOT NULL DEFAULT 0 CHECK (total_cents >= 0),
    currency        CHAR(3) NOT NULL DEFAULT 'USD',
    idempotency_key TEXT UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    variant_id      UUID NOT NULL REFERENCES product_variants(id),
    quantity        INT NOT NULL CHECK (quantity > 0),
    unit_price_cents INT NOT NULL CHECK (unit_price_cents >= 0)
);

CREATE TABLE IF NOT EXISTS search_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    query_type      TEXT NOT NULL DEFAULT 'image'
                        CHECK (query_type IN ('image', 'text')),
    result_count    INT,
    latency_ms      INT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
