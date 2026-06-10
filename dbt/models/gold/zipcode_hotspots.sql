WITH zip_code_summary AS (
    SELECT
        zip_code,
        borough,
        COUNT(*) AS total_inspections,
        COUNT(*) FILTER (WHERE result IN ('Failed for Rat Act', 'Failed for Other R')) AS failed,
        COUNT(*) FILTER (WHERE result IN ('Bait applied', 'Stoppage done', 'Cleanup done')) AS treated
    FROM {{ source('silver', 'inspections') }}
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