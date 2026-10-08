-- Q: Does each month's net revenue cover rent, and if not, how many more nights would close the gap?
-- Assumptions: nights needed = rent gap / (avg current ask on open nights x (1 - 15.5% Airbnb host fee)),
-- rounded up; NULL when the month has no nights left for sale. Ignores cleaning costs and discounts.
-- Postgres: money columns would be NUMERIC; ROUND(float, 2) needs ROUND(x::numeric, 2), and SUM(boolean) needs COUNT(*) FILTER (WHERE ...).
WITH m AS (
    SELECT year_month,
           COALESCE(SUM(net_rev_ex_cleaning), 0)                                    AS net_revenue,
           SUM(night_status = 'open_for_sale')                                       AS open_for_sale,  -- Postgres: COUNT(*) FILTER (WHERE night_status = 'open_for_sale')
           AVG(CASE WHEN night_status = 'open_for_sale' THEN snapshot_price END)     AS avg_ask
    FROM fact_nightly
    GROUP BY year_month
),
rent AS (
    SELECT amount AS rent FROM cost_assumptions WHERE item = 'rent_monthly'
)
SELECT year_month,
       ROUND(net_revenue, 2)                  AS net_revenue,
       rent,
       ROUND(net_revenue - rent, 2)           AS surplus_or_gap,
       ROUND(100.0 * net_revenue / rent, 1)   AS rent_coverage_pct,
       open_for_sale,
       ROUND(avg_ask, 2)                      AS avg_ask,
       CASE WHEN net_revenue >= rent THEN 0
            WHEN avg_ask IS NULL THEN NULL
            ELSE CAST((rent - net_revenue) / (avg_ask * (1 - 0.155)) + 0.999999 AS INTEGER)  -- Postgres: CEIL(...)
       END                                    AS nights_needed,
       CASE WHEN net_revenue >= rent THEN 1
            WHEN avg_ask IS NULL THEN 0
            WHEN CAST((rent - net_revenue) / (avg_ask * (1 - 0.155)) + 0.999999 AS INTEGER) <= open_for_sale THEN 1
            ELSE 0 END                        AS feasible  -- 1 = enough open nights remain to close the gap (ignores min_stay)
FROM m CROSS JOIN rent
ORDER BY year_month;
