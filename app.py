"""
OD Process Control Dashboard
==============================
Streamlit + Plotly dashboard for tracking Impeller OD measurements
across 4 manufacturing stages. Data is sourced live from Airtable.

Author  : Auto-generated
Version : 1.0.0
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pyairtable import Api
import numpy as np

# Discrete color palette for WO grouping (20 distinct colors)
WO_PALETTE = px.colors.qualitative.Plotly + px.colors.qualitative.D3

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OD Process Control Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# AIRTABLE CREDENTIALS
# ──────────────────────────────────────────────────────────────────────────────
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID        = "appaEJDKplqKYpCC8"
TABLE_NAME     = "Impeller Database"

# ──────────────────────────────────────────────────────────────────────────────
# COLUMN DEFINITIONS  – map raw Airtable field name → tidy label
# ──────────────────────────────────────────────────────────────────────────────
ID_COLS = {
    "unique ID #"       : "Unique ID",
    "TPU WO name"       : "TPU WO",        # formula field → plain string
    "Assembly WO name"  : "Assembly WO",   # formula field → plain string
}

# Ordered stage tuples: (stage_label, eff_col, hyd_col)
STAGES = [
    ("Frame",    "Effective OD - Frame",           "Hydraulic OD - Frame"),
    ("Mercedes", "OD Effective - After Mercedes",  "Hydraulic OD - After Mercedes"),
    ("Spray",    "Effective OD - After Spray",     "Hydraulic OD - After Spray"),
    ("Final",    "Effective OD - Final",            "Hydraulic OD - Final"),
]
STAGE_ORDER = [s[0] for s in STAGES]

# ──────────────────────────────────────────────────────────────────────────────
# DATA FETCHING & CACHING
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner="📡  Fetching data from Airtable…")
def fetch_airtable_data() -> pd.DataFrame:
    """Pull all records from Airtable and return a tidy wide DataFrame."""
    api   = Api(AIRTABLE_TOKEN)
    table = api.table(BASE_ID, TABLE_NAME)
    records = table.all()

    rows = [r["fields"] for r in records]

    # Helper: flatten list-type cells (Airtable linked records) into comma-separated strings
    def _flatten_cell(val):
        if isinstance(val, list):
            return ", ".join(str(v) for v in val) if val else ""
        return val
    df   = pd.DataFrame(rows)

    # Keep only the columns we actually need (gracefully ignore missing ones)
    needed_ids   = list(ID_COLS.keys())
    needed_stage = [col for _, eff, hyd in STAGES for col in (eff, hyd)]
    keep         = [c for c in needed_ids + needed_stage if c in df.columns]
    df           = df[keep].copy()

    # Rename ID columns to friendlier labels
    df.rename(columns={k: v for k, v in ID_COLS.items() if k in df.columns}, inplace=True)

    # Flatten list-type cells in identifier columns (linked records come back as lists)
    for col in ("Unique ID", "TPU WO", "Assembly WO"):
        if col in df.columns:
            df[col] = df[col].apply(_flatten_cell)
            df[col] = df[col].replace("", pd.NA)   # treat empty string as NaN for filters

    # Coerce measurement columns to numeric (catches strings / blanks)
    for _, eff, hyd in STAGES:
        for col in (eff, hyd):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def melt_to_long(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """
    Reshape the wide DataFrame into long form keyed on Stage.

    Parameters
    ----------
    dimension : "Effective OD" | "Hydraulic OD"
    """
    col_index = 1 if dimension == "Effective OD" else 2   # index in STAGES tuple

    id_vars = [c for c in ("Unique ID", "TPU WO", "Assembly WO") if c in df.columns]
    value_vars = {stage: STAGES[i][col_index] for i, (stage, *_) in enumerate(STAGES)
                  if STAGES[i][col_index] in df.columns}

    long_rows = []
    for _, row in df.iterrows():
        for stage, raw_col in value_vars.items():
            val = row.get(raw_col, np.nan)
            meta = {c: row.get(c, "") for c in id_vars}
            meta["Stage"] = stage
            meta["Value"] = val
            long_rows.append(meta)

    long_df = pd.DataFrame(long_rows)
    # Enforce chronological stage order (categorical)
    long_df["Stage"] = pd.Categorical(long_df["Stage"], categories=STAGE_ORDER, ordered=True)
    return long_df


# ──────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS  – premium, dark-mode-aware styling
# ──────────────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stButton>button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white !important;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    width: 100%;
    padding: 0.55rem 1rem;
    transition: opacity 0.2s;
}
[data-testid="stSidebar"] .stButton>button:hover {
    opacity: 0.85;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 12px;
    padding: 1rem 1.2rem;
}

/* Section headers */
h1 { font-weight: 700; letter-spacing: -0.5px; }
h2 { font-weight: 600; }
h3 { font-weight: 600; color: #818cf8; }

/* Expander */
details summary { font-weight: 600; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 OD Control Dashboard")
    st.markdown("---")

    # --- Reload button (clears cache) ---
    if st.button("🔄 Reload Live Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    # --- Load data (possibly from cache) ---
    try:
        raw_df = fetch_airtable_data()
        data_ok = True
    except Exception as e:
        st.error(f"❌ Airtable error: {e}")
        data_ok = False
        raw_df = pd.DataFrame()

    if data_ok and not raw_df.empty:
        st.success(f"✅ {len(raw_df):,} impellers loaded")

    st.markdown("### 📐 Dimension")
    dimension = st.radio(
        "Select OD Dimension",
        ["Effective OD", "Hydraulic OD"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("### 🔗 Filters")

    # Assembly WO filter
    assy_options = sorted(
        raw_df["Assembly WO"].dropna().unique().tolist()
    ) if data_ok and "Assembly WO" in raw_df.columns else []
    sel_assy = st.multiselect(
        "Assembly WO",
        options=assy_options,
        placeholder="All Assembly WOs",
    )

    # TPU WO filter
    tpu_options = sorted(
        raw_df["TPU WO"].dropna().unique().tolist()
    ) if data_ok and "TPU WO" in raw_df.columns else []
    sel_tpu = st.multiselect(
        "TPU WO",
        options=tpu_options,
        placeholder="All TPU WOs",
    )

    st.markdown("---")
    st.markdown("### 🎨 Appearance")

    dark_mode = st.toggle("🌙 Dark Mode", value=True)

    color_theme = st.selectbox(
        "Box Plot Color Theme",
        ["Indigo / Purple", "Sky Blue", "Emerald Green", "Rose Red", "Amber"],
    )

    st.markdown("---")
    st.markdown("### 🎯 Color Lines By")
    color_by = st.selectbox(
        "Color spaghetti lines by",
        ["None (single color)", "Assembly WO", "TPU WO"],
        label_visibility="collapsed",
    )

    # Merge WOs: visible only when a grouping is active
    merge_wos: list = []
    if color_by != "None (single color)":
        merge_pool = assy_options if color_by == "Assembly WO" else tpu_options
        if merge_pool:
            st.markdown("**🔗 Merge WOs into one group:**")
            merge_wos = st.multiselect(
                "Select WOs to pool together",
                options=merge_pool,
                placeholder="Pick WOs to merge…",
                label_visibility="collapsed",
            )
            if merge_wos:
                st.caption(f"⬡ {len(merge_wos)} WO(s) combined into one box")

    st.markdown("---")
    st.markdown("### 👁️ Chart Layers")
    show_boxes  = st.checkbox("Show Box Plots",     value=True)
    show_lines  = st.checkbox("Show Spaghetti Lines", value=True)
    show_points = st.checkbox("Show Data Points",   value=True)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CONTENT AREA
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("# 🔬 OD Process Control Dashboard")
st.markdown(
    "Track **Impeller Outside Diameter** through each manufacturing stage — "
    "Frame → Mercedes → Spray → Final."
)

if not data_ok or raw_df.empty:
    st.warning("⚠️ No data available. Check the sidebar for errors or reload.")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# APPLY FILTERS
# ──────────────────────────────────────────────────────────────────────────────
filtered_df = raw_df.copy()

if sel_assy:
    filtered_df = filtered_df[filtered_df["Assembly WO"].isin(sel_assy)]
if sel_tpu:
    filtered_df = filtered_df[filtered_df["TPU WO"].isin(sel_tpu)]

if filtered_df.empty:
    st.warning("⚠️ No records match the current filters.")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# MELT DATA TO LONG FORM
# ──────────────────────────────────────────────────────────────────────────────
long_df = melt_to_long(filtered_df, dimension)
# Drop rows where Value is NaN entirely (no measurement at any stage)
valid_ids = long_df.dropna(subset=["Value"])["Unique ID"].unique()
long_df   = long_df[long_df["Unique ID"].isin(valid_ids)]

# ──────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE SELECTION
# ──────────────────────────────────────────────────────────────────────────────
THEME_COLORS = {
    "Indigo / Purple": {"box": "#6366f1", "line_base": "#a5b4fc", "accent": "#818cf8"},
    "Sky Blue":        {"box": "#0ea5e9", "line_base": "#7dd3fc", "accent": "#38bdf8"},
    "Emerald Green":   {"box": "#10b981", "line_base": "#6ee7b7", "accent": "#34d399"},
    "Rose Red":        {"box": "#f43f5e", "line_base": "#fda4af", "accent": "#fb7185"},
    "Amber":           {"box": "#f59e0b", "line_base": "#fcd34d", "accent": "#fbbf24"},
}
theme = THEME_COLORS[color_theme]

box_color  = theme["box"]
line_color = theme["line_base"]
plotly_tpl = "plotly_dark" if dark_mode else "plotly_white"
bg_color   = "#0f172a" if dark_mode else "#ffffff"
paper_bg   = "#1e293b" if dark_mode else "#f8fafc"
font_color = "#e2e8f0" if dark_mode else "#000000"
grid_color = "rgba(148,163,184,0.2)" if dark_mode else "#000000"


# ──────────────────────────────────────────────────────────────────────────────
# METRICS STRIP
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")

# Get first-stage and last-stage averages for the chosen dimension
first_stage = long_df[long_df["Stage"] == STAGE_ORDER[0]]["Value"].dropna()
last_stage  = long_df[long_df["Stage"] == STAGE_ORDER[-1]]["Value"].dropna()
all_values  = long_df["Value"].dropna()

avg_first   = first_stage.mean() if not first_stage.empty else float("nan")
avg_last    = last_stage.mean()  if not last_stage.empty  else float("nan")
shrinkage   = avg_last - avg_first  # negative = OD reduction

# Overall std as proxy for process variance
variance    = all_values.std() if len(all_values) > 1 else float("nan")
n_impellers = filtered_df["Unique ID"].nunique() if "Unique ID" in filtered_df.columns else len(filtered_df)

mc1, mc2, mc3, mc4 = st.columns(4)

with mc1:
    st.metric(
        label=f"📏 Avg OD — **{STAGE_ORDER[0]}**",
        value=f"{avg_first:.4f}" if not np.isnan(avg_first) else "N/A",
    )
with mc2:
    st.metric(
        label=f"📏 Avg OD — **{STAGE_ORDER[-1]}**",
        value=f"{avg_last:.4f}" if not np.isnan(avg_last) else "N/A",
        delta=f"{shrinkage:+.4f} from Frame" if not np.isnan(shrinkage) else None,
        delta_color="inverse",   # OD shrinkage is expected; red = growth (bad)
    )
with mc3:
    st.metric(
        label="📊 Overall Process Std Dev",
        value=f"{variance:.4f}" if not np.isnan(variance) else "N/A",
    )
with mc4:
    st.metric(
        label="🔢 Impellers Shown",
        value=f"{n_impellers:,}",
    )

st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# BUILD PLOTLY FIGURE
# ──────────────────────────────────────────────────────────────────────────────

# Dynamic opacity: reduce line opacity when there are many impellers
n_lines = long_df["Unique ID"].nunique()
line_opacity = 0.15 if n_lines > 100 else (0.25 if n_lines > 50 else 0.55)
point_opacity = min(line_opacity + 0.2, 0.85)

fig = go.Figure()

# ── Resolve grouping column (shared by lines AND boxes) ───────────────────
group_col = None
if color_by == "Assembly WO" and "Assembly WO" in long_df.columns:
    group_col = "Assembly WO"
elif color_by == "TPU WO" and "TPU WO" in long_df.columns:
    group_col = "TPU WO"

# Apply WO merging: remap selected WOs to a single "Merged" label
if group_col and merge_wos:
    long_df = long_df.copy()
    long_df[group_col] = long_df[group_col].apply(
        lambda v: "⬡ Merged" if v in merge_wos else v
    )

if group_col:
    unique_groups = sorted(long_df[group_col].dropna().unique().tolist())
    wo_colormap   = {g: WO_PALETTE[i % len(WO_PALETTE)] for i, g in enumerate(unique_groups)}
else:
    unique_groups = []
    wo_colormap   = {}

# ── 1.  SPAGHETTI LINES  (drawn FIRST → behind boxes) ─────────────────────
if show_lines:
    # Track which WO legend entries have already been added
    legend_added = set()

    for uid, grp in long_df.groupby("Unique ID"):
        grp_sorted = grp.sort_values("Stage")
        grp_valid  = grp_sorted.dropna(subset=["Value"])
        if grp_valid.empty:
            continue

        assy_val = grp_valid["Assembly WO"].iloc[0] if "Assembly WO" in grp_valid.columns else ""
        tpu_val  = grp_valid["TPU WO"].iloc[0]  if "TPU WO"  in grp_valid.columns else ""

        # Choose color & legend group
        if group_col:
            grp_label = grp_valid[group_col].iloc[0] if not grp_valid[group_col].isna().all() else "Unknown"
            trace_color  = wo_colormap.get(grp_label, line_color)
            legend_group = f"wo_{grp_label}"
            show_leg     = grp_label not in legend_added
            leg_name     = str(grp_label)
            if show_leg:
                legend_added.add(grp_label)
        else:
            trace_color  = line_color
            legend_group = "spaghetti"
            show_leg     = False
            leg_name     = str(uid)

        hover_text = [
            f"<b>ID:</b> {uid}<br>"
            f"<b>Assembly WO:</b> {assy_val}<br>"
            f"<b>TPU WO:</b> {tpu_val}<br>"
            f"<b>Stage:</b> {row['Stage']}<br>"
            f"<b>Value:</b> {row['Value']:.4f}"
            for _, row in grp_valid.iterrows()
        ]

        fig.add_trace(go.Scatter(
            x            = grp_valid["Stage"].tolist(),
            y            = grp_valid["Value"].tolist(),
            mode         = "lines",
            line         = dict(color=trace_color, width=1.4),
            opacity      = line_opacity,
            name         = leg_name,
            legendgroup  = legend_group,
            showlegend   = show_leg,
            hovertemplate= "%{text}<extra></extra>",
            text         = hover_text,
            connectgaps  = False,
        ))

# ── 2.  DATA POINTS (SCATTER) ──────────────────────────────────────────────
if show_points:
    pts = long_df.dropna(subset=["Value"])
    hover_parts = (
        "<b>ID:</b> " + pts["Unique ID"].astype(str) + "<br>" +
        ("<b>Assembly WO:</b> " + pts["Assembly WO"].astype(str) + "<br>"
         if "Assembly WO" in pts.columns else "") +
        "<b>Stage:</b> " + pts["Stage"].astype(str) + "<br>" +
        "<b>Value:</b> " + pts["Value"].round(4).astype(str)
    )
    fig.add_trace(go.Scatter(
        x             = pts["Stage"].tolist(),
        y             = pts["Value"].tolist(),
        mode          = "markers",
        marker        = dict(
            color   = line_color,
            size    = 5,
            opacity = point_opacity,
            line    = dict(width=0.5, color=theme["accent"]),
        ),
        name          = "Data Points",
        legendgroup   = "points",
        showlegend    = True,
        hovertemplate = "%{text}<extra></extra>",
        text          = hover_parts.tolist(),
    ))

# ── 3.  BOX PLOTS  (rendered LAST → visually IN FRONT of lines) ──────────
if show_boxes:
    if group_col and unique_groups:
        # Per-WO boxes: one trace per WO → Plotly places side-by-side per stage
        for wo_label in unique_groups:
            wo_data  = long_df[long_df[group_col] == wo_label].dropna(subset=["Value"])
            if wo_data.empty:
                continue
            wo_color = wo_colormap.get(wo_label, box_color)
            fig.add_trace(go.Box(
                y             = wo_data["Value"].tolist(),
                x             = wo_data["Stage"].tolist(),
                name          = str(wo_label),
                marker_color  = wo_color,
                line_color    = "#000000",
                fillcolor     = wo_color,
                opacity       = 1.0,
                boxmean       = True,       # ◆ mean diamond
                legendgroup   = f"wo_{wo_label}",
                showlegend    = True,
                hovertemplate = (
                    f"<b>{wo_label}</b> · %{{x}}<br>"
                    "Median: %{median:.4f}<br>"
                    "Q1: %{q1:.4f} · Q3: %{q3:.4f}<br>"
                    "Min: %{lowerfence:.4f} · Max: %{upperfence:.4f}"
                    "<extra></extra>"
                ),
            ))
    else:
        # No WO grouping — one combined box per stage
        for stage in STAGE_ORDER:
            stage_data = long_df[long_df["Stage"] == stage]["Value"].dropna()
            if stage_data.empty:
                continue
            fig.add_trace(go.Box(
                y             = stage_data.tolist(),
                x             = [stage] * len(stage_data),
                name          = f"Box — {stage}",
                marker_color  = box_color,
                line_color    = "#000000",
                fillcolor     = box_color,
                opacity       = 1.0,
                boxmean       = True,       # ◆ diamond = mean
                legendgroup   = "boxes",
                showlegend    = True,
                hovertemplate = (
                    f"<b>{stage}</b><br>"
                    "Median: %{median:.4f}<br>"
                    "Q1: %{q1:.4f} | Q3: %{q3:.4f}<br>"
                    "Min: %{lowerfence:.4f} | Max: %{upperfence:.4f}"
                    "<extra></extra>"
                ),
            ))

# ── LAYOUT ─────────────────────────────────────────────────────────────────
# boxmode="group" → per-WO boxes sit side-by-side at each stage
# boxmode="overlay" → combined box overlaid on spaghetti lines
active_boxmode = "group" if (show_boxes and group_col and unique_groups) else "overlay"
many_groups    = bool(group_col and len(unique_groups) > 3)
legend_cfg     = dict(
    orientation = "v" if many_groups else "h",
    x           = 1.01 if many_groups else 0,
    y           = 1    if many_groups else -0.15,
    bgcolor     = "rgba(0,0,0,0.0)",
    bordercolor = "rgba(148,163,184,0.2)",
    borderwidth = 1,
)

fig.update_layout(
    template     = plotly_tpl,
    paper_bgcolor= paper_bg,
    plot_bgcolor = bg_color,
    font         = dict(family="Inter, sans-serif", color=font_color, size=13),
    title        = dict(
        text = (
            f"<b>{dimension}</b> — Stage-by-Stage Process Control"
            + (f"  ·  grouped by <i>{color_by}</i>" if group_col else "")
        ),
        font = dict(size=20, color=theme["accent"]),
        x    = 0.02,
    ),
    xaxis = dict(
        title         = "Manufacturing Stage",
        categoryorder = "array",
        categoryarray = STAGE_ORDER,
        showgrid      = True,
        gridcolor     = "rgba(148,163,184,0.2)",
        zeroline      = False,
        layer         = "below traces",
    ),
    yaxis = dict(
        title    = f"{dimension} (mm)",
        showgrid = True,
        gridcolor= grid_color,
        zeroline = False,
        layer    = "below traces",
    ),
    legend    = legend_cfg,
    hovermode = "closest",
    height    = 640,
    margin    = dict(t=80, b=60, l=70, r=180 if many_groups else 30),
    boxmode   = active_boxmode,
)

# Tight y-range padding
all_vals = long_df["Value"].dropna()
if not all_vals.empty:
    y_pad = (all_vals.max() - all_vals.min()) * 0.08 or 0.05
    fig.update_yaxes(range=[all_vals.min() - y_pad, all_vals.max() + y_pad])

# ──────────────────────────────────────────────────────────────────────────────
# RENDER CHART
# ──────────────────────────────────────────────────────────────────────────────
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "scrollZoom": True})

# ──────────────────────────────────────────────────────────────────────────────
# INFO BANNER: opacity hint
# ──────────────────────────────────────────────────────────────────────────────
if n_lines > 50:
    st.info(
        f"💡 **Density mode active**: {n_lines:,} impeller lines detected — "
        f"line opacity reduced to {int(line_opacity*100)}% to show distribution. "
        "Use the filters to zoom in on a subset."
    )

# ──────────────────────────────────────────────────────────────────────────────
# RAW DATA EXPANDER
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("🗄️ View Raw Data Table", expanded=False):
    st.markdown(f"Showing **{len(filtered_df):,}** records after filtering.")
    st.dataframe(
        filtered_df.reset_index(drop=True),
        use_container_width=True,
        height=300,
    )

# ──────────────────────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#64748b; font-size:0.8rem;'>"
    "OD Process Control Dashboard · Data refreshes every 10 min · "
    "Use <b>🔄 Reload Live Data</b> for instant refresh"
    "</p>",
    unsafe_allow_html=True,
)
