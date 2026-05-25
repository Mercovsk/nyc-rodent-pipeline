CREATE TABLE IF NOT EXISTS inspections (
    id                  SERIAL PRIMARY KEY,
    socrata_id          TEXT UNIQUE NOT NULL,
    inspection_type     TEXT,
    borough             TEXT,
    zip_code            TEXT,
    inspection_date     TIMESTAMP,
    result              TEXT,
    approved_date       TIMESTAMP,
    latitude            NUMERIC,
    longitude           NUMERIC,
    nta                 TEXT,
    community_board     TEXT,
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
);