"""
Insurance Semantic Layer — interactive dashboard.

Every number on this page is queried LIVE from the MetricFlow semantic layer
(via `mf query`), not re-derived in the app. That is the whole point: one
governed definition, consumed everywhere. The same metrics an analyst would pull
into Tableau or Looker are what render here.

Run:
    source .venv/bin/activate
    export DBT_PROFILES_DIR=$(pwd)
    streamlit run app/streamlit_app.py
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MF_BIN = shutil.which("mf") or "mf"

# Dimensions a stakeholder can slice by (entity-qualified, per the project conventions).
DIMENSIONS = {
    "Line of business": "policy__line_of_business",
    "State": "policy__state",
}
# The governed KPIs we expose. Ratios are shown as percentages where natural.
COMPONENT_METRICS = ["loss_ratio", "expense_ratio", "combined_ratio"]


# --------------------------------------------------------------------------- #
# MetricFlow query helper
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def mf_query(metrics: tuple[str, ...], group_by: str | None = None) -> pd.DataFrame:
    """Run `mf query` and return the result as a DataFrame. Cached per arg set."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        out_path = tmp.name
    cmd = [MF_BIN, "query", "--metrics", ",".join(metrics), "--csv", out_path]
    if group_by:
        cmd += ["--group-by", group_by]

    env = {**os.environ, "DBT_PROFILES_DIR": str(PROJECT_ROOT)}
    proc = subprocess.run(
        cmd, cwd=str(PROJECT_ROOT), env=env,
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "mf query failed")

    df = pd.read_csv(out_path)
    os.unlink(out_path)
    return df


def fmt_pct(x: float) -> str:
    return f"{x * 100:,.1f}%"


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Insurance Semantic Layer", page_icon="📊", layout="wide")

st.title("📊 Insurance Semantic Layer")
st.caption(
    "Self-serve P&C insurance KPIs. **Every figure below is queried live from the "
    "MetricFlow semantic layer** — one governed definition, reconciled to source "
    "and gated in CI."
)

with st.sidebar:
    st.header("Slice by")
    dim_label = st.radio("Dimension", list(DIMENSIONS.keys()), index=0)
    dim = DIMENSIONS[dim_label]
    st.divider()
    st.markdown(
        "**Combined ratio** = loss ratio + expense ratio.\n\n"
        "Below **100%** = underwriting **profit**; above = underwriting **loss**."
    )
    st.divider()
    st.caption("Source: `mf query` against the dbt + MetricFlow semantic layer.")

# Guard: the warehouse must be built first.
try:
    overall = mf_query(tuple(COMPONENT_METRICS))
except Exception as exc:  # noqa: BLE001
    st.error(
        "Could not query the semantic layer. Build it first:\n\n"
        "```\nsource .venv/bin/activate\nexport DBT_PROFILES_DIR=$(pwd)\n"
        "python scripts/generate_data.py && dbt build\n```\n\n"
        f"Details: `{exc}`"
    )
    st.stop()

# ---- Headline KPI cards (portfolio-wide) ----------------------------------- #
loss = float(overall["loss_ratio"].iloc[0])
expense = float(overall["expense_ratio"].iloc[0])
combined = float(overall["combined_ratio"].iloc[0])

c1, c2, c3 = st.columns(3)
c1.metric("Loss ratio", fmt_pct(loss))
c2.metric("Expense ratio", fmt_pct(expense))
c3.metric(
    "Combined ratio",
    fmt_pct(combined),
    # Points above/below the 100% breakeven line. delta_color="inverse" so below
    # breakeven (an underwriting profit) shows green, above it shows red.
    delta=f"{(combined - 1) * 100:+.1f} pts vs. breakeven",
    delta_color="inverse",
)

st.divider()

# ---- Breakdown by the selected dimension ----------------------------------- #
st.subheader(f"Combined ratio by {dim_label.lower()}")

breakdown = mf_query(tuple(COMPONENT_METRICS), group_by=dim)
breakdown = breakdown.rename(columns={dim: dim_label}).sort_values(
    "combined_ratio", ascending=False
)

left, right = st.columns([3, 2])

with left:
    # Stacked bar: loss + expense components compose the combined ratio.
    chart_df = breakdown.melt(
        id_vars=[dim_label],
        value_vars=["loss_ratio", "expense_ratio"],
        var_name="Component",
        value_name="Ratio",
    )
    chart_df["Component"] = chart_df["Component"].map(
        {"loss_ratio": "Loss ratio", "expense_ratio": "Expense ratio"}
    )
    st.bar_chart(
        chart_df, x=dim_label, y="Ratio", color="Component", height=380,
    )
    st.caption("Bars are stacked: loss ratio + expense ratio = combined ratio.")

with right:
    show = breakdown.copy()
    for col in ["loss_ratio", "expense_ratio", "combined_ratio"]:
        show[col] = show[col].map(fmt_pct)
    show = show.rename(
        columns={
            "loss_ratio": "Loss",
            "expense_ratio": "Expense",
            "combined_ratio": "Combined",
        }
    )
    st.dataframe(show, hide_index=True, use_container_width=True)

st.divider()

# ---- Frequency / severity, same dimension ---------------------------------- #
st.subheader(f"Claim frequency & severity by {dim_label.lower()}")
fs = mf_query(("claim_frequency", "claim_severity"), group_by=dim)
fs = fs.rename(columns={dim: dim_label})
fcol, scol = st.columns(2)
with fcol:
    st.bar_chart(fs, x=dim_label, y="claim_frequency", height=300)
    st.caption("Claims per policy.")
with scol:
    st.bar_chart(fs, x=dim_label, y="claim_severity", height=300)
    st.caption("Average incurred loss per claim ($).")

st.divider()
st.caption(
    "Trusted by design — see `assert_*` reconciliation tests and the CI gate. "
    "Built with dbt + MetricFlow + DuckDB · Snowflake-ready."
)
