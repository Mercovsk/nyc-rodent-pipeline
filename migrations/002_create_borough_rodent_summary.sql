CREATE TABLE IF NOT EXISTS borough_rodent_summary (
    id                      SERIAL PRIMARY KEY,
    borough                 TEXT UNIQUE NOT NULL,
    total_inspections       INTEGER,
    passed                  INTEGER,
    pass_rate               NUMERIC,
    failed                  INTEGER,
    fail_rate               NUMERIC,
    treated                 INTEGER,
    treated_rate            NUMERIC,
    monitoring              INTEGER,
    monitoring_rate         NUMERIC,
    last_inspection_date    TIMESTAMP,
    refreshed_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);