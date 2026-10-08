-- Q: How did the unit perform from launch (Aug 15) to Dec 31 2026?
-- Assumptions: every spine date is a sellable night; ADR = pre-discount list price per booked night;
-- net revenue = host payout minus cleaning fee and pass-through tax, spread evenly per night.
-- Postgres: money columns would be NUMERIC; ROUND(float, 2) needs ROUND(x::numeric, 2), and SUM(boolean) needs COUNT(*) FILTER (WHERE ...).
SELECT
    COUNT(*)                                                        AS calendar_nights,
    SUM(night_status = 'booked')                                    AS booked_nights,  -- Postgres: SUM(CASE WHEN ... THEN 1 ELSE 0 END)
    ROUND(100.0 * SUM(night_status = 'booked') / COUNT(*), 1)       AS occupancy_pct,
    ROUND(AVG(CASE WHEN night_status = 'booked' THEN nightly_rate END), 2) AS adr,
    ROUND(SUM(net_rev_ex_cleaning), 2)                              AS net_revenue,
    ROUND(SUM(net_rev_ex_cleaning) / COUNT(*), 2)                   AS net_revpar
FROM fact_nightly
WHERE night_date BETWEEN '2026-08-15' AND '2026-12-31';
