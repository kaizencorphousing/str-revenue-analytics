-- Q: Month by month, how full was the unit, at what price, and how did revenue compare to rent?
-- Assumptions: rent is the full monthly lease even in partial August (launch Aug 15);
-- open_nights = every unsold night (past vacant + still for sale).
-- Postgres: money columns would be NUMERIC; ROUND(float, 2) needs ROUND(x::numeric, 2), and SUM(boolean) needs COUNT(*) FILTER (WHERE ...).
SELECT
    year_month,
    COUNT(*)                                                        AS calendar_nights,
    SUM(night_status = 'booked')                                    AS booked_nights,  -- Postgres: SUM(CASE WHEN ... THEN 1 ELSE 0 END)
    SUM(night_status <> 'booked')                                   AS open_nights,
    ROUND(100.0 * SUM(night_status = 'booked') / COUNT(*), 1)       AS occupancy_pct,
    ROUND(AVG(CASE WHEN night_status = 'booked' THEN nightly_rate END), 2) AS adr,
    ROUND(COALESCE(SUM(net_rev_ex_cleaning), 0), 2)                 AS net_revenue,
    (SELECT amount FROM cost_assumptions WHERE item = 'rent_monthly') AS rent
FROM fact_nightly
GROUP BY year_month
ORDER BY year_month;
