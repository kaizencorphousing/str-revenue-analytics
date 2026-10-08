-- Q: Where are the runs of consecutive unsold nights in the latest calendar, and what are they worth at the current ask?
-- Assumptions: latest snapshot only, open nights only.
-- Gaps and islands: date minus ROW_NUMBER is constant within a run of consecutive dates.
-- Postgres: money columns would be NUMERIC; ROUND(float, 2) needs ROUND(x::numeric, 2), and SUM(boolean) needs COUNT(*) FILTER (WHERE ...).
WITH open_nights AS (
    SELECT night_date, price
    FROM calendar_snapshot
    WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM calendar_snapshot)
      AND status = 'open'
),
islands AS (
    SELECT night_date, price,
           julianday(night_date) - ROW_NUMBER() OVER (ORDER BY night_date) AS grp  -- Postgres: night_date::date - ROW_NUMBER() OVER (...)::int
    FROM open_nights
)
SELECT MIN(night_date)       AS gap_start,
       MAX(night_date)       AS gap_end,
       COUNT(*)              AS nights,
       ROUND(SUM(price), 2)  AS value_at_current_ask,
       ROUND(AVG(price), 2)  AS avg_ask
FROM islands
GROUP BY grp
ORDER BY gap_start;
