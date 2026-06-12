"""
Water Quality IoT Dashboard – Dashboard Page
Complete, production-ready Streamlit page.
Drop this file in your project and call render_dashboard(df) from your main app.
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta



# ──────────────────────────────────────────────────────────
#  THRESHOLDS & SCORING
# ──────────────────────────────────────────────────────────
THRESHOLDS = {
    "pH": {
        "min": 6.5,
        "max": 8.5,
        "unit": "",
        "ideal": (6.8, 8.0)
    },

    "Temperature": {
        "min": 5,
        "max": 35,
        "unit": "°C",
        "ideal": (20, 30)
    },

    "Turbidity": {
        "min": 0,
        "max": 5,
        "unit": "NTU",
        "ideal": (0, 1)
    },

    "TDS": {
        "min": 0,
        "max": 1000,
        "unit": "ppm",
        "ideal": (50, 500)
    },

    # Capteurs pas encore implémentés
    "Conductivity": {
        "min": 0,
        "max": 1400,
        "unit": "µS/cm",
        "ideal": (200, 900)
    },

    "DO": {
        "min": 5,
        "max": 14,
        "unit": "mg/L",
        "ideal": (7, 12)
    }
}

PARAM_ICONS = {
    "pH":           "🧪",
    "Temperature":  "🌡️",
    "Turbidity":    "🌫️",
    "TDS":          "💧",
    "Conductivity": "⚡",
    "DO":           "🫧",
}

PARAM_COLORS = {
    "pH":           "#38bdf8",
    "Temperature":  "#fb923c",
    "Turbidity":    "#a78bfa",
    "TDS":          "#34d399",
    "Conductivity": "#fbbf24",
    "DO":           "#60a5fa",
}


def _param_status(param: str, value: float):
    """Return (label, color, pct_of_range) for a parameter value."""
    t = THRESHOLDS[param]
    ideal_lo, ideal_hi = t["ideal"]
    range_max = t["max"]
    range_min = t["min"]
    pct = max(0, min(1, (value - range_min) / (range_max - range_min))) * 100

    if ideal_lo <= value <= ideal_hi:
        return "Bon", "#22c55e", pct
    elif (value < ideal_lo and value >= t["min"]) or (value > ideal_hi and value <= t["max"]):
        return "Moyen", "#f59e0b", pct
    else:
        return "Mauvais", "#ef4444", pct


def _water_quality_score(row: pd.Series) -> tuple:
    score = 100
    for param, t in THRESHOLDS.items():
        if param not in row:
            continue
        v = row[param]
        if pd.isna(v):
            continue
        lo, hi = t["ideal"]
        if v < t["min"] or v > t["max"]:
            score -= 20
        elif not (lo <= v <= hi):
            score -= 8

    score = max(0, min(100, score))

    if score >= 80:
        return score, "EXCELLENTE", "#22c55e", "🟢"
    elif score >= 55:
        return score, "ACCEPTABLE", "#f59e0b", "🟡"
    else:
        return score, "MAUVAISE", "#ef4444", "🔴"


# ──────────────────────────────────────────────────────────
#  CSS INJECTION
# ──────────────────────────────────────────────────────────
def _inject_css(theme: str = "dark"):
    is_dark = theme == "dark"

    if is_dark:
        text_color = "#ffffff"  
    else:
        text_color = "#111111"
        

    st.markdown(f"""<style>
    /* ── Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');

    /* ── Reset & Base ── */
    html, body, [class*="css"] {{
        font-family: 'DM Sans', sans-serif;
    }}
    .block-container {{
        padding: 1.2rem 1.8rem 2rem !important;
        max-width: 100% !important;
    }}
    .stAppDeployButton, #MainMenu, footer {{ display: none !important; }}
    /* ── Top header bar ── */
    .iot-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 22px;
        margin-bottom: 22px;
        background: linear-gradient(135deg, rgba(14,26,48,0.92) 0%, rgba(8,18,38,0.95) 100%);
        border: 1px solid rgba(56,189,248,0.18);
        border-radius: 16px;
        backdrop-filter: blur(20px);
        box-shadow: 0 0 40px rgba(56,189,248,0.06), inset 0 1px 0 rgba(255,255,255,0.05);
        animation: slideDown 0.6s ease;
    }}
    .iot-header-left {{ display: flex; align-items: center; gap: 14px; }}
    .iot-logo {{
        width: 42px; height: 42px;
        background: linear-gradient(135deg, #0ea5e9, #38bdf8);
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 22px;
        box-shadow: 0 0 20px rgba(56,189,248,0.35);
    }}
    .iot-title {{ font-family: 'Space Mono', monospace; font-size: 17px; font-weight: 700; color: #ffffff; letter-spacing: 0.5px; }}
    .iot-sub   {{ font-size: 11px; color: #64748b; letter-spacing: 1px; text-transform: uppercase; }}
    .iot-header-right {{ display: flex; align-items: center; gap: 18px; }}
    .iot-live-badge {{
        display: flex; align-items: center; gap: 7px;
        background: rgba(34,197,94,0.1);
        border: 1px solid rgba(34,197,94,0.3);
        padding: 6px 14px; border-radius: 30px;
        font-size: 12px; color: #22c55e; font-weight: 600; letter-spacing: 0.5px;
    }}
    .pulse-dot {{
        width: 8px; height: 8px; border-radius: 50%;
        background: #22c55e;
        animation: pulse-green 1.6s infinite;
    }}
    .iot-time {{
        font-family: 'Space Mono', monospace;
        font-size: 12px; color: #64748b;
    }}

    /* ── KPI Cards ── */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
        gap: 14px;
        margin-bottom: 20px;
    }}
    .kpi-card {{
        background: linear-gradient(160deg, rgba(14,26,48,0.9) 0%, rgba(8,16,36,0.95) 100%);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 18px;
        padding: 18px 18px 14px;
        position: relative; overflow: hidden;
        transition: transform 0.22s ease, box-shadow 0.22s ease;
        animation: fadeUp 0.5s ease both;
    }}
    .kpi-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.35);
    }}
    .kpi-card::before {{
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: var(--accent);
        opacity: 0.85;
    }}
    .kpi-card-glow {{
        position: absolute; top: -30px; right: -30px;
        width: 100px; height: 100px; border-radius: 50%;
        background: var(--accent);
        opacity: 0.07; filter: blur(20px);
    }}
    .kpi-icon {{ font-size: 22px; margin-bottom: 6px; }}
    .kpi-label {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}
    .kpi-value {{
        font-family: 'Space Mono', monospace;
        font-size: 32px; font-weight: 700; color: #f8fafc;
        line-height: 1; margin-bottom: 2px;
    }}
    .kpi-unit  {{ font-size: 13px; color: #64748b; }}
    .kpi-status-badge {{
        display: inline-flex; align-items: center; gap: 5px;
        padding: 3px 10px; border-radius: 20px; margin-top: 10px;
        font-size: 11px; font-weight: 600; letter-spacing: 0.4px;
    }}
    .kpi-bar-bg {{
        height: 4px; background: rgba(255,255,255,0.07);
        border-radius: 4px; margin-top: 12px; overflow: hidden;
    }}
    .kpi-bar-fill {{
        height: 100%; border-radius: 4px;
        background: var(--accent);
        box-shadow: 0 0 8px var(--accent);
        transition: width 1s ease;
    }}

    /* ── Score Card ── */
    .score-card {{
        background: linear-gradient(160deg, rgba(14,26,48,0.92) 0%, rgba(8,16,36,0.97) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 22px; padding: 26px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        text-align: center; position: relative; overflow: hidden;
        animation: fadeUp 0.4s ease both;
        min-height: 260px;
    }}
    .score-ring-wrap {{ position: relative; width: 150px; height: 150px; margin-bottom: 16px; }}
    .score-ring-svg  {{ width: 150px; height: 150px; transform: rotate(-90deg); }}
    .score-ring-bg   {{ fill: none; stroke: rgba(255,255,255,0.06); stroke-width: 10; }}
    .score-ring-fg   {{ fill: none; stroke-width: 10; stroke-linecap: round;
                       stroke-dasharray: 408; transition: stroke-dashoffset 1.2s ease; }}
    .score-center {{
        position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
        display: flex; flex-direction: column; align-items: center;
    }}
    .score-num {{
        font-family: 'Space Mono', monospace;
        font-size: 38px; font-weight: 700; line-height: 1;
    }}
    .score-pct {{ font-size: 14px; color: #64748b; }}
    .score-label {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px; }}
    .score-status {{ font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }}

    /* ── Section titles ── */
    .section-title {{
        font-family: 'Space Mono', monospace;
        font-size: 13px; color: #38bdf8; text-transform: uppercase;
        letter-spacing: 2px; margin: 24px 0 14px;
        display: flex; align-items: center; gap: 10px;
        color: {text_color};
    }}
    .section-title::after {{
        content: ''; flex: 1; height: 1px;
        background: linear-gradient(90deg, rgba(56,189,248,0.3), transparent);
    }}

    /* ── Chart container ── */
    .chart-card {{
        background: linear-gradient(160deg, rgba(14,26,48,0.9) 0%, rgba(8,16,36,0.95) 100%);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 18px; padding: 20px;
        margin-bottom: 14px;
        animation: fadeUp 0.6s ease both;
    }}
    .chart-card-title {{
        font-family: 'Space Mono', monospace;
        font-size: 12px; color: #94a3b8;
        text-transform: uppercase; letter-spacing: 1.5px;
        margin-bottom: 14px;
        color: {text_color};
    }}

    /* ── Alert badges ── */
    .alert-row {{
        display: flex; align-items: flex-start; gap: 12px;
        padding: 12px 16px; border-radius: 12px;
        margin-bottom: 10px;
        background: rgba(255,255,255,0.03);
        border-left: 3px solid var(--alert-color);
        font-size: 13px; color: #cbd5e1;
        animation: fadeUp 0.5s ease both;
        color: {text_color}!important;
    }}
    .alert-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--alert-color); margin-top: 4px; flex-shrink: 0; }}

    /* ── Device status table ── */
    .device-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px; margin-top: 4px;
    }}
    .device-item {{
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px; padding: 14px 16px;
        display: flex; align-items: center; gap: 12px;
        transition: border-color 0.2s;
    }}
    .device-item:hover {{ border-color: rgba(56,189,248,0.25); }}
    .device-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
    .device-name {{ font-size: 13px; color: {text_color}; font-weight: 500; }}
    .device-status-text {{ font-size: 11px; color: #64748b; margin-top: 2px; }}

    /* ── Filters bar ── */
    .filters-bar {{
        background: rgba(14,26,48,0.7);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 14px; padding: 14px 18px;
        margin-bottom: 20px;
        display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
    }}

    /* ── Animations ── */
    @keyframes slideDown {{
        from {{ opacity: 0; transform: translateY(-16px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes fadeUp {{
        from {{ opacity: 0; transform: translateY(14px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes pulse-green {{
        0%,100% {{ opacity: 1; box-shadow: 0 0 0 0 rgba(34,197,94,0.5); }}
        50%      {{ opacity: 0.7; box-shadow: 0 0 0 6px rgba(34,197,94,0); }}
    }}
    @keyframes countUp {{
        from {{ opacity: 0; }}
        to   {{ opacity: 1; }}
    }}

    /* ── Altair / Vega overrides ── */
    .vega-embed {{ background: transparent !important; }}
    .vega-embed .marks {{ background: transparent; }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{ width: 5px; }}
    ::-webkit-scrollbar-track {{ background: #050d1a; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(56,189,248,0.25); border-radius: 4px; }}

    /* ── Streamlit widget tweaks ── */
    [data-testid="stSelectbox"] > div,
    [data-testid="stDateInput"] input,
    [data-testid="stSlider"] {{ color: #e2e8f0 !important; }}
    .stSelectbox > div > div {{ background: rgba(14,26,48,0.8) !important; border: 1px solid rgba(255,255,255,0.1) !important; }}
    label {{ color: #94a3b8 !important; font-size: 12px !important; }}
    </style>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  SUB-COMPONENTS
# ──────────────────────────────────────────────────────────

def _render_header(last_update: str):
    st.markdown(f"""
    <div class="iot-header">
        <div class="iot-header-left">
            <div class="iot-logo">💧</div>
            <div>
                <div class="iot-title">AquaMonitor IoT</div>
                <div class="iot-sub">Water Quality Intelligence Platform</div>
            </div>
        </div>
        <div class="iot-header-right">
            <div class="iot-live-badge">
                <div class="pulse-dot"></div>
                REAL-TIME MONITORING
            </div>
            <div class="iot-time">Updated&nbsp; {last_update}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_kpi_card(param: str, value, delay_ms: int = 0):
    icon  = PARAM_ICONS.get(param, "📊")
    color = PARAM_COLORS.get(param, "#38bdf8")
    unit  = THRESHOLDS[param]["unit"]

    if pd.isna(value):
        val_str, label, badge_color, pct = "N/A", "—", "#64748b", 0
    else:
        label, badge_color, pct = _param_status(param, value)
        val_str = f"{value:.1f}" if isinstance(value, float) else str(value)

    badge_bg = badge_color + "1a"
    bar_pct  = f"{pct:.1f}%"

    st.markdown(f"""
    <div class="kpi-card" style="--accent:{color}; animation-delay:{delay_ms}ms;">
        <div class="kpi-card-glow" style="--accent:{color};"></div>
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{param.upper()}</div>
        <div class="kpi-value">{val_str}</div>
        <span class="kpi-unit">{unit}</span>
        <div>
            <span class="kpi-status-badge"
                  style="background:{badge_bg}; color:{badge_color}; border:1px solid {badge_color}40;">
                {"●"}&nbsp;{label}
            </span>
        </div>
        <div class="kpi-bar-bg">
            <div class="kpi-bar-fill" style="width:{bar_pct};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_score_card(score: int, status: str, color: str, emoji: str):
    # SVG ring: circumference = 2π×65 ≈ 408.4
    circum = 408.4
    offset = circum * (1 - score / 100)

    st.markdown(f"""
    <div class="score-card">
        <div class="score-label">Water Quality Score</div>
        <div class="score-ring-wrap">
            <svg class="score-ring-svg" viewBox="0 0 150 150">
                <circle class="score-ring-bg" cx="75" cy="75" r="65"/>
                <circle class="score-ring-fg"
                    cx="75" cy="75" r="65"
                    stroke="{color}"
                    stroke-dashoffset="{offset:.1f}"
                    style="filter: drop-shadow(0 0 6px {color});"
                />
            </svg>
            <div class="score-center">
                <div class="score-num" style="color:{color};">{score}</div>
                <div class="score-pct">/ 100</div>
            </div>
        </div>
        <div class="score-status" style="color:{color};">{emoji}&nbsp;{status}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_alerts(df_latest: pd.Series):
    alerts = []
    rules = [
        ("pH",           lambda v: v < 6.5 or v > 9.2,  "error",   "pH hors normes critiques"),
        ("pH",           lambda v: 6.5 <= v < 6.8 or 8.2 < v <= 9.2, "warning", "pH légèrement hors de la plage idéale"),
        ("Temperature",  lambda v: v > 30,               "error",   "Température trop élevée (>30 °C)"),
        ("Temperature",  lambda v: v > 25,               "warning", "Température légèrement haute (>25 °C)"),
        ("Turbidity",    lambda v: v > 5,                "error",   "Turbidité critique (>5 NTU)"),
        ("Turbidity",    lambda v: 0.5 < v <= 5,         "warning", "Turbidité au-dessus de l'idéal (>0.5 NTU)"),
        ("TDS",          lambda v: v < 50,               "error",   "TDS trop bas (<50 ppm)"),
        ("TDS",          lambda v: v > 300,              "warning", "TDS au-dessus du recommandé (>300 ppm)"),
        ("Conductivity", lambda v: v > 1400,             "error",   "Conductivité trop élevée (>1400 µS/cm)"),
        ("Conductivity", lambda v: v > 900,              "warning", "Conductivité au-dessus du recommandé"),
        ("DO",           lambda v: v < 5,                "error",   "Oxygène dissous critique (<5 mg/L)"),
    ]
    seen = set()
    for param, cond, level, msg in rules:
        val = df_latest.get(param, np.nan)
        if pd.notna(val) and cond(val):
            key = (param, level)
            if key not in seen:
                seen.add(key)
                alerts.append((level, f"{PARAM_ICONS.get(param,'')}  {msg}"))

    if not alerts:
        st.markdown("""
        <div class="alert-row" style="--alert-color:#22c55e; border-left-color:#22c55e;">
            <div class="alert-dot" style="background:#22c55e;"></div>
            ✅&nbsp; Tous les paramètres sont dans les limites normales.
        </div>
        """, unsafe_allow_html=True)
    else:
        for level, msg in alerts:
            color = "#ef4444" if level == "error" else "#f59e0b"
            st.markdown(f"""
            <div class="alert-row" style="--alert-color:{color};">
                <div class="alert-dot" style="background:{color};"></div>
                {msg}
            </div>
            """, unsafe_allow_html=True)


def _altair_line_chart(df: pd.DataFrame, params: list, title: str):
    """Render a styled multi-line Altair chart."""
    if df.empty:
        st.info("Aucune donnée disponible.")
        return

    melt = df[["created_at"] + [p for p in params if p in df.columns]].copy()
    melt = melt.melt("created_at", var_name="Parameter", value_name="Value").dropna()

    color_map = {p: PARAM_COLORS.get(p, "#38bdf8") for p in params}

    selection = alt.selection_point(fields=["Parameter"], bind="legend")

    chart = (
        alt.Chart(melt)
        .mark_line(interpolate="monotone", strokeWidth=2.2)
        .encode(
            x=alt.X("created_at:T", title="", axis=alt.Axis(
                labelColor="#64748b", gridColor="#0f1f3a",
                tickColor="#0f1f3a", format="%H:%M",
            )),
            y=alt.Y("Value:Q", title="", axis=alt.Axis(
                labelColor="#64748b", gridColor="#0f1f3a",
                tickColor="#0f1f3a",
            )),
            color=alt.Color("Parameter:N", scale=alt.Scale(
                domain=list(color_map.keys()),
                range=list(color_map.values()),
            ), legend=alt.Legend(
                orient="top-left",
                labelColor="#94a3b8",
                titleColor="#64748b",
            )),
            opacity=alt.condition(selection, alt.value(1), alt.value(0.15)),
            tooltip=["created_at:T", "Parameter:N", alt.Tooltip("Value:Q", format=".2f")],
        )
        .add_params(selection)
        .properties(height=240, background="transparent", title=alt.Title(""))
        .configure_view(strokeOpacity=0)
        .configure_axis(domainColor="#1e293b")
    )

    st.markdown(f'<div class="chart-card-title">📈 {title}</div>', unsafe_allow_html=True)
    st.altair_chart(chart, width="stretch")


def _render_device_status(df: pd.DataFrame):
    devices = [
        #("🌡️", "Temperature Sensor", "Connected", "Strong",  "#22c55e"),
        #("🧪", "pH Sensor",          "Connected", "Strong",  "#22c55e"),
        #("🌫️", "Turbidity Sensor",   "Connected", "Medium",  "#f59e0b"),
        #("💧", "TDS Sensor",         "Connected", "Strong",  "#22c55e"),
        #("⚡", "Conductivity Sensor","Connected", "Strong",  "#22c55e"),
        #("🫧", "DO Sensor",          "Connected", "Strong",  "#22c55e"),
        #("📡", "Edge Device",        "Online",    "Strong",  "#22c55e"),
    ]
    if (df["temp_sensor"] == True).any():
        devices.append(("🌡️", "Temperature Sensor", "Connected", "Strong",  "#22c55e"))
    else:
        devices.append(("🌡️", "Temperature Sensor", "Disconnected", "—",  "#ef4444"))

    if (df["ph_sensor"] == True).any():
        devices.append(("🧪", "pH Sensor", "Connected", "Strong",  "#22c55e"))
    else:
        devices.append(("🧪", "pH Sensor", "Disconnected", "—",  "#ef4444"))

    if (df["tds_sensor"] == True).any():
        devices.append(("💧", "TDS Sensor", "Connected", "Strong",  "#22c55e"))
    else:
        devices.append(("💧", "TDS Sensor", "Disconnected", "—",  "#ef4444"))

    if (df["turbidity_sensor"] == True).any():
        devices.append(("🌫️", "Turbidity Sensor", "Connected", "Strong",  "#22c55e"))
    else:
        devices.append(("🌫️", "Turbidity Sensor", "Disconnected", "—",  "#ef4444"))

    devices.append(("🫧", "DO Sensor", "Disconnected", "—",  "#ef4444"))
    devices.append(("⚡", "Conductivity Sensor", "Disconnected", "—",  "#ef4444"))
  
    html = '<div class="device-grid">'
    for icon, name, status, signal, color in devices:
        html += f"""
        <div class="device-item">
            <div class="device-dot" style="background:{color}; box-shadow:0 0 6px {color};"></div>
            <div>
                <div class="device-name">{icon} {name}</div>
                <div class="device-status-text">{status} · {signal}</div>
            </div>
        </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ──────────────────────────────────────────────────────────

def render_dashboard(df: pd.DataFrame, theme: str = "dark"):
    """
    Main dashboard renderer.
    Call this function from your main app when the user is logged in
    and has navigated to the Dashboard page.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns: created_at, Temperature, pH, Turbidity,
        TDS, Conductivity, DO
    """

    _inject_css(theme)
    
    df = df.sort_values("created_at", na_position="first", kind="stable").copy()
    latest = df.iloc[-1]
    last_t = latest.get("created_at", pd.NaT)
    last_t = str(last_t) if pd.notna(last_t) else "-"
    # ── Header ──────────────────────────────────────────
    _render_header(last_t)

    # ── Filters bar ─────────────────────────────────────
    st.markdown('<div class="section-title">⚙️ Filtres & Contrôles</div>', unsafe_allow_html=True)
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 1])

    with f_col1:
        sensor_opt = st.selectbox(
            "Capteur actif",
            ["Tous les capteurs", "Capteur A – Zone 1", "Capteur B – Zone 2", "Capteur C – Zone 3"],
            key="dash_sensor",
        )
        
    with f_col2:
        date_from = st.date_input(
        "Date début",
        value=datetime.now().date(),
        key="dash_date_from",
    )

    with f_col3:
        date_to = st.date_input(
        "Date fin",
        value=datetime.now().date(),
        key="dash_date_to",
    )
    with f_col4:
        st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
        apply = st.button("Appliquer", width="stretch", type="primary")

    # Apply date filter
    if not df.empty:
        mask = (df["created_at"].dt.date >= date_from) & (df["created_at"].dt.date <= date_to)
        df_filtered = df[mask].copy()
        if df_filtered.empty:
            df_filtered = df.copy()
    else:
        df_filtered = df.copy()

    # ── Score + KPIs ─────────────────────────────────────
    st.markdown('<div class="section-title">📊 Indicateurs Clés de Performance</div>', unsafe_allow_html=True)
    score_col, kpi_col = st.columns([1, 3])

    with score_col:
        if latest.empty:
            _render_score_card(0, "N/A", "#64748b", "❓")
        else:
            score, status, color, emoji = _water_quality_score(latest)
            _render_score_card(score, status, color, emoji)

    with kpi_col:


        st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1,1])

        with col1:
            val = latest.get("Temperature", np.nan) if not latest.empty else np.nan
            _render_kpi_card("Temperature", val, delay_ms=1 * 80)
        
        with col2:
            val = latest.get("pH", np.nan) if not latest.empty else np.nan
            _render_kpi_card("pH", val, delay_ms=1 * 80)

        with col3:
            val = latest.get("Turbidity", np.nan) if not latest.empty else np.nan
            _render_kpi_card("Turbidity", val, delay_ms=1 * 80)
        
        col1, col2, col3 = st.columns([1, 1,1])

        with col1:
            val = latest.get("TDS", np.nan) if not latest.empty else np.nan
            _render_kpi_card("TDS", val, delay_ms=1 * 80)
        
        with col2:
            val = latest.get("Conductivity", np.nan) if not latest.empty else np.nan
            _render_kpi_card("Conductivity", val, delay_ms=1 * 80)

        with col3:
            val = latest.get("DO", np.nan) if not latest.empty else np.nan
            _render_kpi_card("DO", val, delay_ms=1 * 80)

        st.markdown('</div>', unsafe_allow_html=True)
        
    # ── Charts ───────────────────────────────────────────
    st.markdown('<div class="section-title">📈 Évolution Temporelle</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        _altair_line_chart(df_filtered, ["Temperature", "DO"],       "Température & Oxygène dissous")
    with c2:
        _altair_line_chart(df_filtered, ["pH", "Turbidity"],         "pH & Turbidité")

    c3, c4 = st.columns(2)
    with c3:
        _altair_line_chart(df_filtered, ["TDS", "Conductivity"],     "TDS & Conductivité")
    with c4:
        # Mini stats table
        st.markdown('<div class="chart-card-title">🔬 Statistiques Descriptives</div>', unsafe_allow_html=True)
        if not df_filtered.empty:
            params = ["Temperature", "pH", "Turbidity", "TDS", "Conductivity", "DO"]
            available = [p for p in params if p in df_filtered.columns]
            stats_df = df_filtered[available].agg(["min", "mean", "max"]).round(2).T
            stats_df.columns = ["Min", "Moyenne", "Max"]
            stats_df.index.name = "Paramètre"
            st.dataframe(
                stats_df,
                width="stretch",
                height=235,
            )
        else:
            st.info("Pas de données pour la période sélectionnée.")

    # ── Alerts ───────────────────────────────────────────
    st.markdown('<div class="section-title">⚠️ Alertes & Diagnostics</div>', unsafe_allow_html=True)
    a_col, d_col = st.columns([1, 1])

    with a_col:
        _render_alerts(latest)

    with d_col:
        st.markdown('<div class="section-title" style="margin-top:0;">📡 État des Dispositifs</div>', unsafe_allow_html=True)
        _render_device_status(df)

    # ── Data export ──────────────────────────────────────
    st.markdown('<div class="section-title">💾 Gestion des Données</div>', unsafe_allow_html=True)
    ex_c1, ex_c2, ex_c3 = st.columns([2, 1, 1])
    with ex_c1:
        if not df_filtered.empty:
            csv = df_filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️  Télécharger les données filtrées (CSV)",
                data=csv,
                file_name=f"water_quality_{date_from}_{date_to}.csv",
                mime="text/csv",
                width="stretch",
            )
    with ex_c2:
        st.metric("Enregistrements", len(df_filtered) if not df_filtered.empty else 0)
    with ex_c3:
        period = (date_to - date_from).days
        st.metric("Période", f"{period} jours")

    # ── Footer ───────────────────────────────────────────
    st.markdown("""
    <div style="
        text-align:center; padding:28px 0 10px;
        color:#334155; font-size:12px; letter-spacing:0.5px;
    ">
        AquaMonitor IoT &nbsp;·&nbsp; Developed by <b style="color:#475569">Ourabah Sanaa & ANNABI ADEL</b>
        &nbsp;·&nbsp; Master – Industrial Computer Science &nbsp;·&nbsp; University of Oran 1
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  STANDALONE DEMO (python dashboard_page.py)
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    st.set_page_config(
        page_title="AquaMonitor – Dashboard",
        page_icon="💧",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # ── Generate synthetic demo data ──
    np.random.seed(42)
    n = 120
    now = datetime.now()
    times = [now - timedelta(minutes=5 * i) for i in range(n, 0, -1)]

    demo_df = pd.DataFrame({
        "created_at":  pd.to_datetime(times),
        "Temperature": np.clip(np.random.normal(22, 2, n), 10, 35),
        "pH":          np.clip(np.random.normal(7.2, 0.4, n), 5.5, 9.5),
        "Turbidity":   np.clip(np.abs(np.random.normal(0.8, 0.6, n)), 0, 8),
        "TDS":         np.clip(np.random.normal(180, 40, n), 20, 400),
        "Conductivity":np.clip(np.random.normal(600, 120, n), 100, 1600),
        "DO":          np.clip(np.random.normal(8.5, 1.2, n), 2, 14),
    })

    render_dashboard(demo_df)
