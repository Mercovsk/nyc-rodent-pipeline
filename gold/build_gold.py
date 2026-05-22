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

MONTHLY_INSPECTION_TRENDS_QUERY_FROM_SILVER = """
    WITH monthly_trends AS (
        SELECT
            EXTRACT(YEAR FROM inspection_date) AS year,
            EXTRACT(MONTH FROM inspection_date) AS month,
            borough,
            COUNT(*)  total_inspections,
            COUNT(*) FILTER (WHERE result = 'Passed') AS passed,
            COUNT(*) FILTER (WHERE result IN ('Failed for Rat Act', 'Failed for Other R')) AS failed,
            COUNT(*) FILTER (WHERE result IN ('Bait applied', 'Stoppage done', 'Cleanup done')) AS treated,
            COUNT(*) FILTER (WHERE result IN ('Monitoring visit', 'Rat Activity')) AS monitoring
        FROM inspections
        GROUP BY 1, 2, 3
    )

    SELECT
        year,
        month,
        borough,
        total_inspections,
        passed,
        ROUND(passed * 100.0 / total_inspections, 2) AS pass_rate,
        failed,
        ROUND(failed * 100.0 / total_inspections, 2) AS fail_rate,
        treated,
        ROUND(treated * 100.0 / total_inspections, 2) AS treated_rate,
        monitoring,
        ROUND(monitoring * 100.0 / total_inspections, 2) AS monitoring_rate
    FROM monthly_trends
    WHERE borough IS NOT NULL
    ORDER BY 1 DESC, 2 DESC, 3 ASC
    ;
"""

ZIPCODE_HOTSPOTS_QUERY_FROM_SILVER = """
    WITH zip_code_summary AS (
        SELECT
            zip_code,
            borough,
            COUNT(*) AS total_inspections,
            COUNT(*) FILTER (WHERE result IN ('Failed for Rat Act', 'Failed for Other R')) AS failed,
            COUNT(*) FILTER (WHERE result IN ('Bait applied', 'Stoppage done', 'Cleanup done')) AS treated
        FROM inspections
        GROUP BY zip_code, borough
    )

    SELECT
        zip_code,
        borough,
        total_inspections,
        failed,
        ROUND(failed * 100.0 / total_inspections, 2) AS fail_rate,
        treated,
        ROUND(treated * 100.0 / total_inspections, 2) AS treated_rate,
        ROUND(((treated * 1.0) + (failed * 2.0)) / total_inspections * 100, 2) AS infestation_score
    FROM zip_code_summary
    WHERE zip_code IS NOT NULL AND borough IS NOT NULL
    ;
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

def build_monthly_inspection_trends(cur) -> None:
    cur.execute(MONTHLY_INSPECTION_TRENDS_QUERY_FROM_SILVER)
    rows = cur.fetchall()

    for row in rows:
        try:
            cur.execute("""
                INSERT INTO monthly_inspection_trends (
                    inspection_year,
                    inspection_month,
                    borough,
                    total_inspections,
                    passed,
                    pass_rate,
                    failed,
                    fail_rate,
                    treated,
                    treated_rate,
                    monitoring,
                    monitoring_rate
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (inspection_year, inspection_month, borough)
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
                    refreshed_at            = NOW()
            """, row)
        except Exception as e:
            logger.error(f"Failed to upsert monthly trend row {row[0]}-{row[1]}-{row[2]}: {e}")
            raise

def build_zipcode_hotspots(cur) -> None:
    cur.execute(ZIPCODE_HOTSPOTS_QUERY_FROM_SILVER)
    rows = cur.fetchall()

    for row in rows:
        try:
            cur.execute("""
                INSERT INTO zipcode_hotspots (
                    zip_code,
                    borough,
                    total_inspections,
                    failed,
                    fail_rate,
                    treated,
                    treated_rate,
                    infestation_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (zip_code)
                DO UPDATE SET
                    borough                 = EXCLUDED.borough,
                    total_inspections       = EXCLUDED.total_inspections,
                    failed                  = EXCLUDED.failed,
                    fail_rate               = EXCLUDED.fail_rate,
                    treated                 = EXCLUDED.treated,
                    treated_rate            = EXCLUDED.treated_rate,
                    infestation_score       = EXCLUDED.infestation_score,
                    refreshed_at            = NOW()
            """, row)
        except Exception as e:
            logger.error(f"Failed to upsert zipcode hotspot row {row[0]}-{row[1]}: {e}")
            raise

def run():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                build_borough_rodent_summary(cur)
                build_monthly_inspection_trends(cur)
                build_zipcode_hotspots(cur)
            conn.commit()
            logger.info("Gold layer build complete.")
    except Exception as e:
        logger.error(f"Error building gold layer: {e}")
        raise

if __name__ == "__main__":
    run()