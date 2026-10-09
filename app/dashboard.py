"""Streamlit dashboard: why October stalled, and where the money leaks.

Reads only data/processed/*.csv (written by src/export.py). It never touches the API,
the token or the raw data, so it is safe to deploy publicly.
Styled in the Kaizen Corp Housing brand: black, ivory, one gold; 0px corners; 1px hairlines.
Run: streamlit run app/dashboard.py
"""
import base64
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP = Path(__file__).resolve().parent
DATA = APP.parent / "data" / "processed"

# ---------- Kaizen brand tokens ----------
BLACK, GRAPHITE, HAIRLINE = "#050505", "#0C0C0B", "#2E2A1D"
IVORY, STONE, GOLD = "#F2EFE6", "#A09A8C", "#D4AF5F"
FAINT = "#7D786C"   # dimmer stone, for recessive marks
RULE = "#1A1913"    # gridlines, quieter than the hairline
SANS, MONO, HEAD = "IBM Plex Sans, sans-serif", "IBM Plex Mono, monospace", "Jost, sans-serif"

# Gold means "booked / net money" everywhere; everything else is a warm neutral.
STATUS = {  # night_status -> (label, colour)
    "booked": ("Booked", GOLD),
    "open_for_sale": ("Open for sale", "#2B2820"),
    "vacant_past": ("Unsold (past)", FAINT),
    "blocked": ("Blocked", STONE),
    "not_in_snapshot": ("No data", "#121110"),
}
DEFAULT_RANGE = (date(2026, 8, 15), date(2026, 12, 31))  # same window as query 01

st.set_page_config(page_title="Why October stalled · Kaizen", page_icon=str(APP / "assets" / "k-mark.png"),
                   layout="wide")

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Jost:wght@300;400&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
.block-container {{ padding-top: 4.2rem; max-width: 1280px; }}
h1, h2, h3 {{ font-family: {HEAD} !important; font-weight: 300 !important; letter-spacing: .01em; color: {IVORY}; }}
.kz-eyebrow {{ font-family: {MONO}; font-size: 11px; letter-spacing: .22em; text-transform: uppercase; color: {GOLD}; margin: 0 0 6px; }}
.kz-muted {{ color: {STONE}; }}
.kz-rule {{ border: 0; border-top: 1px solid {HAIRLINE}; margin: 18px 0 22px; }}
.kz-brand {{ display: flex; align-items: center; gap: 14px; }}
.kz-brand img {{ height: 34px; }}
.kz-word {{ font-family: {HEAD}; font-weight: 300; letter-spacing: .42em; font-size: 18px; color: {IVORY}; line-height: 1.1; }}
.kz-word small {{ display: block; font-family: {MONO}; letter-spacing: .32em; font-size: 9px; color: {GOLD}; margin-top: 4px; }}
.kz-head {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; flex-wrap: wrap; }}
.kz-title {{ font-family: {HEAD}; font-weight: 300; font-size: clamp(2rem, 4.2vw, 3.2rem); line-height: 1.05; color: {IVORY}; margin: 0; }}
.kz-lede {{ color: {STONE}; max-width: 720px; margin: 12px 0 0; font-size: 15px; line-height: 1.6; }}
.kz-stamp {{ font-family: {MONO}; font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: {STONE}; text-align: right; }}
.kz-kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border: 1px solid {HAIRLINE}; background: {GRAPHITE}; }}
.kz-kpi {{ padding: 18px 20px; border-right: 1px solid {HAIRLINE}; min-width: 0; }}
.kz-kpi:last-child {{ border-right: 0; }}
.kz-kpi .v {{ font-family: {MONO}; font-size: clamp(1.4rem, 2.6vw, 2.15rem); color: {IVORY}; margin-top: 6px; white-space: nowrap; }}
.kz-kpi .v.gold {{ color: {GOLD}; }}
.kz-kpi .s {{ color: {STONE}; font-size: 12px; margin-top: 4px; }}
.kz-find {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 0; border-top: 1px solid {HAIRLINE}; border-left: 1px solid {HAIRLINE}; }}
.kz-find .kz-card {{ grid-column: span 2; }} .kz-find .kz-card:nth-child(-n+2) {{ grid-column: span 3; }}
.kz-card {{ background: {GRAPHITE}; padding: 18px 18px 16px; border-right: 1px solid {HAIRLINE}; border-bottom: 1px solid {HAIRLINE}; }}
.kz-num {{ display: inline-block; font-family: {MONO}; font-size: 11px; color: {GOLD}; border: 1px solid {HAIRLINE}; padding: 2px 7px; }}
.kz-card h4 {{ font-family: {HEAD}; font-weight: 400; font-size: 17px; color: {IVORY}; margin: 12px 0 6px; line-height: 1.3; }}
.kz-card p {{ color: {STONE}; font-size: 13.5px; line-height: 1.55; margin: 0; }}
.kz-card .fig {{ font-family: {MONO}; color: {IVORY}; }}
.kz-card .tag {{ font-family: {MONO}; font-size: 10px; letter-spacing: .16em; text-transform: uppercase; color: {FAINT}; margin-top: 10px; }}
.kz-legend {{ font-family: {MONO}; font-size: 11px; letter-spacing: .08em; color: {STONE}; display: flex; flex-wrap: wrap; gap: 18px; margin-top: 2px; }}
.kz-legend i {{ display: inline-block; width: 11px; height: 11px; margin-right: 7px; vertical-align: -1px; border: 1px solid {HAIRLINE}; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ background: {GRAPHITE}; border-radius: 0 !important; }}
[data-testid="stCaptionContainer"] {{ color: {FAINT} !important; font-size: 12px; }}
[data-testid="stTab"], [data-testid="stTab"] p {{ font-family: {MONO} !important; text-transform: uppercase; letter-spacing: .16em; font-size: 12px !important; color: {STONE}; }}
[data-testid="stTab"][aria-selected="true"], [data-testid="stTab"][aria-selected="true"] p {{ color: {GOLD} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {GOLD}; }}
[data-testid="stSidebar"] label {{ font-family: {MONO}; text-transform: uppercase; letter-spacing: .14em; font-size: 11px; color: {STONE}; }}
@media (max-width: 900px) {{ .kz-find {{ grid-template-columns: 1fr; }} .kz-find .kz-card, .kz-find .kz-card:nth-child(-n+2) {{ grid-column: auto; }} }}
@media (max-width: 760px) {{ .kz-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .kz-kpi:nth-child(2) {{ border-right: 0; }} .kz-kpi:nth-child(-n+2) {{ border-bottom: 1px solid {HAIRLINE}; }}
  .kz-stamp {{ text-align: left; }} }}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load():
    d = {p.stem: pd.read_csv(p) for p in DATA.glob("*.csv")}
    d["nightly"]["night_date"] = pd.to_datetime(d["nightly"]["night_date"])
    return d


