
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- provides gen_random_uuid() 

CREATE TABLE IF NOT EXISTS users (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(120)  NOT NULL,
    email               VARCHAR(255)  NOT NULL UNIQUE,
    password_hash       VARCHAR(255)  NOT NULL,
    role                VARCHAR(20)   NOT NULL CHECK (role IN ('patient', 'caretaker')),
    preferred_language  VARCHAR(5)    NOT NULL DEFAULT 'en' CHECK (preferred_language IN ('en', 'bn')),
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT now()
);
