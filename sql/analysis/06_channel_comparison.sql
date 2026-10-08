-- Q: How do Airbnb and Vrbo compare on conversion, fees and net yield?
-- Assumptions: requests = every booking record; lost = declined + expired; cancelled shown separately.
-- Fee % and net per night use accepted stays only; fee = channel fee (excludes the Hospitable fee).
SELECT
    platform,
    COUNT(*)                                                         AS requests,
    SUM(status = 'accepted')                                         AS confirmed,  -- Postgres: COUNT(*) FILTER (WHERE ...)
    SUM(status IN ('declined', 'expired'))                           AS lost,
    SUM(status = 'cancelled')                                        AS cancelled,
    ROUND(100.0 * SUM(status = 'accepted') / COUNT(*), 1)            AS conversion_pct,
    ROUND(100.0 * SUM(CASE WHEN status = 'accepted' THEN platform_fee END)
                / SUM(CASE WHEN status = 'accepted' THEN host_accommodation END), 1) AS fee_pct_of_gross,
    ROUND(SUM(CASE WHEN status = 'accepted' THEN host_revenue - cleaning_fee - host_taxes END)
          / SUM(CASE WHEN status = 'accepted' THEN nights END), 2)  AS net_per_night
FROM reservations
GROUP BY platform
ORDER BY platform;
