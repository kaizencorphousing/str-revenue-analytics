-- Q: How much higher are event nights priced than ordinary nights of the same day type?
-- Assumptions: price = booked pre-discount rate if sold, otherwise the latest list price;
-- past unsold nights have no price and are skipped, which biases event averages towards nights that sold. Baseline = non-event nights with the same is_weekend.
-- Postgres: money columns would be NUMERIC; ROUND(float, 2) needs ROUND(x::numeric, 2), and SUM(boolean) needs COUNT(*) FILTER (WHERE ...).
WITH priced AS (
    SELECT night_date, is_weekend, event_type,
           COALESCE(nightly_rate, snapshot_price) AS price
    FROM fact_nightly
    WHERE COALESCE(nightly_rate, snapshot_price) IS NOT NULL
),
baseline AS (
    SELECT is_weekend, AVG(price) AS base_price, COUNT(*) AS base_nights
    FROM priced
    WHERE event_type IS NULL
    GROUP BY is_weekend
)
SELECT p.event_type,
       CASE p.is_weekend WHEN 1 THEN 'Fri/Sat' ELSE 'Sun-Thu' END        AS day_type,
       COUNT(*)                                                        AS event_nights,
       ROUND(AVG(p.price), 2)                                          AS avg_event_price,
       ROUND(b.base_price, 2)                                          AS baseline_price,
       b.base_nights                                                   AS baseline_nights,
       ROUND(100.0 * (AVG(p.price) - b.base_price) / b.base_price, 1)  AS premium_pct
FROM priced p
JOIN baseline b USING (is_weekend)
WHERE p.event_type IS NOT NULL
GROUP BY p.event_type, p.is_weekend
ORDER BY premium_pct DESC;
