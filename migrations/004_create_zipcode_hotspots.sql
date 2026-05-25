CREATE TABLE IF NOT EXISTS zipcode_hotspots (
    id                  SERIAL PRIMARY KEY,
    zip_code            TEXT NOT NULL,
    borough             TEXT NOT NULL,
    total_inspections   INTEGER,
    failed              INTEGER,
    fail_rate           NUMERIC,
    treated             INTEGER,
    treated_rate        NUMERIC,
    infestation_score   NUMERIC,
    refreshed_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);