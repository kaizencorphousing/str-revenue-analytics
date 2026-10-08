-- Q: How far ahead do confirmed guests book? Buckets plus the median.
-- Assumptions: lead time = check-in date minus booking date, accepted stays only.
-- Median via ROW_NUMBER: SQLite has no PERCENTILE_CONT (Postgres would use
-- PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lead_days)).
WITH stays AS (
    SELECT reservation_id,
           CAST(julianday(checkin) - julianday(booked_at) AS INTEGER) AS lead_days  -- Postgres: checkin::date - booked_at::date
    FROM reservations
    WHERE status = 'accepted'
),
ranked AS (
    SELECT lead_days,
           ROW_NUMBER() OVER (ORDER BY lead_days) AS rn,
           COUNT(*) OVER ()                       AS n
    FROM stays
),
buckets AS (
    SELECT CASE WHEN lead_days <= 7  THEN '1: 0-7 days'
                WHEN lead_days <= 30 THEN '2: 8-30 days'
                WHEN lead_days <= 60 THEN '3: 31-60 days'
                WHEN lead_days <= 90 THEN '4: 61-90 days'
                ELSE '5: 91+ days' END AS bucket,
           lead_days
    FROM stays
)
SELECT bucket, COUNT(*) AS stays, MIN(lead_days) AS min_days, MAX(lead_days) AS max_days, NULL AS median_days
FROM buckets
GROUP BY bucket
UNION ALL
-- middle row (odd n) or average of the two middle rows (even n)
SELECT '6: all stays', MAX(n), NULL, NULL, AVG(lead_days)
FROM ranked
WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
ORDER BY bucket;
