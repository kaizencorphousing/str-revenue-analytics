"""Streamlit dashboard: why October stalled, and where the money leaks.

Reads only data/processed/*.csv (written by src/export.py). It never touches the API,
the token or the raw data, so it is safe to deploy publicly.
Run: streamlit run app/dashboard.py
"""
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data" / "processed"

# One accent for "booked"; everything else is neutral.
ACCENT = "#2a78d6"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e6e5e1"
STATUS = {  # night_status -> (label, colour)
    "booked": ("Booked", ACCENT),
    "open_for_sale": ("Open for sale", "#dcdad5"),
    "vacant_past": ("Unsold (past)", "#a8a6a0"),
    "blocked": ("Blocked", "#52514e"),
    "not_in_snapshot": ("No data", "#f3f2ef"),
}
DEFAULT_RANGE = (date(2026, 8, 15), date(2026, 12, 31))  # same window as query 01

st.set_page_config(page_title="Why October stalled", layout="wide")
st.markdown("""<style>
[data-testid="stMetricValue"] { font-size: clamp(1.3rem, 2.4vw, 2.1rem); }
h3 { font-size: 1.2rem !important; }
</style>""", unsafe_allow_html=True)


@st.cache_data
def load():
    d = {p.stem: pd.read_csv(p) for p in DATA.glob("*.csv")}
    d["nightly"]["night_date"] = pd.to_datetime(d["nightly"]["night_date"])
    return d


def base_layout(fig, height=320, showlegend=False, margin=None, **kw):
    fig.update_layout(
        height=height, margin=margin or dict(l=8, r=8, t=36, b=8), plot_bgcolor="white", paper_bgcolor="white",
        font=dict(color=INK_2, size=13), hoverlabel=dict(bgcolor="white", font_color=INK),
        showlegend=showlegend, **kw)
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont_color=INK_2)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont_color=INK_2)
    return fig


def kpis(n: pd.DataFrame) -> dict:
    booked = n[n.night_status == "booked"]
    nights = len(n)
    net = round(n.net_rev_ex_cleaning.sum(), 2)
    return {
        "nights": nights, "booked": len(booked),
        "occupancy": round(100 * len(booked) / nights, 1) if nights else 0.0,
        "adr": round(booked.nightly_rate.mean(), 2) if len(booked) else 0.0,
        "net": net, "revpar": round(net / nights, 2) if nights else 0.0,
    }


d = load()
nightly, meta = d["nightly"], d["meta"].iloc[0]
rent = float(meta.rent_monthly)
clean_cost = float(d["cost_assumptions"].set_index("item").loc["turnover_clean", "amount"])

# ---------- sidebar ----------
st.sidebar.header("Filter")
lo, hi = nightly.night_date.min().date(), nightly.night_date.max().date()
picked = st.sidebar.date_input("Nights between", value=DEFAULT_RANGE, min_value=lo, max_value=hi)
start, end = (picked if isinstance(picked, (tuple, list)) and len(picked) == 2 else DEFAULT_RANGE)
st.sidebar.caption("Drives the KPI tiles, calendar, monthly and weekday charts. "
                   "Default is launch (Aug 15) to Dec 31 2026.")
n = nightly[(nightly.night_date.dt.date >= start) & (nightly.night_date.dt.date <= end)].copy()

# ---------- header ----------
st.title("Why October stalled: STR revenue analytics")
st.markdown("A 4-bed townhouse near the University of Florida, launched August 2026. "
            "September ran near-full on one 31-night stay; October and November stalled. "
            "This dashboard traces why, and where the revenue is recoverable.")
st.caption(f"Data snapshot: {meta.snapshot_date} · Source: Hospitable API (read-only), anonymized · "
           f"Showing nights {start:%b %d %Y} to {end:%b %d %Y}")

