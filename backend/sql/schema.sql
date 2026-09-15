-- MediMate — Milestone 1 Postgres schema (users table only).
-- Later milestones extend this with the remaining v1 tables
-- (medications, schedules, dose_events, ...). The same schema is defined
-- in ORM form in app/models.py (source of truth, auto-created at startup
-- via Base.metadata.create_all); this file is a reference copy / manual
-- bootstrap — keep it in sync with models.py.
-- All tables use UUID primary keys (gen_random_uuid(), PostgreSQL 13+;
-- Supabase/Neon are 14+/15+) so ids can be generated on-device during
-- offline-first sync without collisions (plan.md §8).

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- provides gen_random_uuid() on PG < 13

CREATE TABLE IF NOT EXISTS users (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(120)  NOT NULL,
    email               VARCHAR(255)  NOT NULL UNIQUE,
    password_hash       VARCHAR(255)  NOT NULL,
    role                VARCHAR(20)   NOT NULL CHECK (role IN ('patient', 'caretaker')),
    preferred_language  VARCHAR(5)    NOT NULL DEFAULT 'en' CHECK (preferred_language IN ('en', 'bn')),
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT now()
);