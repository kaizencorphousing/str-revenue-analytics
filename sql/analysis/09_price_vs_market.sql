-- Q: Is our total stay price above or below the comp median, and how did that move between pulls?
-- Assumptions: comps were pulled manually (seed data); gap = our total - comp median.
SELECT
    stay_label, stay_start, pulled_on, n_comps,
    comp_median, our_total,
    our_total - comp_median                                    AS gap_dollars,
    ROUND(100.0 * (our_total - comp_median) / comp_median, 1)  AS gap_pct,
    CASE WHEN ROW_NUMBER() OVER (PARTITION BY stay_start ORDER BY pulled_on DESC) = 1
         THEN 1 ELSE 0 END                                     AS is_latest_pull
FROM comps
ORDER BY stay_start, pulled_on;