@st.cache_data
def logo_b64() -> str:
    return base64.b64encode((APP / "assets" / "k-mark.png").read_bytes()).decode()


def section(eyebrow: str, title: str):
    st.markdown(f"<p class='kz-eyebrow'>{eyebrow}</p><h3 style='margin:0 0 4px'>{title}</h3>",
                unsafe_allow_html=True)


def base_layout(fig, height=320, showlegend=False, margin=None, **kw):
    fig.update_layout(
        height=height, margin=margin or dict(l=8, r=12, t=24, b=8),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=SANS, color=STONE, size=12),
        hoverlabel=dict(bgcolor=BLACK, bordercolor=HAIRLINE, font=dict(family=MONO, color=IVORY, size=12)),
        showlegend=showlegend, **kw)
    fig.update_xaxes(showgrid=False, linecolor=HAIRLINE, tickfont=dict(family=MONO, color=STONE, size=11),
                     title_font=dict(family=MONO, color=FAINT, size=11))
    fig.update_yaxes(gridcolor=RULE, zeroline=False, linecolor=HAIRLINE,
                     tickfont=dict(family=MONO, color=STONE, size=11), title_font=dict(family=MONO, color=FAINT, size=11))
    return fig


def show(fig):
    st.plotly_chart(fig, config={"displayModeBar": False})


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
st.sidebar.markdown(
    f"<div class='kz-brand'><img src='data:image/png;base64,{logo_b64()}' alt='Kaizen K mark'>"
    f"<div class='kz-word'>KAIZEN<small>CORP HOUSING</small></div></div><hr class='kz-rule'>",
    unsafe_allow_html=True)
