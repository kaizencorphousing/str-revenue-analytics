# Resume bullets

**STR Revenue Analytics** · Python, SQL (SQLite), pandas, Streamlit, Plotly · [GitHub](https://github.com/kaizencorphousing/str-revenue-analytics) · Live dashboard: _link after deploy_

- Built an end-to-end analytics pipeline for a short-term rental I operate: extracted 15 reservations and 266 calendar nights from the Hospitable REST API (pagination, rate-limit backoff, read-only), modelled them in a 9-table SQLite model with a date-spine fact view, and served the results in a Streamlit dashboard (make it "public Streamlit dashboard" once deployed).
- Diagnosed an occupancy collapse from 77% in September to 19% in October and 7% in November with 13 SQL analyses (window functions, gaps and islands, interval self-joins). Identified weeknights (31% vs 51% weekend occupancy) and a 45-night unsold block before year-end worth $7,885 as the recoverable revenue.
- Found that all 5 lost Vrbo booking requests overlapped dates already sold on Airbnb, and that discounts consumed 22.5% of gross rent ($4,103). This led to recommendations on calendar sync, weekday pricing and length-of-stay discount caps.
- Engineered data quality into the pipeline: 6 automated reconciliation checks (nightly prices sum to stay rent to the cent, no double bookings), a data-quality log, 57 pytest tests on a synthetic fixture, and PII safeguards (surrogate keys, a git pre-commit PII scanner, anonymized exports). Headline KPIs matched an independent manual audit exactly.
