-- Canonical schema. This is the contract between the Python ingestion service
-- and the TypeScript app — both read/write these tables. Keep changes additive
-- and versioned (0002_*.sql, ...).

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- fuzzy title matching for dedupe

-- Sources mirror sources.yaml plus runtime health stats.
CREATE TABLE IF NOT EXISTS source (
    id            text PRIMARY KEY,           -- matches sources.yaml id
    name          text NOT NULL,
    region        text NOT NULL,
    enabled       boolean NOT NULL DEFAULT false,
    last_run_at   timestamptz,
    last_ok_at    timestamptz,
    fail_count    integer NOT NULL DEFAULT 0,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS venue (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    address     text,
    lat         double precision,
    lng         double precision,
    region      text,
    website     text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (name, region)
);

CREATE TABLE IF NOT EXISTS event (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title         text NOT NULL,
    description   text,
    starts_at     timestamptz NOT NULL,
    ends_at       timestamptz,
    all_day       boolean NOT NULL DEFAULT false,
    venue_id      uuid REFERENCES venue(id) ON DELETE SET NULL,
    categories    text[] NOT NULL DEFAULT '{}',   -- from the interest taxonomy
    tags          text[] NOT NULL DEFAULT '{}',   -- free-form
    price_min     numeric,
    price_max     numeric,
    currency      text NOT NULL DEFAULT 'EUR',
    url           text,                           -- canonical source page
    ticket_url    text,
    image_url     text,
    organizer     text,
    region        text,
    status        text NOT NULL DEFAULT 'active', -- active | cancelled | expired
    dedupe_hash   text NOT NULL UNIQUE,           -- stable merge key
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS event_starts_at_idx ON event (starts_at);
CREATE INDEX IF NOT EXISTS event_categories_idx ON event USING gin (categories);
CREATE INDEX IF NOT EXISTS event_title_trgm_idx ON event USING gin (title gin_trgm_ops);

-- One event can come from several sources; keep every provenance link.
CREATE TABLE IF NOT EXISTS event_source (
    event_id     uuid NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    source_id    text NOT NULL REFERENCES source(id) ON DELETE CASCADE,
    source_url   text,
    raw_hash     text,                  -- content hash; skip re-extract if unchanged
    extracted_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, source_id)
);

CREATE INDEX IF NOT EXISTS event_source_raw_hash_idx ON event_source (raw_hash);
