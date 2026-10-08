-- Q: Do Fri/Sat nights sell differently from Sun-Thu nights (Aug 15 - Dec 31 2026)?
-- Assumptions: weekend = Friday and Saturday nights; ask = current list price on nights still for sale.
-- Postgres: money columns would be NUMERIC; ROUND(float, 2) needs ROUND(x::numeric, 2), and SUM(boolean) needs COUNT(*) FILTER (WHERE ...).
SELECT
    CASE is_weekend WHEN 1 THEN 'Fri/Sat' ELSE 'Sun-Thu' END        AS day_type,
    COUNT(*)                                                        AS calendar_nights,
    SUM(night_status = 'booked')                                    AS booked_nights,  -- Postgres: SUM(CASE WHEN ... THEN 1 ELSE 0 END)
    ROUND(100.0 * SUM(night_status = 'booked') / COUNT(*), 1)       AS occupancy_pct,
    ROUND(AVG(CASE WHEN night_status = 'booked' THEN nightly_rate END), 2)          AS booked_adr,
    SUM(night_status = 'open_for_sale')                             AS open_for_sale_nights,
    ROUND(AVG(CASE WHEN night_status = 'open_for_sale' THEN snapshot_price END), 2) AS avg_ask_open
FROM fact_nightly
WHERE night_date BETWEEN '2026-08-15' AND '2026-12-31'
GROUP BY is_weekend
ORDER BY is_weekend DESC;
