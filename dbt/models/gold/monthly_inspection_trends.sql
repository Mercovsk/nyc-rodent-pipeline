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
    FROM {{ source('silver', 'inspections') }}
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