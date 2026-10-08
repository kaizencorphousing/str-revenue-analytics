-- Q: Were the requests we lost (declined/expired) for dates we had already sold?
-- Assumptions: self-join with interval overlap a.checkin < b.checkout AND a.checkout > b.checkin
-- (the checkout morning is free). "Already sold" = the overlapping accepted stay was booked
-- on or before the day the request came in.
SELECT
    a.reservation_id                                        AS lost_request,
    a.platform,
    a.status,
    a.checkin,
    a.checkout,
    a.booked_at                                             AS requested_on,
    b.reservation_id                                        AS overlapping_stay,
    b.platform                                              AS stay_platform,
    b.booked_at                                             AS stay_booked_on,
    CASE WHEN b.booked_at <= a.booked_at THEN 1 ELSE 0 END  AS already_sold_at_request,
    CAST(MIN(julianday(a.checkout), julianday(b.checkout))
       - MAX(julianday(a.checkin),  julianday(b.checkin)) AS INTEGER) AS overlap_nights  -- Postgres: LEAST()/GREATEST() on dates
FROM reservations a
LEFT JOIN reservations b
       ON b.status = 'accepted'
      AND a.checkin < b.checkout
      AND a.checkout > b.checkin
WHERE a.status IN ('declined', 'expired')
ORDER BY a.checkin, a.reservation_id;
