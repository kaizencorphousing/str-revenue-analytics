-- SQLite schema for gainesville.db. Rebuilt from scratch on every load.
-- Money columns are dollars (converted once from API cents in src/transform.py).
-- Discounts and fees are stored as positive amounts (the API sends them negative).

DROP VIEW IF EXISTS fact_nightly;
DROP TABLE IF EXISTS reservation_nights;
DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS calendar_snapshot;
DROP TABLE IF EXISTS price_changes;
DROP TABLE IF EXISTS comps;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS cost_assumptions;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS data_quality_log;

-- One booking request (any status). Surrogate id R01, R02... ordered by check-in.
CREATE TABLE reservations (
    reservation_id           TEXT PRIMARY KEY,
    platform                 TEXT NOT NULL,          -- airbnb / vrbo
    booked_at                TEXT NOT NULL,          -- ISO date the request was made
    checkin                  TEXT NOT NULL,          -- ISO date
    checkout                 TEXT NOT NULL,          -- ISO date (morning of departure)
    nights                   INTEGER NOT NULL,
    guests                   INTEGER,
    status                   TEXT NOT NULL CHECK (status IN ('accepted','cancelled','declined','expired','request')),
    host_accommodation       REAL NOT NULL,          -- pre-discount rent
    cleaning_fee             REAL NOT NULL,
    discount_promo           REAL NOT NULL,
    discount_top_rated       REAL NOT NULL,
    discount_length_of_stay  REAL NOT NULL,
    discount_early_booking   REAL NOT NULL,
    discount_other           REAL NOT NULL,
    platform_fee             REAL NOT NULL,          -- channel fee: Airbnb host service fee / Vrbo commission
    pms_fee                  REAL NOT NULL,          -- Hospitable service fee (seen only on unconverted Vrbo requests)
    host_taxes               REAL NOT NULL,          -- pass-through lodging tax included in host_revenue
    host_revenue             REAL NOT NULL           -- payout to host as reported by the API
);

-- One booked night of an accepted reservation, at its pre-discount nightly rate.
CREATE TABLE reservation_nights (
    reservation_id  TEXT NOT NULL REFERENCES reservations(reservation_id),
    night_date      TEXT NOT NULL,
    nightly_rate    REAL NOT NULL,
    allocated       INTEGER NOT NULL CHECK (allocated IN (0,1)),  -- 1 = spread evenly, no breakdown
    PRIMARY KEY (reservation_id, night_date)
);

-- One night as seen in one calendar pull.
CREATE TABLE calendar_snapshot (
    snapshot_date  TEXT NOT NULL,
    night_date     TEXT NOT NULL,
    price          REAL,
    min_stay       INTEGER,
    status         TEXT NOT NULL CHECK (status IN ('open','reserved','blocked')),
    note           TEXT,
    PRIMARY KEY (snapshot_date, night_date)
);

CREATE TABLE price_changes (
    night_date  TEXT NOT NULL,
    changed_on  TEXT NOT NULL,
    list_price  REAL NOT NULL,
    reason      TEXT,
    PRIMARY KEY (night_date, changed_on)
);

CREATE TABLE comps (
    stay_label   TEXT NOT NULL,
    stay_start   TEXT NOT NULL,
    pulled_on    TEXT NOT NULL,
    comp_min     REAL,
    comp_median  REAL,
    comp_max     REAL,
    n_comps      INTEGER,
    our_total    REAL,
    PRIMARY KEY (stay_start, pulled_on)
);

CREATE TABLE events (
    night_date  TEXT PRIMARY KEY,
    event       TEXT NOT NULL,
    event_type  TEXT NOT NULL
);

CREATE TABLE cost_assumptions (
    item    TEXT PRIMARY KEY,
    amount  REAL NOT NULL,
    note    TEXT
);

-- Date spine. is_weekend marks Friday and Saturday nights.
CREATE TABLE dim_date (
    date        TEXT PRIMARY KEY,
    day_name    TEXT NOT NULL,
    is_weekend  INTEGER NOT NULL,
    year_month  TEXT NOT NULL,
    month       INTEGER NOT NULL,
    year        INTEGER NOT NULL
);

CREATE TABLE data_quality_log (
    log_id          INTEGER PRIMARY KEY,
    check_name      TEXT NOT NULL,
    reservation_id  TEXT,
    night_date      TEXT,
    detail          TEXT NOT NULL,
    action          TEXT NOT NULL
);

-- One row per date on the spine.
-- night_status: booked (accepted stay) / open_for_sale / blocked (latest snapshot)
--               / vacant_past (before the latest snapshot started, unsold) / not_in_snapshot.
CREATE VIEW fact_nightly AS
WITH latest AS (
    SELECT * FROM calendar_snapshot
    WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM calendar_snapshot)
),
booked AS (
    SELECT n.night_date, n.reservation_id, n.nightly_rate, n.allocated,
           r.platform, r.nights, r.host_revenue, r.cleaning_fee, r.host_taxes
    FROM reservation_nights n
    JOIN reservations r USING (reservation_id)
    WHERE r.status = 'accepted'
)
SELECT
    d.date AS night_date,
    d.day_name, d.is_weekend, d.year_month, d.month, d.year,
    b.reservation_id,
    b.platform,
    b.nightly_rate,
    b.allocated,
    ROUND((b.host_revenue - b.cleaning_fee - b.host_taxes) / b.nights, 2) AS net_rev_ex_cleaning,
    l.price  AS snapshot_price,
    l.status AS snapshot_status,
    e.event, e.event_type,
    CASE
        WHEN b.reservation_id IS NOT NULL THEN 'booked'
        WHEN d.date < (SELECT MAX(snapshot_date) FROM calendar_snapshot) THEN 'vacant_past'
        WHEN l.status = 'open'            THEN 'open_for_sale'
        WHEN l.status IS NOT NULL         THEN 'blocked'   -- reserved with no accepted stay, or owner block
        ELSE 'not_in_snapshot'
    END AS night_status
FROM dim_date d
LEFT JOIN booked b ON b.night_date = d.date
LEFT JOIN latest l ON l.night_date = d.date
LEFT JOIN events e ON e.night_date = d.date;