lo, hi = nightly.night_date.min().date(), nightly.night_date.max().date()
picked = st.sidebar.date_input("Nights between", value=DEFAULT_RANGE, min_value=lo, max_value=hi)
start, end = (picked if isinstance(picked, (tuple, list)) and len(picked) == 2 else DEFAULT_RANGE)
st.sidebar.caption("Drives the KPI tiles, calendar, monthly and weekday charts. "
                   "Default is launch (Aug 15) to Dec 31 2026.")
n = nightly[(nightly.night_date.dt.date >= start) & (nightly.night_date.dt.date <= end)].copy()

# ---------- header ----------
st.markdown(f"""
<div class='kz-head'>
  <div>
    <p class='kz-eyebrow'>Revenue analytics · Gainesville, FL · 4 bed / 4 bath</p>
    <h1 class='kz-title'>Why October stalled.</h1>
    <p class='kz-lede'>A townhouse near the University of Florida, launched August 2026. September ran near-full on one
    31-night stay; October and November stalled. This traces why, and where the revenue is recoverable.</p>
  </div>
  <div class='kz-stamp'>Snapshot {meta.snapshot_date}<br>Hospitable API · read-only · anonymized<br>
  Nights {start:%b %d %Y} – {end:%b %d %Y}</div>
</div><hr class='kz-rule'>""", unsafe_allow_html=True)

k = kpis(n)
st.markdown(f"""
<div class='kz-kpis'>
  <div class='kz-kpi'><p class='kz-eyebrow'>Occupancy</p><div class='v'>{k['occupancy']:.1f}%</div>
    <div class='s'>{k['booked']} of {k['nights']} nights booked</div></div>
  <div class='kz-kpi'><p class='kz-eyebrow'>ADR</p><div class='v'>${k['adr']:,.2f}</div>
    <div class='s'>Pre-discount rate per booked night</div></div>
  <div class='kz-kpi'><p class='kz-eyebrow'>Net RevPAR</p><div class='v'>${k['revpar']:,.2f}</div>
    <div class='s'>Net revenue per calendar night</div></div>
  <div class='kz-kpi'><p class='kz-eyebrow'>Net revenue</p><div class='v gold'>${k['net']:,.2f}</div>
    <div class='s'>Payout less cleaning fee and tax</div></div>
</div>""", unsafe_allow_html=True)
st.write("")

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
short_cpn = (short.host_revenue - short.host_taxes - clean_cost).sum() / short.nights.sum()

findings = [
    ("Demand fell off a cliff after September.",
     f"Occupancy went from <span class='fig'>{by_month.get('2026-09', 0):.0f}%</span> in September to "
     f"<span class='fig'>{by_month.get('2026-10', 0):.0f}%</span> in October and "
     f"<span class='fig'>{by_month.get('2026-11', 0):.0f}%</span> in November.", "Calendar · Monthly"),
    ("Weeknights are the hole.",
     f"Sun–Thu nights sold <span class='fig'>{wk.get(0, 0):.0f}%</span> vs "
     f"<span class='fig'>{wk.get(1, 0):.0f}%</span> for Fri/Sat.", "Weekday chart"),
    ("Pricing whipsawed.",
     f"{pd.Timestamp(swing_night):%a %b %d}{swing_event} was listed at <span class='fig'>${tex.list_price.max():.0f}</span> "
     f"and ended at <span class='fig'>${tex.list_price.iloc[-1]:.0f}</span> after {len(tex) - 1} changes; "
     f"now {swing_status}.", "Price history"),
    ("Vrbo lost on availability, not price.",
     f"Vrbo converted <span class='fig'>{int(ch.loc['vrbo', 'confirmed'])} of {int(ch.loc['vrbo', 'requests'])}</span> "
     f"requests; {lost_phrase} lost requests overlapped nights already sold on Airbnb.", "Money leaks · Channels"),
    ("Discounts and long stays dilute yield.",
     f"Discounts gave away <span class='fig'>{disc_total:.1f}%</span> of gross rent. The {int(long_stay.nights)}-night "
     f"stay earned <span class='fig'>${long_stay.contribution_per_night:,.0f}</span>/night after cleaning vs "
     f"<span class='fig'>${short_cpn:,.0f}</span> for 1–2 night stays.", "Money leaks"),
]

