-- Q: After paying the cleaner, what does each stay length actually earn per night?
-- Assumptions: contribution = host payout - pass-through tax - one turnover clean (cost_assumptions).
-- The guest-paid cleaning fee stays in revenue because it is what offsets the clean.
WITH clean AS (
    SELECT amount AS turnover_clean FROM cost_assumptions WHERE item = 'turnover_clean'
),
stays AS (
    SELECT r.nights,
           CASE WHEN r.nights <= 2  THEN '1: 1-2 nights'
                WHEN r.nights <= 6  THEN '2: 3-6 nights'
                WHEN r.nights <= 27 THEN '3: 7-27 nights'
                ELSE '4: 28+ nights' END                          AS length_bucket,
           r.host_revenue - r.host_taxes - c.turnover_clean       AS contribution
    FROM reservations r CROSS JOIN clean c
    WHERE r.status = 'accepted'
)
SELECT length_bucket,
       COUNT(*)                                   AS stays,
       SUM(nights)                                AS nights,
       ROUND(SUM(contribution), 2)                AS contribution,
       ROUND(SUM(contribution) / SUM(nights), 2)  AS contribution_per_night,
       ROUND(AVG(contribution), 2)                AS contribution_per_stay
FROM stays
GROUP BY length_bucket
ORDER BY length_bucket;
