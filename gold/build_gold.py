from datetime import datetime
import logging
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from silver.db import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOROUGH_RODENT_SUMMARY_QUERY_FROM_SILVER = """
    WITH summary AS (
    SELECT
        borough,
        COUNT(*) AS total_inspections,
        COUNT(*) FILTER (WHERE result = 'Passed') AS passed,
        COUNT(*) FILTER (WHERE result IN ('Failed for Rat Act', 'Failed for Other R')) AS failed,
        COUNT(*) FILTER (WHERE result IN ('Bait applied', 'Stoppage done', 'Cleanup done')) AS treated,
        COUNT(*) FILTER (WHERE result IN ('Monitoring visit', 'Rat Activity')) AS monitoring,
        MAX(inspection_date) AS last_inspection_date
    FROM inspections
    GROUP BY borough
    )

    SELECT
        borough,
        total_inspections,
        passed,
        ROUND(passed * 100.0 / total_inspections, 2) AS pass_rate,
        failed,
        ROUND(failed * 100.0 / total_inspections, 2) AS fail_rate,
        treated,
        ROUND(treated * 100.0 / total_inspections, 2) as treated_rate,
        monitoring,
        ROUND(monitoring * 100.0 / total_inspections, 2) as monitoring_rate,
        last_inspection_date
    FROM summary
    WHERE borough IS NOT NULL;
"""

def build_borough_rodent_summary(cur) -> None:
    cur.execute(BOROUGH_RODENT_SUMMARY_QUERY_FROM_SILVER)
    rows = cur.fetchall()

    for row in rows:
        try:
            cur.execute("""
                INSERT INTO borough_rodent_summary (
                    borough,
                    total_inspections,
                    passed,
                    pass_rate,
                    failed,
                    fail_rate,
                    treated,
                    treated_rate,
                    monitoring,
                    monitoring_rate,
                    last_inspection_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (borough)
                DO UPDATE SET
                    total_inspections       = EXCLUDED.total_inspections,
                    passed                  = EXCLUDED.passed,
                    pass_rate               = EXCLUDED.pass_rate,
                    failed                  = EXCLUDED.failed,
                    fail_rate               = EXCLUDED.fail_rate,
                    treated                 = EXCLUDED.treated,
                    treated_rate            = EXCLUDED.treated_rate,
                    monitoring              = EXCLUDED.monitoring,
                    monitoring_rate         = EXCLUDED.monitoring_rate,
                    last_inspection_date    = EXCLUDED.last_inspection_date,
                    refreshed_at            = NOW()
            """, row)
        except Exception as e:
            logger.error(f"Failed to upsert row {row[0]}: {e}")
            raise

def run():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                build_borough_rodent_summary(cur)
            conn.commit()
            logger.info("Gold layer build complete.")
    except Exception as e:
        logger.error(f"Error building gold layer: {e}")
        raise

if __name__ == "__main__":
    run()