k = kpis(n)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Occupancy", f"{k['occupancy']:.1f}%", help=f"{k['booked']} of {k['nights']} nights booked")
c2.metric("ADR", f"${k['adr']:,.2f}", help="Average pre-discount nightly rate on booked nights")
c3.metric("Net RevPAR", f"${k['revpar']:,.2f}", help="Net revenue (ex cleaning) per calendar night")
c4.metric("Net revenue", f"${k['net']:,.2f}", help="Host payout minus cleaning fee and pass-through tax")

tab1, tab2 = st.tabs(["Why October stalled", "Where the money leaks"])

# ---------- findings (fixed to the launch-to-Dec-31 window, not the filter) ----------
f = nightly[(nightly.night_date.dt.date >= DEFAULT_RANGE[0]) & (nightly.night_date.dt.date <= DEFAULT_RANGE[1])]
by_month = f.groupby("year_month").apply(lambda g: (g.night_status == "booked").mean() * 100, include_groups=False)
wk = f.groupby("is_weekend").apply(lambda g: (g.night_status == "booked").mean() * 100, include_groups=False)
ch = d["channel_comparison"].set_index("platform")
lost = d["lost_requests"]
disc_total = d["discount_leakage"].set_index("discount_type").loc["TOTAL", "pct_of_gross_rent"]
pc = d["price_changes"]
# The night whose list price swung the most across the price-change log.
swing_night = pc.groupby("night_date").list_price.agg(lambda p: p.max() - p.min()).idxmax()
tex = pc[pc.night_date == swing_night].sort_values("changed_on")
swing_row = nightly[nightly.night_date == swing_night]
swing_status = STATUS[swing_row.night_status.iloc[0]][0].lower() if len(swing_row) else "unknown"
swing_event = f" ({swing_row.event.iloc[0]})" if len(swing_row) and pd.notna(swing_row.event.iloc[0]) else ""
lost_n = lost.lost_request.nunique()
lost_sold = lost.loc[lost.already_sold_at_request == 1, "lost_request"].nunique()
lost_phrase = f"all {lost_n}" if lost_sold == lost_n else f"{lost_sold} of {lost_n}"
res = d["reservations"]
acc = res[res.status == "accepted"].copy()
acc["contribution_per_night"] = (acc.host_revenue - acc.host_taxes - clean_cost) / acc.nights
long_stay = acc.loc[acc.nights.idxmax()]
short = acc[acc.nights <= 2]

