-- Q: How did the list price for key nights change over time, and by how much at each step?
-- Assumptions: seed log of manual price changes; the first change per night has no prior price.
SELECT
    night_date, changed_on, reason,
    LAG(list_price) OVER w                                    AS prior_price,
    list_price,
    list_price - LAG(list_price) OVER w                       AS change_dollars,
    ROUND(100.0 * (list_price - LAG(list_price) OVER w) / LAG(list_price) OVER w, 1) AS change_pct
FROM price_changes
WINDOW w AS (PARTITION BY night_date ORDER BY changed_on)  -- same named-window syntax in Postgres
ORDER BY night_date, changed_on;
