# Rebuilding the main view in Tableau Public

This rebuilds the dashboard's first tab ("Why October stalled") in Tableau Public from the anonymized files in `data/processed/`. Nothing here needs the API, the token or the database.

Time: about 60 to 90 minutes the first time.

## 1. Connect the data

1. Install Tableau Public (free) and sign in.
2. **Connect → To a File → Text file** and pick `data/processed/nightly.csv`.
3. On the Data Source page, check the field types and fix any that are wrong:
   - `night_date` → **Date** (not Date & Time)
   - `is_weekend` → **Number (whole)**
   - `nightly_rate`, `net_rev_ex_cleaning`, `snapshot_price` → **Number (decimal)**
   - everything else → **String**
4. Add the other files as **separate data sources**, not joins, because they have different grains (one row per night vs one row per price change):
   - `price_changes.csv` (one row per price change)
   - `price_vs_market.csv` (one row per comp pull)
   - `meta.csv` (one row: snapshot date and monthly rent)

## 2. Calculated fields (in the `nightly` source)

Create these with **Analysis → Create Calculated Field**. The names matter because later steps refer to them.

| Name | Formula | Why |
|---|---|---|
| `Booked` | `IF [night_status] = "booked" THEN 1 ELSE 0 END` | 1 per booked night, so SUM counts nights |
| `Occupancy %` | `SUM([Booked]) / COUNT([night_date])` | Booked nights ÷ calendar nights. Format as a percentage with 1 decimal |
| `ADR` | `SUM(IF [night_status] = "booked" THEN [nightly_rate] END) / SUM([Booked])` | Pre-discount rate per booked night |
| `Net Revenue` | `SUM([net_rev_ex_cleaning])` | Payout minus cleaning fee and tax |
| `Net RevPAR` | `[Net Revenue] / COUNT([night_date])` | Net revenue per calendar night |
| `Day Type` | `IF [is_weekend] = 1 THEN "Fri/Sat" ELSE "Sun-Thu" END` | Groups nights for the weekday chart |
| `Week Start` | `DATETRUNC('week', [night_date], 'monday')` | Column for the calendar heatmap |
| `Weekday` | `DATENAME('weekday', [night_date])` | Row for the calendar heatmap |
| `Price Shown` | `IFNULL([nightly_rate], [snapshot_price])` | Booked rate if sold, otherwise the current ask |
| `Status Label` | `CASE [night_status] WHEN "booked" THEN "Booked" WHEN "open_for_sale" THEN "Open for sale" WHEN "vacant_past" THEN "Unsold (past)" WHEN "blocked" THEN "Blocked" ELSE "No data" END` | Readable legend |
| `Monthly Rent` | `2350` | Reference line. Keep it equal to `meta.csv` → `rent_monthly` |

**Date filter:** drag `night_date` to Filters, choose **Range of dates**, and set it to 2026-08-15 to 2026-12-31. Right-click the filter → **Apply to Worksheets → All Using This Data Source**, so every sheet uses the same window as the Streamlit default.

## 3. One sheet per chart

### Sheet "KPIs"
- Put `Measure Names` on Columns, and `Measure Values` on Text. Keep only `Occupancy %`, `ADR`, `Net RevPAR` and `Net Revenue` in the Measure Values card.
- **Check:** with the date filter at Aug 15 to Dec 31 2026, it must show **36.7%, $284.14, $63.21, $8,786.61**. These are the same numbers as `results/01_headline_kpis.csv`. If they differ, your filter or field types are wrong.

### Sheet "Calendar"
- Columns: `Week Start`, set to **exact date (discrete)**. Rows: `Weekday`. Sort the rows manually from Monday to Sunday.
- Marks: **Square**. Put `Status Label` on Color with these colours: Booked `#2a78d6`, Open for sale `#dcdad5`, Unsold (past) `#a8a6a0`, Blocked `#52514e`, No data `#f3f2ef`.
- Tooltip: `night_date`, `Status Label`, `Price Shown`, `event`.
- Optional: duplicate the sheet as a dual-axis layer that shows a small circle where `event` is not null.

### Sheet "Monthly revenue vs rent"
- Columns: `MONTH(night_date)` as **Month / Year** (discrete), so months from different years never merge. Rows: `Net Revenue`. Marks: **Bar**.
- **Analytics pane → Reference Line → Entire Table → Value = `Monthly Rent`**, labelled "Rent".
- Colour: `IF [Net Revenue] >= 2350 THEN "Covered" ELSE "Short" END` (create this as a calculated field). Covered = `#52514e` (dark grey), Short = `#8a8984`. Blue stays reserved for booked nights.

### Sheet "Fri/Sat vs Sun-Thu"
- Columns: `Day Type`. Rows: `Occupancy %` and `ADR`, shown as **two separate panes, not a dual axis** (the units differ). Marks: Bar, with a label on each bar.

### Sheet "Price history" (source: price_changes)
- Columns: `changed_on`, set to exact date. Rows: `list_price`. Marks: **Line** with path type **Step**. Put `night_date` on Detail, and on Label with "Line ends" ticked.

### Sheet "Price vs market" (source: price_vs_market)
- Filter `is_latest_pull` = 1. Rows: `stay_label`. Columns: `gap_pct`. Marks: Bar. Add a reference line at 0.

## 4. Dashboard layout

1. **New Dashboard**, size **Automatic** (or 1366 × 900 for a fixed laptop layout).
2. Title text: "Why October stalled: STR revenue analytics", with a subtitle line giving the snapshot date from `meta.csv`.
3. Layout from top to bottom:
   - Row 1: the KPIs sheet across the full width.
   - Row 2: Calendar across the full width.
   - Row 3: Monthly revenue vs rent | Fri/Sat vs Sun-Thu.
   - Row 4: Price history | Price vs market.
4. Show the `night_date` filter as a **slider** at the top right. It drives every sheet that uses the nightly source.
5. Add a text box with the 3 to 5 findings from the Streamlit dashboard, each ending with the name of its chart.
6. Keep blue `#2a78d6` for "booked" only and use greys everywhere else, matching the Streamlit version.

## 5. Publish

**File → Save to Tableau Public**. Tableau Public workbooks are public, so check first that only the anonymized `data/processed/` files are used (surrogate ids R01..., no names or codes). Put the link in the README next to the Streamlit link.
