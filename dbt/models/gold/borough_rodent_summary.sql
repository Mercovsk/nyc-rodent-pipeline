WITH summary AS (
    SELECT
        borough,
        COUNT(*) AS total_inspections,
        COUNT(*) FILTER (WHERE result = 'Passed') AS passed,
        COUNT(*) FILTER (WHERE result IN ('Failed for Rat Act', 'Failed for Other R')) AS failed,
        COUNT(*) FILTER (WHERE result IN ('Bait applied', 'Stoppage done', 'Cleanup done')) AS treated,
        COUNT(*) FILTER (WHERE result IN ('Monitoring visit', 'Rat Activity')) AS monitoring,
        MAX(inspection_date) AS last_inspection_date
    FROM {{ source('silver', 'inspections') }}
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
WHERE borough IS NOT NULL