# ---------- tab 1 ----------
with tab1:
    st.markdown("<p class='kz-eyebrow' style='margin-top:8px'>Findings</p><div class='kz-find'>" + "".join(
        f"<div class='kz-card'><span class='kz-num'>{i:02d}</span><h4>{t}</h4><p>{b}</p><div class='tag'>{tag}</div></div>"
        for i, (t, b, tag) in enumerate(findings, 1)) + "</div>", unsafe_allow_html=True)
    st.write("")

    # Calendar heatmap: weeks (x) by weekday (y)
    with st.container(border=True):
        section("Calendar", "Every night, by status")
        order = list(STATUS)
        cal = n.assign(code=n.night_status.map(order.index),
                       week=(n.night_date - pd.to_timedelta(n.night_date.dt.weekday, unit="D")),
                       dow=n.night_date.dt.weekday)
        cal["price"] = cal.nightly_rate.fillna(cal.snapshot_price)
        cal["hover"] = (cal.night_date.dt.strftime("%a %b %d %Y") + "<br>" + cal.night_status.map(lambda s: STATUS[s][0])
                        + cal.price.map(lambda p: "" if pd.isna(p) else f"<br>Price ${p:,.0f}")
                        + cal.event.map(lambda e: "" if pd.isna(e) else f"<br>{e}"))
        cal["mark"] = cal.event.map(lambda e: "" if pd.isna(e) else "◆")
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
            zmin=-0.5, zmax=len(order) - 0.5, colorscale=scale, showscale=False, xgap=3, ygap=3,
            text=txt.values, texttemplate="%{text}", textfont=dict(color=IVORY, size=8),
            customdata=hov.values, hovertemplate="%{customdata}<extra></extra>"))
        base_layout(fig, height=290)
        fig.update_yaxes(autorange="reversed", showgrid=False, linecolor="rgba(0,0,0,0)")
        fig.update_xaxes(title_text="WEEK STARTING", tickangle=0, nticks=12, linecolor="rgba(0,0,0,0)")
        show(fig)
        present = [s for s in order if s in set(n.night_status)]
        st.markdown("<div class='kz-legend'>" + "".join(
            f"<span><i style='background:{STATUS[s][1]}'></i>{STATUS[s][0]}</span>" for s in present)
            + "<span>◆ Event night</span></div>", unsafe_allow_html=True)

    left, right = st.columns(2)
    with left, st.container(border=True):
        section("Monthly", "Net revenue vs rent")
        m = n.groupby("year_month").agg(net=("net_rev_ex_cleaning", "sum"),
                                         booked=("night_status", lambda s: (s == "booked").sum()),
                                         nights=("night_status", "size")).reset_index()
        fig = go.Figure(go.Bar(
            x=pd.to_datetime(m.year_month).dt.strftime("%b %Y"), y=m.net,
            marker=dict(color=[GOLD if v >= rent else FAINT for v in m.net], line=dict(width=0)),
            customdata=m[["booked", "nights"]], hovertemplate="%{x}<br>Net $%{y:,.0f}"
            "<br>Booked %{customdata[0]} of %{customdata[1]} nights<extra></extra>"))
        fig.add_hline(y=rent, line_dash="dot", line_color=IVORY, line_width=1,
                      annotation_text=f"RENT ${rent:,.0f}", annotation_position="top right",
                      annotation_font=dict(family=MONO, size=11, color=IVORY))
        base_layout(fig, bargap=0.45)
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
        show(fig)
        st.caption("Gold bars covered rent. Partial months show only nights inside the filter.")

    with right, st.container(border=True):
        section("Day of week", "Fri/Sat vs Sun–Thu")
        w = n.assign(day_type=n.is_weekend.map({1: "Fri/Sat", 0: "Sun–Thu"}))
        g = w.groupby("day_type").agg(
            occ=("night_status", lambda s: 100 * (s == "booked").mean()),
            adr=("nightly_rate", "mean")).reindex(["Fri/Sat", "Sun–Thu"])
        a, b = st.columns(2)
        for col, field, title, fmt in ((a, "occ", "OCCUPANCY", "{:.0f}%"), (b, "adr", "BOOKED ADR", "${:,.0f}")):
            fig = go.Figure(go.Bar(x=g.index, y=g[field], marker=dict(color=[STONE, FAINT], line=dict(width=0)),
                                   text=[fmt.format(v) if pd.notna(v) else "" for v in g[field]],
                                   textposition="outside", textfont=dict(family=MONO, color=IVORY, size=13),
                                   cliponaxis=False, hovertemplate="%{x}: %{text}<extra></extra>"))
            base_layout(fig, height=300, bargap=0.4,
                        title=dict(text=title, font=dict(family=MONO, size=11, color=STONE), x=0, y=0.98))
            fig.update_yaxes(showticklabels=False, showgrid=False, range=[0, (g[field].max() or 1) * 1.25])
            with col:
                show(fig)

    left, right = st.columns(2)
    with left, st.container(border=True):
        section("Pricing", "List-price history, key nights")
        fig = go.Figure()
        ends = []
        for night, grp in pc.groupby("night_date"):
            grp = grp.sort_values("changed_on")
            label = pd.Timestamp(night).strftime("%a %b %d")
            hero = night == swing_night
            fig.add_trace(go.Scatter(
                x=grp.changed_on, y=grp.list_price, mode="lines+markers", line_shape="hv",
                line=dict(width=2, color=IVORY if hero else FAINT),
                marker=dict(size=8, color=IVORY if hero else FAINT, line=dict(color=GRAPHITE, width=2)),
                name=label, customdata=grp.reason,
                hovertemplate=f"{label}<br>%{{x}} · $%{{y:,.0f}}<br>%{{customdata}}<extra></extra>"))
            ends.append((grp.list_price.iloc[-1], grp.changed_on.iloc[-1], label, hero))
        # End labels, nudged apart so lines that finish at similar prices stay readable.
        min_gap = (pc.list_price.max() - pc.list_price.min()) * 0.07
        prev = None
        for price, x, label, hero in sorted(ends, reverse=True):
            y = price if prev is None else min(price, prev - min_gap)
            prev = y
            fig.add_annotation(x=x, y=y, text=f"{label} ${price:,.0f}", xanchor="left", xshift=8, showarrow=False,
                               font=dict(family=MONO, size=10.5, color=IVORY if hero else STONE))
        base_layout(fig, height=360, margin=dict(l=8, r=120, t=24, b=8))
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
        fig.update_xaxes(title_text="DATE CHANGED")
        show(fig)
        st.caption("Highlighted: the night with the largest price swing.")

    with right, st.container(border=True):
        section("Market", "Our price vs comp median, latest pull")
        pm = d["price_vs_market"]
        pm = pm[pm.is_latest_pull == 1].sort_values("stay_start")
        fig = go.Figure(go.Bar(
            y=pm.stay_label + " · " + pm.pulled_on.str[5:], x=pm.gap_pct, orientation="h",
            marker=dict(color=[STONE if v >= 0 else FAINT for v in pm.gap_pct], line=dict(width=0)),
            text=[f"{v:+.1f}%" for v in pm.gap_pct], textposition="outside",
            textfont=dict(family=MONO, color=IVORY, size=11), cliponaxis=False,
            customdata=pm[["our_total", "comp_median", "pulled_on"]],
            hovertemplate="%{y}<br>Ours $%{customdata[0]:,.0f} vs median $%{customdata[1]:,.0f}"
                          "<br>Gap %{x:+.1f}% · pulled %{customdata[2]}<extra></extra>"))
        fig.add_vline(x=0, line_color=IVORY, line_width=1)
        base_layout(fig, height=360, bargap=0.35)
        span = max(abs(pm.gap_pct.min()), abs(pm.gap_pct.max())) * 1.45
        fig.update_xaxes(ticksuffix="%", title_text="GAP VS COMP MEDIAN  (+ = WE ARE PRICIER)", showgrid=True,
                         gridcolor=RULE, range=[-span, span])
        fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(family=SANS, size=11.5, color=STONE))
        show(fig)
        st.caption("Comps are manually pulled list prices, not achieved rates.")

