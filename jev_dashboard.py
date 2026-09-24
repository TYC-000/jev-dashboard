"""Jev API Usage Dashboard — Streamlit app.

Reads jev_usage.jsonl and renders interactive charts with Plotly.

Deploy on Streamlit Community Cloud:
  https://share.streamlit.io
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"


def resolve_data_path() -> Path:
    """Prefer real usage file, fall back to bundled sample."""
    candidates = [
        DATA_DIR / "jev_usage.jsonl",
        DATA_DIR / "sample_usage.jsonl",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


DATA_PATH = resolve_data_path()

# TypeSafe early-access credit (configurable via Streamlit secrets if you want)
try:
    TOTAL_CREDIT_USD = float(st.secrets.get("TOTAL_CREDIT_USD", 5.0))
except Exception:
    TOTAL_CREDIT_USD = 5.0

# Pricing (per million tokens)
PRICE_PER_M_INPUT = 0.042
PRICE_PER_M_OUTPUT = 0.0  # output is free

# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_entries():
    if not DATA_PATH.exists():
        return pd.DataFrame()
    rows = []
    with open(DATA_PATH) as f:
        for line in f:
            try:
                row = json.loads(line)
                row["ts"] = pd.to_datetime(row["ts"])
                rows.append(row)
            except json.JSONDecodeError:
                continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["cost_usd"] = df["input_tokens"] / 1_000_000 * PRICE_PER_M_INPUT
    df["date"] = df["ts"].dt.date
    return df


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Jev API Dashboard",
    page_icon="💰",
    layout="wide",
)

st.title("💰 Jev API Usage Dashboard")
st.caption("Track every call, every token, every dollar — in real time.")

df = load_entries()

if df.empty:
    st.error("❌ No usage data found. Make sure `data/jev_usage.jsonl` exists.")
    st.stop()

# Sidebar filters
with st.sidebar:
    st.header("📊 Filters")
    window = st.selectbox(
        "Time window",
        ["All time", "Last 7 days", "Last 30 days", "Today"],
        index=0,
    )

    if window == "Today":
        cutoff = pd.Timestamp.now().normalize()
        df = df[df["ts"] >= cutoff]
    elif window == "Last 7 days":
        cutoff = pd.Timestamp.now() - timedelta(days=7)
        df = df[df["ts"] >= cutoff]
    elif window == "Last 30 days":
        cutoff = pd.Timestamp.now() - timedelta(days=30)
        df = df[df["ts"] >= cutoff]

    st.divider()
    st.markdown(f"**Total credit:** ${TOTAL_CREDIT_USD:.2f}")
    st.markdown(f"**Pricing:** ${PRICE_PER_M_INPUT}/M input tokens")
    st.caption(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

if df.empty:
    st.warning("No data in this time window.")
    st.stop()

# ----------------------------------------------------------------------
# KPI cards
# ----------------------------------------------------------------------
total_calls = len(df)
total_tokens = int(df["input_tokens"].sum())
total_cost = df["cost_usd"].sum()
credit_used_pct = total_cost / TOTAL_CREDIT_USD * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("📞 Total calls", f"{total_calls:,}")
col2.metric("🔢 Input tokens", f"{total_tokens:,}")
col3.metric("💵 Total cost", f"${total_cost:.6f}")
col4.metric(
    "💳 Credit used",
    f"{credit_used_pct:.4f}%",
    delta=f"${TOTAL_CREDIT_USD - total_cost:.4f} left",
    delta_color="off",
)

st.divider()

# ----------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📈 Cumulative", "📊 Daily", "🥧 By script", "📉 Tokens"])

with tab1:
    st.subheader("Cumulative cost over time")
    df_sorted = df.sort_values("ts").reset_index(drop=True)
    df_sorted["cum_cost"] = df_sorted["cost_usd"].cumsum()
    df_sorted["cum_calls"] = range(1, len(df_sorted) + 1)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sorted["ts"], y=df_sorted["cum_cost"],
        mode="lines+markers", name="Cumulative cost",
        line=dict(color="#dc2626", width=3),
        fill="tozeroy", fillcolor="rgba(220,38,38,0.15)",
    ))
    fig.add_hline(
        y=TOTAL_CREDIT_USD, line_dash="dot",
        line_color="#9ca3af",
        annotation_text=f"${TOTAL_CREDIT_USD} credit",
        annotation_position="top right",
    )
    fig.update_layout(
        xaxis_title="Time", yaxis_title="Cumulative cost (USD)",
        hovermode="x unified", height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Daily usage breakdown")
    daily = df.groupby("date").agg(
        calls=("ts", "count"),
        cost=("cost_usd", "sum"),
        tokens=("input_tokens", "sum"),
    ).reset_index()
    daily["date"] = pd.to_datetime(daily["date"])

    fig = px.bar(
        daily, x="date", y="calls",
        color="cost", color_continuous_scale="Reds",
        title=f"Calls per day ({len(daily)} active days)",
        labels={"calls": "Number of calls", "date": "Date"},
        height=450,
    )
    fig.update_traces(marker_line_color="white", marker_line_width=1)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        daily.sort_values("date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

with tab3:
    st.subheader("Cost & calls by script")
    by_script = df.groupby("script").agg(
        calls=("ts", "count"),
        cost=("cost_usd", "sum"),
        tokens=("input_tokens", "sum"),
    ).reset_index().sort_values("cost", ascending=False)

    col_a, col_b = st.columns([2, 3])

    with col_a:
        fig = px.pie(
            by_script, values="cost", names="script",
            title="Cost share", hole=0.4, height=400,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.dataframe(
            by_script.style.format({
                "cost": "${:.6f}",
                "tokens": "{:,}",
            }),
            use_container_width=True,
            hide_index=True,
        )

with tab4:
    st.subheader("Input token distribution")
    fig = px.histogram(
        df, x="input_tokens", nbins=20,
        color_discrete_sequence=["#7c3aed"],
        title=f"Distribution of input tokens per call (n={len(df)})",
        height=450,
    )
    mean_tokens = df["input_tokens"].mean()
    median_tokens = df["input_tokens"].median()
    fig.add_vline(x=mean_tokens, line_dash="dash", line_color="#dc2626",
                  annotation_text=f"mean: {mean_tokens:.0f}")
    fig.add_vline(x=median_tokens, line_dash="dot", line_color="#059669",
                  annotation_text=f"median: {median_tokens:.0f}")
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------
# Recent activity
# ----------------------------------------------------------------------
st.divider()
st.subheader("📜 Recent calls")
st.dataframe(
    df.sort_values("ts", ascending=False).head(20)[
        ["ts", "script", "section", "input_tokens", "cost_usd"]
    ].style.format({"cost_usd": "${:.7f}", "input_tokens": "{:,}"}),
    use_container_width=True,
    hide_index=True,
)

# Footer
st.caption(
    "💡 Tip: refresh the page to re-read the log file, or wait 5 minutes "
    "for the cached data to reload."
)