# ---------- tab 1 ----------
with tab1:
    with st.container(border=True):
        st.subheader("Findings")
        st.markdown(rf"""
1. **Demand fell off a cliff after September.** Occupancy went from {by_month.get('2026-09', 0):.0f}% in September to
   {by_month.get('2026-10', 0):.0f}% in October and {by_month.get('2026-11', 0):.0f}% in November. *(Calendar, Monthly revenue)*
2. **Weeknights are the hole.** Sun–Thu nights sold {wk.get(0, 0):.0f}% vs {wk.get(1, 0):.0f}% for Fri/Sat. *(Weekday chart)*
3. **Pricing whipsawed.** {pd.Timestamp(swing_night):%a %b %d}{swing_event} was listed at \${tex.list_price.max():.0f} and ended at
   \${tex.list_price.iloc[-1]:.0f} after {len(tex) - 1} changes; status now: {swing_status}. *(Price history)*
4. **Vrbo lost on availability, not price.** Vrbo converted {int(ch.loc['vrbo', 'confirmed'])} of {int(ch.loc['vrbo', 'requests'])} requests;
   {lost_phrase} lost requests were for nights already sold on Airbnb. *(Tab 2, Channels)*
5. **Discounts and long stays dilute yield.** Discounts gave away {disc_total:.1f}% of gross rent, and the
   {int(long_stay.nights)}-night stay earned \${long_stay.contribution_per_night:,.0f}/night after cleaning vs
   \${(short.host_revenue - short.host_taxes - clean_cost).sum() / short.nights.sum():,.0f} for 1–2 night stays. *(Tab 2)*
""")

    # Calendar heatmap: weeks (x) by weekday (y)
    st.subheader("Every night, by status")
    order = list(STATUS)
    cal = n.assign(code=n.night_status.map(order.index),
                   week=(n.night_date - pd.to_timedelta(n.night_date.dt.weekday, unit="D")),
                   dow=n.night_date.dt.weekday)
    cal["price"] = cal.nightly_rate.fillna(cal.snapshot_price)
    cal["hover"] = (cal.night_date.dt.strftime("%a %b %d %Y") + "<br>" + cal.night_status.map(lambda s: STATUS[s][0])
                    + cal.price.map(lambda p: "" if pd.isna(p) else f"<br>Price: ${p:,.0f}")
                    + cal.event.map(lambda e: "" if pd.isna(e) else f"<br>Event: {e}"))
    cal["mark"] = cal.event.map(lambda e: "" if pd.isna(e) else "●")
    weeks = sorted(cal.week.unique())
    z = pd.DataFrame(index=range(7), columns=weeks, dtype=float)
    txt = pd.DataFrame("", index=range(7), columns=weeks)
    hov = pd.DataFrame("", index=range(7), columns=weeks)
    for r in cal.itertuples():
        z.loc[r.dow, r.week], txt.loc[r.dow, r.week], hov.loc[r.dow, r.week] = r.code, r.mark, r.hover
    scale = []
    for i, s in enumerate(order):
        lo_, hi_ = i / len(order), (i + 1) / len(order)
        scale += [[lo_, STATUS[s][1]], [hi_, STATUS[s][1]]]
    fig = go.Figure(go.Heatmap(
        z=z.values, x=[pd.Timestamp(w).strftime("%b %d") for w in weeks],
        y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        zmin=-0.5, zmax=len(order) - 0.5, colorscale=scale, showscale=False, xgap=2, ygap=2,
        text=txt.values, texttemplate="%{text}", textfont=dict(color=INK, size=9),
        customdata=hov.values, hovertemplate="%{customdata}<extra></extra>"))
    base_layout(fig, height=300)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(title_text="Week starting", tickangle=0, nticks=12)
    st.plotly_chart(fig, config={"displayModeBar": False})
    present = [s for s in order if s in set(n.night_status)]
    st.markdown(" &nbsp; ".join(
        f"<span style='display:inline-block;width:12px;height:12px;border-radius:3px;background:{STATUS[s][1]};"
        f"vertical-align:middle;border:1px solid {GRID}'></span> {STATUS[s][0]}" for s in present)
        + " &nbsp; ● event night", unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Monthly net revenue vs rent")
        m = n.groupby("year_month").agg(net=("net_rev_ex_cleaning", "sum"),
                                         booked=("night_status", lambda s: (s == "booked").sum()),
                                         nights=("night_status", "size")).reset_index()
        fig = go.Figure(go.Bar(
            x=m.year_month, y=m.net, marker_color=[INK_2 if v >= rent else MUTED for v in m.net],
            marker_cornerradius=4,
            customdata=m[["booked", "nights"]], hovertemplate="%{x}<br>Net revenue: $%{y:,.0f}"
            "<br>Booked %{customdata[0]} of %{customdata[1]} nights<extra></extra>"))
        fig.add_hline(y=rent, line_dash="dash", line_color=INK, line_width=1.5,
                      annotation_text=f"Rent ${rent:,.0f}", annotation_position="top right")
        base_layout(fig)
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
        st.plotly_chart(fig, config={"displayModeBar": False})
        st.caption("Dark bars covered rent. Partial months show only nights inside the filter.")

    with right:
        st.subheader("Fri/Sat vs Sun–Thu")
        w = n.assign(day_type=n.is_weekend.map({1: "Fri/Sat", 0: "Sun–Thu"}))
        g = w.groupby("day_type").agg(
            occ=("night_status", lambda s: 100 * (s == "booked").mean()),
            adr=("nightly_rate", "mean")).reindex(["Fri/Sat", "Sun–Thu"])
        a, b = st.columns(2)
        for col, field, title, fmt in ((a, "occ", "Occupancy %", "{:.0f}%"), (b, "adr", "Booked ADR", "${:,.0f}")):
            fig = go.Figure(go.Bar(x=g.index, y=g[field], marker_color=[INK_2, MUTED], marker_cornerradius=4,
                                   text=[fmt.format(v) if pd.notna(v) else "" for v in g[field]],
                                   textposition="outside", textfont_color=INK,
                                   hovertemplate="%{x}: %{text}<extra></extra>"))
            base_layout(fig, title=dict(text=title, font=dict(size=14, color=INK)))
            fig.update_yaxes(showticklabels=False, showgrid=False, range=[0, (g[field].max() or 1) * 1.25])
            col.plotly_chart(fig, config={"displayModeBar": False})

    left, right = st.columns(2)
    with left:
        st.subheader("List-price history, key nights")
        fig = go.Figure()
        ends = []
        for night, grp in pc.groupby("night_date"):
            grp = grp.sort_values("changed_on")
            label = pd.Timestamp(night).strftime("%a %b %d")
            fig.add_trace(go.Scatter(
                x=grp.changed_on, y=grp.list_price, mode="lines+markers", line_shape="hv",
                line=dict(width=2, color=MUTED), marker=dict(size=8, color=MUTED),
                name=label, customdata=grp.reason,
                hovertemplate=f"{label}<br>%{{x}}: $%{{y:,.0f}}<br>%{{customdata}}<extra></extra>"))
            ends.append((grp.list_price.iloc[-1], grp.changed_on.iloc[-1], label))
        # End labels, nudged apart so lines that finish at similar prices stay readable.
        min_gap = (pc.list_price.max() - pc.list_price.min()) * 0.07
        prev = None
        for price, x, label in sorted(ends, reverse=True):
            y = price if prev is None else min(price, prev - min_gap)
            prev = y
            fig.add_annotation(x=x, y=y, text=f"{label} ${price:,.0f}", xanchor="left", xshift=8,
                               showarrow=False, font=dict(size=11, color=INK_2))
        base_layout(fig, height=360, margin=dict(l=8, r=110, t=36, b=8))
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
        fig.update_xaxes(title_text="Date changed")
        st.plotly_chart(fig, config={"displayModeBar": False})

    with right:
        st.subheader("Our price vs market median (latest pull)")
        pm = d["price_vs_market"]
        pm = pm[pm.is_latest_pull == 1].sort_values("stay_start")
        fig = go.Figure(go.Bar(
            y=pm.stay_label + " · " + pm.pulled_on.str[5:], x=pm.gap_pct, orientation="h", marker_cornerradius=4,
            marker_color=[MUTED if v >= 0 else "#c9c7c1" for v in pm.gap_pct],
            text=[f"{v:+.1f}%" for v in pm.gap_pct], textposition="outside", textfont_color=INK, cliponaxis=False,
            customdata=pm[["our_total", "comp_median", "pulled_on"]],
            hovertemplate="%{y}<br>Ours $%{customdata[0]:,.0f} vs median $%{customdata[1]:,.0f}"
                          "<br>Gap %{x:+.1f}% (pulled %{customdata[2]})<extra></extra>"))
        fig.add_vline(x=0, line_color=INK, line_width=1.5)
        base_layout(fig, height=360)
        fig.update_xaxes(ticksuffix="%", title_text="Gap vs comp median (+ = we are pricier)", showgrid=True, gridcolor=GRID)
        fig.update_yaxes(autorange="reversed", showgrid=False)
        st.plotly_chart(fig, config={"displayModeBar": False})
        st.caption("Comps are manually pulled list prices, not achieved rates.")

# ---------- tab 2 ----------
with tab2:
    left, right = st.columns(2)
    with left:
        st.subheader("Discount leakage (% of gross rent)")
        dl = d["discount_leakage"]
        dl = dl[(dl.discount_type != "TOTAL") & (dl.discount_dollars > 0)].sort_values("pct_of_gross_rent")
        fig = go.Figure(go.Bar(
            y=dl.discount_type.str.replace("_", " "), x=dl.pct_of_gross_rent, orientation="h",
            marker_color=MUTED, marker_cornerradius=4, text=[f"{v:.1f}%" for v in dl.pct_of_gross_rent],
            textposition="outside", textfont_color=INK, customdata=dl.discount_dollars,
            hovertemplate="%{y}: %{x:.1f}% ($%{customdata:,.0f})<extra></extra>"))
        base_layout(fig)
        fig.update_xaxes(ticksuffix="%", range=[0, dl.pct_of_gross_rent.max() * 1.3])
        fig.update_yaxes(showgrid=False)
        st.plotly_chart(fig, config={"displayModeBar": False})
        st.caption(f"Total: {disc_total:.1f}% of pre-discount rent on accepted stays.")

    with right:
        st.subheader("Stay economics: longer stays earn less per night")
        fig = go.Figure(go.Scatter(
            x=acc.nights, y=acc.contribution_per_night, mode="markers",
            marker=dict(size=12, color=ACCENT, line=dict(color="white", width=2)),
            customdata=acc[["reservation_id", "platform", "checkin"]],
            hovertemplate="%{customdata[0]} (%{customdata[1]}), check-in %{customdata[2]}"
                          "<br>%{x} nights · $%{y:,.0f}/night after cleaning<extra></extra>"))
        base_layout(fig)
        fig.update_xaxes(type="log", title_text="Nights (log scale)", tickvals=[1, 2, 4, 8, 16, 31])
        fig.update_yaxes(tickprefix="$", tickformat=",.0f", title_text="Contribution per night")
        st.plotly_chart(fig, config={"displayModeBar": False})
        st.caption(f"Contribution = host payout − pass-through tax − ${clean_cost:,.0f} turnover clean.")

    st.subheader("Channels: Vrbo requests were lost to dates already sold on Airbnb")
    left, right = st.columns([1, 1])
    with left:
        cc = d["channel_comparison"]
        fig = go.Figure([
            go.Bar(name="Confirmed", x=cc.platform, y=cc.confirmed, marker_color=ACCENT, marker_cornerradius=4,
                   hovertemplate="%{x}: %{y} confirmed<extra></extra>"),
            go.Bar(name="Lost (declined/expired)", x=cc.platform, y=cc.lost, marker_color=MUTED, marker_cornerradius=4,
                   hovertemplate="%{x}: %{y} lost<extra></extra>"),
            go.Bar(name="Cancelled", x=cc.platform, y=cc.cancelled, marker_color="#c9c7c1", marker_cornerradius=4,
                   hovertemplate="%{x}: %{y} cancelled<extra></extra>"),
        ])
        base_layout(fig, barmode="group", bargap=0.3, bargroupgap=0.08, showlegend=True,
                    legend=dict(orientation="h", y=1.12, x=0, font=dict(color=INK_2)))
        fig.update_yaxes(title_text="Booking requests", dtick=2)
        st.plotly_chart(fig, config={"displayModeBar": False})
    with right:
        st.dataframe(
            cc.rename(columns={"platform": "Channel", "requests": "Requests", "confirmed": "Confirmed",
                               "lost": "Lost", "cancelled": "Cancelled", "conversion_pct": "Conversion %",
                               "fee_pct_of_gross": "Fee % of gross", "net_per_night": "Net $/night"}),
            hide_index=True)
        st.markdown("**Lost requests vs the stay that already held those nights**")
        st.dataframe(lost[["lost_request", "platform", "checkin", "checkout", "requested_on",
                           "overlapping_stay", "stay_booked_on"]].rename(columns={
                               "lost_request": "Lost", "platform": "Channel", "checkin": "Check-in",
                               "checkout": "Check-out", "requested_on": "Requested",
                               "overlapping_stay": "Held by", "stay_booked_on": "Held since"}),
                     hide_index=True)
        st.caption("Every lost Vrbo request overlapped an Airbnb stay booked weeks earlier: "
                   "which points to Vrbo availability not being blocked for nights that were already sold.")

st.divider()
st.caption("Built with Python, SQLite, SQL window functions, Streamlit and Plotly. "
           "Every number traces to a query in sql/analysis/.")