# ---------- tab 2 ----------
with tab2:
    left, right = st.columns(2)
    with left, st.container(border=True):
        section("Discounts", "Leakage as % of gross rent")
        dl = d["discount_leakage"]
        dl = dl[(dl.discount_type != "TOTAL") & (dl.discount_dollars > 0)].sort_values("pct_of_gross_rent")
        fig = go.Figure(go.Bar(
            y=dl.discount_type.str.replace("_", " ").str.capitalize(), x=dl.pct_of_gross_rent, orientation="h",
            marker=dict(color=STONE, line=dict(width=0)), text=[f"{v:.1f}%" for v in dl.pct_of_gross_rent],
            textposition="outside", textfont=dict(family=MONO, color=IVORY, size=12), cliponaxis=False,
            customdata=dl.discount_dollars, hovertemplate="%{y}: %{x:.1f}% · $%{customdata:,.0f}<extra></extra>"))
        base_layout(fig, bargap=0.4)
        fig.update_xaxes(ticksuffix="%", range=[0, dl.pct_of_gross_rent.max() * 1.3])
        fig.update_yaxes(showgrid=False, tickfont=dict(family=SANS, size=12, color=STONE))
        show(fig)
        st.caption(f"Total: {disc_total:.1f}% of pre-discount rent on accepted stays.")

    with right, st.container(border=True):
        section("Stay economics", "Longer stays earn less per night")
        fig = go.Figure(go.Scatter(
            x=acc.nights, y=acc.contribution_per_night, mode="markers",
            marker=dict(size=13, color=GOLD, line=dict(color=GRAPHITE, width=2)),
            customdata=acc[["reservation_id", "platform", "checkin"]],
            hovertemplate="%{customdata[0]} · %{customdata[1]} · in %{customdata[2]}"
                          "<br>%{x} nights · $%{y:,.0f}/night after cleaning<extra></extra>"))
        base_layout(fig)
        fig.update_xaxes(type="log", title_text="NIGHTS (LOG SCALE)", tickvals=[1, 2, 4, 8, 16, 31])
        fig.update_yaxes(tickprefix="$", tickformat=",.0f", title_text="CONTRIBUTION / NIGHT")
        show(fig)
        st.caption(f"Contribution = host payout − pass-through tax − ${clean_cost:,.0f} turnover clean.")

    with st.container(border=True):
        section("Channels", "Vrbo requests were lost to dates already sold on Airbnb")
        left, right = st.columns([2, 3])
        cc = d["channel_comparison"]
        with left:
            fig = go.Figure([
                go.Bar(name="Confirmed", x=cc.platform.str.capitalize(), y=cc.confirmed,
                       marker=dict(color=GOLD, line=dict(width=0)), hovertemplate="%{x}: %{y} confirmed<extra></extra>"),
                go.Bar(name="Lost (declined/expired)", x=cc.platform.str.capitalize(), y=cc.lost,
                       marker=dict(color=STONE, line=dict(width=0)), hovertemplate="%{x}: %{y} lost<extra></extra>"),
                go.Bar(name="Cancelled", x=cc.platform.str.capitalize(), y=cc.cancelled,
                       marker=dict(color=FAINT, line=dict(width=0)), hovertemplate="%{x}: %{y} cancelled<extra></extra>"),
            ])
            base_layout(fig, barmode="group", bargap=0.35, bargroupgap=0.1, showlegend=True,
                        legend=dict(orientation="h", y=1.14, x=0, font=dict(family=MONO, size=11, color=STONE)))
            fig.update_yaxes(title_text="BOOKING REQUESTS", dtick=2)
            show(fig)
        with right:
            st.dataframe(
                cc.rename(columns={"platform": "Channel", "requests": "Requests", "confirmed": "Confirmed",
                                   "lost": "Lost", "cancelled": "Cancelled", "conversion_pct": "Conversion %",
                                   "fee_pct_of_gross": "Fee % of gross", "net_per_night": "Net $/night"}),
                hide_index=True)
            st.markdown("<p class='kz-eyebrow' style='margin-top:10px'>Lost requests vs the stay holding those nights</p>",
                        unsafe_allow_html=True)
            st.dataframe(lost[["lost_request", "platform", "checkin", "checkout", "requested_on",
                               "overlapping_stay", "stay_booked_on"]].rename(columns={
                                   "lost_request": "Lost", "platform": "Channel", "checkin": "Check-in",
                                   "checkout": "Check-out", "requested_on": "Requested",
                                   "overlapping_stay": "Held by", "stay_booked_on": "Held since"}),
                         hide_index=True)
            st.caption("Every lost Vrbo request overlapped an Airbnb stay booked weeks earlier, "
                       "which points to Vrbo availability not being blocked for nights that were already sold.")

st.markdown(f"<hr class='kz-rule'><p class='kz-stamp' style='text-align:left'>Kaizen Corp Housing · "
            f"Python · SQLite · SQL window functions · Streamlit · Plotly · every number traces to sql/analysis/</p>",
            unsafe_allow_html=True)
