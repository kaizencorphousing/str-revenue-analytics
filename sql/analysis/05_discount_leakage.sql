-- Q: How much pre-discount rent was given away in discounts, by type?
-- Assumptions: accepted stays only (all dates); gross rent = host_accommodation (pre-discount).
-- UNION ALL unpivots the five discount columns into rows.
WITH acc AS (
    SELECT * FROM reservations WHERE status = 'accepted'
),
long AS (
    SELECT 'top_rated' AS discount_type, discount_top_rated AS amount FROM acc
    UNION ALL SELECT 'length_of_stay', discount_length_of_stay FROM acc
    UNION ALL SELECT 'promo',          discount_promo          FROM acc
    UNION ALL SELECT 'early_booking',  discount_early_booking  FROM acc
    UNION ALL SELECT 'other',          discount_other          FROM acc
),
gross AS (
    SELECT SUM(host_accommodation) AS gross_rent FROM acc
)
SELECT discount_type,
       ROUND(SUM(amount), 2)                                  AS discount_dollars,
       ROUND(100.0 * SUM(amount) / MAX(gross.gross_rent), 1)  AS pct_of_gross_rent
FROM long CROSS JOIN gross
GROUP BY discount_type
UNION ALL
SELECT 'TOTAL',
       ROUND(SUM(amount), 2),
       ROUND(100.0 * SUM(amount) / MAX(gross.gross_rent), 1)
FROM long CROSS JOIN gross
ORDER BY discount_dollars DESC;
