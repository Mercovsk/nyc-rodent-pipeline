CREATE TABLE IF NOT EXISTS monthly_inspection_trends (
    id                  SERIAL PRIMARY KEY,
    inspection_year     INTEGER NOT NULL,
    inspection_month    INTEGER NOT NULL,
    borough             TEXT NOT NULL,
    total_inspections   INTEGER,
    passed              INTEGER,
    pass_rate           NUMERIC,
    failed              INTEGER,
    fail_rate           NUMERIC,
    treated             INTEGER,
    treated_rate        NUMERIC,
    monitoring          INTEGER,
    monitoring_rate     NUMERIC,
    refreshed_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (inspection_year, inspection_month, borough)
);