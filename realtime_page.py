# ============================================================
#  realtime_page.py  —  AquaMonitor · Real-Time Data Page
#  Style : Scientific IoT Lab · Glassmorphism · Dark/Light
#  Parameters: Temperature, pH, Turbidity, DO, Conductivity, TDS
#  Dependencies : streamlit, plotly, pandas, numpy
# ============================================================

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import random


# ─────────────────────────────────────────────────────────────
#  SECTION 1 :  TIME FILTER
# ─────────────────────────────────────────────────────────────

def filter_by_range(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Filtre le dataframe selon le range temporel sélectionné."""
    now = datetime.now(timezone.utc)
    cutoffs = {
        "1 Heure":   now - timedelta(hours=1),
        "6 Heures":  now - timedelta(hours=6),
        "24 Heures": now - timedelta(hours=24),
        "7 Jours":   now - timedelta(days=7),
    }
    cutoff = cutoffs.get(label, cutoffs["24 Heures"])
    return df[df["Timestamp"] >= cutoff].copy()


# ─────────────────────────────────────────────────────────────
#  SECTION 2 :  THRESHOLDS & STATUS HELPERS
# ─────────────────────────────────────────────────────────────

THRESHOLDS = {
    "Temperature":  {"min": 5,   "max": 30, "ideal": (15,  25), "ok": (15, 25),  "warn": (25, 30),    "crit": (30, 40),    "unit": "°C"},
    "pH":           {"min": 6.5, "max": 8.5, "ideal": (6.5, 8.5), "ok": (6.5, 8.5),  "warn": (6.0, 9.0),  "crit": (5.5, 9.5),  "unit": ""},
    "Turbidity":    {"min": 0,   "max": 5, "ideal": (0, 1), "ok": (0, 5),      "warn": (5, 10),     "crit": (10, 50),    "unit": " NTU"},
    "DO":           {"min": 5,   "max": 14, "ideal": (7,   12), "ok": (6, 12),     "warn": (4, 6),      "crit": (0, 4),      "unit": " mg/L"},
    "Conductivity": {"min": 0,   "max": 1400, "ideal": (200, 900), "ok": (0, 500),    "warn": (500, 1000), "crit": (1000, 2000),"unit": " µS/cm"},
    "TDS":          {"min": 50,  "max": 300,"ideal": (50,  200), "ok": (0, 300),    "warn": (300, 600),  "crit": (600, 1200), "unit": " mg/L"},
}

# Scientific labels and icons for each parameter
PARAM_META = {
    "Temperature":  {"label": "Température",              "symbol": "T",   "icon": "🌡",  "color": "#4FC3F7", "color2": "#0ea5e9"},
    "pH":           {"label": "pH",                        "symbol": "pH",  "icon": "🧪",  "color": "#818cf8", "color2": "#6366f1"},
    "Turbidity":    {"label": "Turbidité",                 "symbol": "NTU", "icon": "🌊",  "color": "#fbbf24", "color2": "#f59e0b"},
    "DO":           {"label": "Oxygène Dissous",           "symbol": "DO",  "icon": "💧",  "color": "#10b981", "color2": "#059669"},
    "Conductivity": {"label": "Conductivité Électrique",   "symbol": "EC",  "icon": "⚡",  "color": "#f59e0b", "color2": "#d97706"},
    "TDS":          {"label": "Solides Dissous Totaux",    "symbol": "TDS", "icon": "🔬",  "color": "#a78bfa", "color2": "#7c3aed"},
}

def get_status(param: str, value: float) -> tuple:
    """Retourne (label, couleur hex, emoji) selon le seuil."""
    thr = THRESHOLDS[param]
    lo_ok, hi_ok     = thr["ok"]
    lo_warn, hi_warn  = thr["warn"]

    # Special logic for DO (lower = worse)
    if param == "DO":
        if value >= lo_ok:
            return "Optimal", "#34d399", "🟢"
        elif value >= lo_warn:
            return "Attention", "#fbbf24", "🟡"
        else:
            return "Critique", "#f87171", "🔴"

    if lo_ok <= value <= hi_ok:
        return "Optimal", "#34d399", "🟢"
    elif lo_warn <= value <= hi_warn:
        return "Attention", "#fbbf24", "🟡"
    else:
        return "Critique", "#f87171", "🔴"

def compute_quality_score(global_score) -> tuple:
    """Calcule le score qualité global pondéré sur tous les paramètres."""
    
    g_color = "#34d399" if global_score >= 80 else "#fbbf24" if global_score >= 50 else "#f87171"
    g_label = "Excellente" if global_score >= 80 else "Acceptable" if global_score >= 50 else "Mauvaise"
    g_emoji = "🏆" if global_score >= 80 else "⚠️" if global_score >= 50 else "🚨"
    return g_color, g_label, g_emoji


# ─────────────────────────────────────────────────────────────
#  SECTION 3 :  CSS INJECTION
# ─────────────────────────────────────────────────────────────

def inject_realtime_css(theme: str = "dark"):
    is_dark = (theme == "dark")

    if is_dark:
        bg_body      = "transparent"
        glass_bg     = "rgba(8, 16, 42, 0.60)"
        glass_border = "rgba(79, 195, 247, 0.20)"
        glass_shine  = "rgba(255,255,255,0.06)"
        text_primary = "#e8f4ff"
        text_muted   = "#6888b0"
        accent       = "#4FC3F7"
        accent_glow  = "rgba(79,195,247,0.30)"
        accent2      = "#818cf8"
        card_shadow  = "0 8px 32px rgba(0,0,0,0.50), 0 1px 0 rgba(255,255,255,0.04) inset"
        metric_bg    = "rgba(12, 24, 60, 0.72)"
        table_bg     = "rgba(8,16,42,0.65)"
        ok_col       = "#34d399"
        warn_col     = "#fbbf24"
        crit_col     = "#f87171"
        chat_bg      = "rgba(8,18,52,0.78)"
        user_bubble  = "rgba(79,195,247,0.18)"
        ai_bubble    = "rgba(129,140,248,0.14)"
        divider      = "rgba(79,195,247,0.12)"
        status_dot   = "#34d399"
        badge_bg     = "rgba(52,211,153,0.12)"
        badge_border = "rgba(52,211,153,0.25)"
        param_pill   = "rgba(79,195,247,0.10)"
    else:
        bg_body      = "transparent"
        glass_bg     = "rgba(255,255,255,0.74)"
        glass_border = "rgba(0,130,230,0.18)"
        glass_shine  = "rgba(255,255,255,0.65)"
        text_primary = "#1a2a4a"
        text_muted   = "#5070a0"
        accent       = "#0077cc"
        accent_glow  = "rgba(0,119,204,0.22)"
        accent2      = "#6366f1"
        card_shadow  = "0 8px 32px rgba(0,80,180,0.10), 0 1px 0 rgba(255,255,255,0.85) inset"
        metric_bg    = "rgba(228,242,255,0.82)"
        table_bg     = "rgba(238,248,255,0.82)"
        ok_col       = "#059669"
        warn_col     = "#d97706"
        crit_col     = "#dc2626"
        chat_bg      = "rgba(232,244,255,0.82)"
        user_bubble  = "rgba(0,119,204,0.11)"
        ai_bubble    = "rgba(99,102,241,0.09)"
        divider      = "rgba(0,119,204,0.10)"
        status_dot   = "#059669"
        badge_bg     = "rgba(5,150,105,0.08)"
        badge_border = "rgba(5,150,105,0.20)"
        param_pill   = "rgba(0,119,204,0.08)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

    /* ── PAGE HEADER ─────────────────────────────────── */
    .rt-page-header {{
        font-family: 'Syne', sans-serif;
        font-size: 2.0rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: {text_primary};
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 4px;
    }}
    .rt-page-subtitle {{
        font-family: 'Inter', sans-serif;
        font-size: 0.80rem;
        color: {text_muted};
        letter-spacing: 0.07em;
        text-transform: uppercase;
        margin-bottom: 22px;
    }}

    /* ── GLASS CARD ──────────────────────────────────── */
    .glass-card {{
        background: {glass_bg};
        border: 1px solid {glass_border};
        border-radius: 18px;
        padding: 22px 26px;
        box-shadow: {card_shadow};
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        position: relative;
        overflow: hidden;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        animation: fadeSlideUp 0.55s ease both;
    }}
    .glass-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, {glass_shine}, transparent);
        pointer-events: none;
    }}
    .glass-card:hover {{
        transform: translateY(-3px);
        box-shadow: {card_shadow}, 0 0 32px {accent_glow};
    }}

    /* ── METRIC CARD ─────────────────────────────────── */
    .metric-card {{
        background: {metric_bg};
        border: 1px solid {glass_border};
        border-radius: 16px;
        padding: 16px 18px 14px;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: {card_shadow};
        animation: fadeSlideUp 0.5s ease both;
        transition: transform 0.22s, box-shadow 0.22s;
        position: relative;
        overflow: hidden;
        min-height: 118px;
    }}
    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, {glass_shine}, transparent);
        pointer-events: none;
    }}
    .metric-card::after {{
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0; height: 2.5px;
        background: var(--card-accent, linear-gradient(90deg, {accent}, {accent2}));
        border-radius: 0 0 16px 16px;
    }}
    .metric-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 14px 44px {accent_glow};
    }}
    .metric-symbol {{
        position: absolute;
        top: 12px; right: 14px;
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: {text_muted};
        background: {param_pill};
        border: 1px solid {glass_border};
        border-radius: 6px;
        padding: 2px 7px;
    }}
    .metric-label {{
        font-family: 'Inter', sans-serif;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.11em;
        text-transform: uppercase;
        color: {text_muted};
        margin-bottom: 7px;
    }}
    .metric-value {{
        font-family: 'Space Mono', monospace;
        font-size: 1.95rem;
        font-weight: 700;
        color: {text_primary};
        line-height: 1;
    }}
    .metric-unit {{
        font-family: 'Space Mono', monospace;
        font-size: 0.80rem;
        color: {text_muted};
        margin-left: 4px;
    }}
    .metric-status {{
        font-family: 'Inter', sans-serif;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        margin-top: 8px;
        display: flex;
        align-items: center;
        gap: 5px;
    }}
    .metric-delta {{
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem;
        color: {text_muted};
        margin-top: 4px;
    }}

    /* ── STATUS PANEL ────────────────────────────────── */
    .status-panel {{
        background: {glass_bg};
        border: 1px solid {glass_border};
        border-radius: 14px;
        padding: 14px 20px;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        display: flex;
        align-items: center;
        gap: 16px;
        animation: fadeSlideUp 0.4s ease both;
    }}
    .status-dot {{
        width: 10px; height: 10px;
        border-radius: 50%;
        background: {status_dot};
        box-shadow: 0 0 8px {status_dot}, 0 0 18px {status_dot}44;
        animation: pulse 2s infinite;
        flex-shrink: 0;
    }}
    .status-dot.error {{
        background: #f87171;
        box-shadow: 0 0 8px #f87171, 0 0 18px #f8717144;
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50%       {{ opacity: 0.55; transform: scale(0.82); }}
    }}
    .status-label {{
        font-family: 'Inter', sans-serif;
        font-size: 0.78rem;
        font-weight: 500;
        color: {text_primary};
    }}
    .status-sub {{
        font-family: 'Space Mono', monospace;
        font-size: 0.67rem;
        color: {text_muted};
        margin-top: 2px;
    }}
    .latency-badge {{
        margin-left: auto;
        font-family: 'Space Mono', monospace;
        font-size: 0.63rem;
        color: {ok_col};
        background: {badge_bg};
        border: 1px solid {badge_border};
        border-radius: 20px;
        padding: 3px 10px;
    }}

    /* ── SECTION TITLE ───────────────────────────────── */
    .section-title {{
        font-family: 'Syne', sans-serif;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: {accent};
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
        margin-top: 8px;
    }}
    .section-title::after {{
        content: '';
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, {divider}, transparent);
    }}

    /* ── PARAMETER LEGEND BAR ────────────────────────── */
    .param-legend {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 14px;
    }}
    .param-pill {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-family: 'Inter', sans-serif;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        padding: 4px 10px;
        border-radius: 20px;
        background: {param_pill};
        border: 1px solid {glass_border};
        color: {text_primary};
    }}
    .param-dot {{
        width: 7px; height: 7px; border-radius: 50%;
        display: inline-block;
    }}

    /* ── AI CHAT ─────────────────────────────────────── */
    .chat-container {{
        background: {chat_bg};
        border: 1px solid {glass_border};
        border-radius: 18px;
        padding: 18px 20px;
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        max-height: 440px;
        overflow-y: auto;
        scroll-behavior: smooth;
        animation: fadeSlideUp 0.6s ease both;
    }}
    .chat-container::-webkit-scrollbar {{ width: 4px; }}
    .chat-container::-webkit-scrollbar-track {{ background: transparent; }}
    .chat-container::-webkit-scrollbar-thumb {{
        background: {glass_border};
        border-radius: 4px;
    }}
    .chat-msg {{
        display: flex;
        gap: 10px;
        margin-bottom: 14px;
        animation: fadeSlideUp 0.3s ease both;
    }}
    .chat-avatar {{
        width: 30px; height: 30px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.85rem;
        flex-shrink: 0;
        margin-top: 2px;
    }}
    .chat-avatar.ai   {{ background: linear-gradient(135deg, {accent}, {accent2}); }}
    .chat-avatar.user {{ background: {'rgba(79,195,247,0.22)' if is_dark else 'rgba(0,119,204,0.14)'}; }}
    .chat-bubble {{
        padding: 10px 14px;
        border-radius: 14px;
        max-width: 88%;
        font-family: 'Inter', sans-serif;
        font-size: 0.79rem;
        line-height: 1.58;
        color: {text_primary};
    }}
    .chat-bubble.ai   {{ background: {ai_bubble}; border: 1px solid {glass_border}; border-radius: 4px 14px 14px 14px; }}
    .chat-bubble.user {{ background: {user_bubble}; border: 1px solid {glass_border}; border-radius: 14px 4px 14px 14px; margin-left: auto; }}
    .chat-time {{
        font-family: 'Space Mono', monospace;
        font-size: 0.58rem;
        color: {text_muted};
        margin-top: 4px;
    }}
    .ai-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-family: 'Inter', sans-serif;
        font-size: 0.67rem;
        font-weight: 600;
        color: {accent};
        letter-spacing: 0.07em;
        margin-bottom: 12px;
    }}
    .ai-badge span {{
        width: 6px; height: 6px; border-radius: 50%;
        background: {accent};
        animation: pulse 1.5s infinite;
    }}

    /* ── DATA TABLE ──────────────────────────────────── */
    .data-table-wrap {{
        background: {table_bg};
        border: 1px solid {glass_border};
        border-radius: 14px;
        overflow: hidden;
        backdrop-filter: blur(14px);
        animation: fadeSlideUp 0.5s ease both;
    }}

    /* ── ANIMATIONS ──────────────────────────────────── */
    @keyframes fadeSlideUp {{
        from {{ opacity: 0; transform: translateY(18px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}

    /* ── PLOTLY OVERRIDE ─────────────────────────────── */
    .js-plotly-plot .plotly .main-svg {{
        border-radius: 12px;
    }}

    /* ── STREAMLIT ELEMENTS ──────────────────────────── */
    .stButton > button {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.04em !important;
        border-radius: 10px !important;
        transition: all 0.22s ease !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 18px {accent_glow} !important;
    }}
    .stSelectbox > div > div {{
        border-radius: 10px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.82rem !important;
    }}
    .stTextInput > div > div > input {{
        border-radius: 10px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.82rem !important;
    }}
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  SECTION 4 :  PLOTLY CHART BUILDERS
# ─────────────────────────────────────────────────────────────

def _plotly_layout(theme: str, title: str, y_label: str) -> dict:
    """Base layout Plotly partagée entre tous les graphes."""
    is_dark = (theme == "dark")
    grid_col  = "rgba(79,195,247,0.07)"  if is_dark else "rgba(0,119,204,0.06)"
    line_col  = "rgba(79,195,247,0.13)"  if is_dark else "rgba(0,119,204,0.10)"
    tick_col  = "#6888b0"               if is_dark else "#5070a0"
    title_col = "#e8f4ff"               if is_dark else "#1a2a4a"
    hover_bg  = "rgba(8,16,42,0.88)"    if is_dark else "rgba(238,248,255,0.95)"
    return dict(
        title=dict(
            text=title,
            font=dict(family="Syne, sans-serif", size=14, color=title_col),
            x=0.02, y=0.97,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor ="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=tick_col, size=11),
        margin=dict(l=52, r=20, t=50, b=48),
        xaxis=dict(
            showgrid=True, gridcolor=grid_col, gridwidth=1,
            zeroline=False,
            tickfont=dict(family="Space Mono, monospace", size=9, color=tick_col),
            showline=True, linecolor=line_col,
        ),
        yaxis=dict(
            title=dict(text=y_label, font=dict(size=10)),
            showgrid=True, gridcolor=grid_col, gridwidth=1,
            zeroline=False,
            tickfont=dict(family="Space Mono, monospace", size=9, color=tick_col),
            showline=True, linecolor=line_col,
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=hover_bg,
            font_family="Space Mono, monospace",
            font_size=11,
            bordercolor="rgba(79,195,247,0.28)",
        ),
        legend=dict(
            orientation="h", x=0.01, y=-0.16,
            font=dict(family="Inter, sans-serif", size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
    )


def _add_threshold_zones(fig, zones: list):
    """Helper : ajoute des zones colorées horizontales."""
    for y0, y1, color, text, pos in zones:
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=color, line_width=0,
            annotation_text=text,
            annotation_position=pos,
            annotation_font_size=9,
            annotation_font_color=color.replace("0.10", "1").replace("0.08", "1").replace("0.07", "1"),
        )


def build_temperature_chart(df: pd.DataFrame, theme: str) -> go.Figure:
    """Graphique Température avec zones de seuils et anomalies."""
    fig = go.Figure()
    _add_threshold_zones(fig, [
        (30, 42, "rgba(248,113,113,0.10)", "⚠ CRITIQUE", "top right"),
        (25, 30, "rgba(251,191,36,0.08)",  "ATTENTION",  "top right"),
        (15, 25, "rgba(52,211,153,0.07)",  "✓ OPTIMAL",  "top right"),
    ])
    fig.add_hline(y=25, line_dash="dot", line_color="rgba(251,191,36,0.45)", line_width=1)
    fig.add_hline(y=30, line_dash="dot", line_color="rgba(248,113,113,0.45)", line_width=1)
    # Fill under
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["Temperature"],
        fill="tozeroy", fillcolor="rgba(79,195,247,0.05)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["Temperature"],
        mode="lines", name="Température",
        line=dict(color="#4FC3F7", width=2.5, shape="spline", smoothing=1.2),
        hovertemplate="<b>%{y:.2f} °C</b><extra>T</extra>",
    ))
    hot = df[df["Temperature"] > 28]
    if not hot.empty:
        fig.add_trace(go.Scatter(
            x=hot["Timestamp"], y=hot["Temperature"], mode="markers",
            marker=dict(color="#f87171", size=7, symbol="circle", line=dict(color="#fff", width=1)),
            name="Anomalie thermique",
            hovertemplate="<b>%{y:.2f} °C</b> — Anomalie<extra></extra>",
        ))
    layout = _plotly_layout(theme, "🌡 Température · T (°C)", "°C")
    layout["yaxis"]["range"] = [10, 44]
    fig.update_layout(**layout)
    return fig


def build_ph_chart(df: pd.DataFrame, theme: str) -> go.Figure:
    """Graphique pH avec bandes de qualité OMS."""
    fig = go.Figure()
    _add_threshold_zones(fig, [
        (5.5, 6.5, "rgba(248,113,113,0.10)", "⚠ Acide",  "top left"),
        (6.5, 8.5, "rgba(52,211,153,0.07)",  "✓ OMS",    "top right"),
        (8.5, 9.5, "rgba(248,113,113,0.10)", "⚠ Alcalin","top right"),
    ])
    fig.add_hline(y=7.0, line_dash="dash", line_color="rgba(129,140,248,0.38)", line_width=1,
                  annotation_text="pH neutre = 7.0", annotation_position="right",
                  annotation_font_size=8, annotation_font_color="#818cf8")
    fig.add_hline(y=6.5, line_dash="dot", line_color="rgba(251,191,36,0.42)", line_width=1)
    fig.add_hline(y=8.5, line_dash="dot", line_color="rgba(251,191,36,0.42)", line_width=1)
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["pH"],
        mode="lines", name="pH",
        line=dict(color="#818cf8", width=2.5, shape="spline", smoothing=1.3),
        hovertemplate="<b>pH %{y:.3f}</b><extra>pH</extra>",
    ))
    layout = _plotly_layout(theme, "🧪 Potentiel Hydrogène · pH", "pH")
    layout["yaxis"]["range"] = [5.0, 10.0]
    fig.update_layout(**layout)
    return fig


def build_turbidity_chart(df: pd.DataFrame, theme: str) -> go.Figure:
    """Graphique Turbidité avec pics critiques marqués."""
    fig = go.Figure()
    turb_max = max(df["Turbidity"].max() * 1.25 + 2, 15)
    _add_threshold_zones(fig, [
        (0,  5,         "rgba(52,211,153,0.07)",  "✓ Clair",   "top right"),
        (5,  10,        "rgba(251,191,36,0.08)",  "⚠ Trouble", "top right"),
        (10, turb_max,  "rgba(248,113,113,0.08)", "⛔ Critique","top right"),
    ])
    fig.add_hline(y=5,  line_dash="dot", line_color="rgba(251,191,36,0.45)", line_width=1)
    fig.add_hline(y=10, line_dash="dot", line_color="rgba(248,113,113,0.45)", line_width=1)
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["Turbidity"],
        fill="tozeroy", fillcolor="rgba(251,191,36,0.05)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["Turbidity"],
        mode="lines", name="Turbidité",
        line=dict(color="#fbbf24", width=2.5, shape="spline", smoothing=1.1),
        hovertemplate="<b>%{y:.2f} NTU</b><extra>Turbidité</extra>",
    ))
    peaks = df[df["Turbidity"] > 10]
    if not peaks.empty:
        fig.add_trace(go.Scatter(
            x=peaks["Timestamp"], y=peaks["Turbidity"], mode="markers",
            marker=dict(color="#f87171", size=8, symbol="triangle-up", line=dict(color="#fff", width=1)),
            name="Pic critique",
            hovertemplate="<b>%{y:.2f} NTU</b> — Pic<extra></extra>",
        ))
    layout = _plotly_layout(theme, "🌊 Turbidité · NTU (Nephelometric)", "NTU")
    layout["yaxis"]["range"] = [-0.5, turb_max]
    fig.update_layout(**layout)
    return fig


def build_do_chart(df: pd.DataFrame, theme: str) -> go.Figure:
    """Graphique Oxygène Dissous avec zones de saturation."""
    fig = go.Figure()
    _add_threshold_zones(fig, [
        (0,  4,  "rgba(248,113,113,0.12)", "⛔ Anoxique",  "top right"),
        (4,  6,  "rgba(251,191,36,0.09)",  "⚠ Hypoxique",  "top right"),
        (6,  14, "rgba(52,211,153,0.07)",  "✓ Saturé",     "top right"),
    ])
    fig.add_hline(y=6.0, line_dash="dot", line_color="rgba(251,191,36,0.45)", line_width=1)
    fig.add_hline(y=4.0, line_dash="dot", line_color="rgba(248,113,113,0.45)", line_width=1)
    fig.add_hline(y=9.0, line_dash="dash", line_color="rgba(16,185,129,0.30)", line_width=1,
                  annotation_text="Saturation typique 20°C", annotation_position="right",
                  annotation_font_size=8, annotation_font_color="#10b981")
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["DO"],
        fill="tozeroy", fillcolor="rgba(16,185,129,0.05)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["DO"],
        mode="lines", name="Oxygène Dissous",
        line=dict(color="#10b981", width=2.5, shape="spline", smoothing=1.2),
        hovertemplate="<b>%{y:.2f} mg/L</b><extra>DO</extra>",
    ))
    low_do = df[df["DO"] < 4]
    if not low_do.empty:
        fig.add_trace(go.Scatter(
            x=low_do["Timestamp"], y=low_do["DO"], mode="markers",
            marker=dict(color="#f87171", size=7, symbol="circle-open", line=dict(color="#f87171", width=2)),
            name="Anoxie critique",
            hovertemplate="<b>%{y:.2f} mg/L</b> — Anoxie<extra></extra>",
        ))
    layout = _plotly_layout(theme, "💧 Oxygène Dissous · DO (mg/L)", "mg/L")
    layout["yaxis"]["range"] = [-0.3, max(df["DO"].max() * 1.2 + 1, 16)]
    fig.update_layout(**layout)
    return fig


def build_conductivity_chart(df: pd.DataFrame, theme: str) -> go.Figure:
    """Graphique Conductivité Électrique avec seuils de salinité."""
    fig = go.Figure()
    cond_max = max(df["Conductivity"].max() * 1.2 + 50, 600)
    _add_threshold_zones(fig, [
        (0,   500,      "rgba(52,211,153,0.07)",  "✓ Eau douce",    "top right"),
        (500, 1000,     "rgba(251,191,36,0.08)",  "⚠ Légèrement",   "top right"),
        (1000, cond_max,"rgba(248,113,113,0.09)", "⛔ Élevée",       "top right"),
    ])
    fig.add_hline(y=500,  line_dash="dot", line_color="rgba(251,191,36,0.42)", line_width=1)
    fig.add_hline(y=1000, line_dash="dot", line_color="rgba(248,113,113,0.42)", line_width=1)
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["Conductivity"],
        fill="tozeroy", fillcolor="rgba(245,158,11,0.05)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["Conductivity"],
        mode="lines", name="Conductivité",
        line=dict(color="#f59e0b", width=2.5, shape="spline", smoothing=1.1),
        hovertemplate="<b>%{y:.1f} µS/cm</b><extra>EC</extra>",
    ))
    layout = _plotly_layout(theme, "⚡ Conductivité Électrique · EC (µS/cm)", "µS/cm")
    layout["yaxis"]["range"] = [-10, cond_max]
    fig.update_layout(**layout)
    return fig


def build_tds_chart(df: pd.DataFrame, theme: str) -> go.Figure:
    """Graphique TDS (Solides Dissous Totaux) avec niveaux de potabilité."""
    fig = go.Figure()
    tds_max = max(df["TDS"].max() * 1.2 + 30, 400)
    _add_threshold_zones(fig, [
        (0,   300,     "rgba(52,211,153,0.07)",  "✓ Potable",     "top right"),
        (300, 600,     "rgba(251,191,36,0.08)",  "⚠ Acceptable",  "top right"),
        (600, tds_max, "rgba(248,113,113,0.09)", "⛔ Non potable", "top right"),
    ])
    fig.add_hline(y=300, line_dash="dot", line_color="rgba(251,191,36,0.42)", line_width=1)
    fig.add_hline(y=600, line_dash="dot", line_color="rgba(248,113,113,0.42)", line_width=1)
    fig.add_hline(y=500, line_dash="dash", line_color="rgba(167,139,250,0.30)", line_width=1,
                  annotation_text="Limite OMS 500 mg/L", annotation_position="right",
                  annotation_font_size=8, annotation_font_color="#a78bfa")
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["TDS"],
        fill="tozeroy", fillcolor="rgba(167,139,250,0.05)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=df["Timestamp"], y=df["TDS"],
        mode="lines", name="TDS",
        line=dict(color="#a78bfa", width=2.5, shape="spline", smoothing=1.2),
        hovertemplate="<b>%{y:.1f} mg/L</b><extra>TDS</extra>",
    ))
    layout = _plotly_layout(theme, "🔬 Solides Dissous Totaux · TDS (mg/L)", "mg/L")
    layout["yaxis"]["range"] = [-5, tds_max]
    fig.update_layout(**layout)
    return fig


def build_combined_overview(df: pd.DataFrame, theme: str) -> go.Figure:
    """Vue combinée 6 paramètres normalisés (0–100 %) pour comparaison."""
    def norm(s, lo, hi):
        return ((s - lo) / (hi - lo) * 100).clip(0, 100)

    df_n = df.copy()
    df_n["Temp_norm"] = norm(df["Temperature"], 15, 40)
    df_n["pH_norm"]   = norm(df["pH"], 5.5, 9.5)
    df_n["Turb_norm"] = norm(df["Turbidity"], 0, 50)
    df_n["DO_norm"]   = norm(df["DO"], 0, 14)
    df_n["Cond_norm"] = norm(df["Conductivity"], 0, 1000)
    df_n["TDS_norm"]  = norm(df["TDS"], 0, 600)

    fig = go.Figure()
    series = [
        ("Temp_norm", "#4FC3F7", "Température (T)"),
        ("pH_norm",   "#818cf8", "pH"),
        ("Turb_norm", "#fbbf24", "Turbidité (NTU)"),
        ("DO_norm",   "#10b981", "DO (mg/L)"),
        ("Cond_norm", "#f59e0b", "EC (µS/cm)"),
        ("TDS_norm",  "#a78bfa", "TDS (mg/L)"),
    ]
    for col, color, name in series:
        fig.add_trace(go.Scatter(
            x=df_n["Timestamp"], y=df_n[col],
            mode="lines", name=name,
            line=dict(color=color, width=2, shape="spline", smoothing=1.2),
            hovertemplate=f"<b>{{y:.1f}} %</b><extra>{name}</extra>",
        ))

    layout = _plotly_layout(theme, "📊 Vue d'ensemble normalisée — 6 paramètres (0–100 %)", "Score (%)")
    layout["yaxis"]["range"] = [-5, 105]
    layout["hovermode"] = "x unified"
    fig.update_layout(**layout)
    return fig

def build_correlation_chart(df: pd.DataFrame, theme: str) -> go.Figure:
    """Graphique corrélation Conductivité vs TDS."""

    is_dark = (theme == "dark")
    color = "#4FC3F7" if is_dark else "#0077cc"

    # =========================
    # Nettoyage des données
    # =========================
    x = pd.to_numeric(df["Conductivity"], errors="coerce")
    y = pd.to_numeric(df["TDS"], errors="coerce")
    temp = pd.to_numeric(df["Temperature"], errors="coerce")

    # Supprimer NaN et inf
    mask = np.isfinite(x) & np.isfinite(y)

    x = x[mask]
    y = y[mask]
    temp = temp[mask]

    # Figure vide par défaut
    fig = go.Figure()

    # =========================
    # Scatter principal
    # =========================
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="markers",
        name="EC vs TDS",
        marker=dict(
            color=temp,
            colorscale="plasma",
            size=6,
            opacity=0.75,
            colorbar=dict(
                title="T (°C)",
                thickness=10,
                len=0.6
            ),
            line=dict(
                width=0.5,
                color="rgba(255,255,255,0.3)"
            ),
        ),
        hovertemplate=(
            "<b>EC: %{x:.1f} µS/cm</b><br>"
            "TDS: %{y:.1f} mg/L<extra></extra>"
        ),
    ))

    # =========================
    # Régression linéaire
    # =========================
    if len(x) >= 2 and np.std(x) > 0 and np.std(y) > 0:

        try:
            m, b = np.polyfit(x, y, 1)

            x_line = np.linspace(x.min(), x.max(), 100)
            y_line = m * x_line + b

            fig.add_trace(go.Scatter(
                x=x_line,
                y=y_line,
                mode="lines",
                name=f"Régression (facteur ≈ {m:.3f})",
                line=dict(
                    color="rgba(167,139,250,0.55)",
                    width=1.5,
                    dash="dot"
                ),
            ))

        except np.linalg.LinAlgError:
            pass

    # =========================
    # Layout
    # =========================
    layout = _plotly_layout(
        theme,
        "🔗 Corrélation EC–TDS (coloré par T°C)",
        "TDS (mg/L)"
    )

    layout["xaxis"]["title"] = dict(
        text="EC (µS/cm)",
        font=dict(size=10)
    )

    layout["hovermode"] = "closest"

    fig.update_layout(**layout)

    return fig

def build_correlation_chart_dev(df: pd.DataFrame, theme: str) -> go.Figure:
    """Graphique corrélation Conductivité vs TDS (relation linéaire attendue)."""
    is_dark = (theme == "dark")
    color = "#4FC3F7" if is_dark else "#0077cc"

    # Regression line
    x = df["Conductivity"].values

    y = df["TDS"].values
    if len(x) > 1:
        m, b = np.polyfit(x, y, 1)
        x_line = np.linspace(x.min(), x.max(), 100)
        y_line = m * x_line + b
    else:
        x_line, y_line = x, y

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line,
        mode="lines", name=f"Régression (R·factor ≈ {m:.3f})",
        line=dict(color="rgba(167,139,250,0.55)", width=1.5, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=df["Conductivity"], y=df["TDS"],
        mode="markers", name="EC vs TDS",
        marker=dict(
            color=df["Temperature"], colorscale="plasma",
            size=6, opacity=0.75,
            colorbar=dict(title="T (°C)", thickness=10, len=0.6),
            line=dict(width=0.5, color="rgba(255,255,255,0.3)"),
        ),
        hovertemplate="<b>EC: %{x:.1f} µS/cm</b><br>TDS: %{y:.1f} mg/L<extra></extra>",
    ))
    layout = _plotly_layout(theme, "🔗 Corrélation EC–TDS (coloré par T°C)", "TDS (mg/L)")
    layout["xaxis"]["title"] = dict(text="EC (µS/cm)", font=dict(size=10))
    layout["hovermode"] = "closest"
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────
#  SECTION 5 :  AI ASSISTANT
# ─────────────────────────────────────────────────────────────

def analyze_data_auto(df: pd.DataFrame) -> list:
    """Analyse automatique complète de tous les paramètres."""
    msgs = []
    if df.empty:
        return ["Aucune donnée disponible pour l'analyse."]

    last   = df.iloc[-1]
    recent = df.tail(12)

    # ── Température ──
    t = float(last["Temperature"])
    if t > 30:
        msgs.append(f"🌡️ **Température critique** — {t:.1f} °C dépasse le seuil de 30 °C. "
                    "Risque de prolifération bactérienne accrue.")
    elif t > 25:
        msgs.append(f"⚠️ **Température élevée** — {t:.1f} °C. Surveillance recommandée.")
    else:
        msgs.append(f"✅ **Température optimale** — {t:.1f} °C dans la plage recommandée (15–25 °C).")

    # ── pH ──
    ph = float(last["pH"])
    if ph < 6.5:
        msgs.append(f"🧪 **pH acide** — {ph:.3f} sous le seuil OMS (6.5). Risque corrosif sur les canalisations.")
    elif ph > 8.5:
        msgs.append(f"🧪 **pH alcalin** — {ph:.3f} dépasse 8.5. Possible contamination ou excès de carbonates.")
    else:
        msgs.append(f"✅ **pH conforme OMS** — {ph:.3f} dans la plage recommandée (6.5–8.5).")

    # ── Turbidité ──
    turb = float(last["Turbidity"])
    if turb > 10:
        msgs.append(f"🌊 **Turbidité critique** — {turb:.2f} NTU dépasse le seuil OMS (10 NTU). "
                    "Filtration urgente recommandée.")
    elif turb > 5:
        msgs.append(f"⚠️ **Turbidité modérée** — {turb:.2f} NTU. Légèrement au-dessus du seuil potable.")
    else:
        msgs.append(f"✅ **Eau claire** — turbidité de {turb:.2f} NTU, excellente clarté optique.")

    # ── Oxygène Dissous ──
    do = float(last["DO"])
    if do < 4:
        msgs.append(f"💧 **Anoxie critique** — OD = {do:.2f} mg/L. Risque majeur pour la faune aquatique. "
                    "Aération immédiate requise.")
    elif do < 6:
        msgs.append(f"⚠️ **Hypoxie** — OD = {do:.2f} mg/L sous le seuil optimal (6 mg/L). "
                    "Conditions de stress pour la vie aquatique.")
    else:
        msgs.append(f"✅ **Oxygène dissous correct** — {do:.2f} mg/L. Bonne oxygénation du milieu aquatique.")

    # ── Conductivité ──
    ec = float(last["Conductivity"])
    if ec > 1000:
        msgs.append(f"⚡ **Conductivité élevée** — EC = {ec:.1f} µS/cm. Minéralisation excessive, "
                    "possible contamination ionique.")
    elif ec > 500:
        msgs.append(f"⚠️ **Conductivité modérée** — EC = {ec:.1f} µS/cm. Surveillance de la minéralisation.")
    else:
        msgs.append(f"✅ **Conductivité normale** — EC = {ec:.1f} µS/cm, eau peu minéralisée.")

    # ── TDS ──
    tds = float(last["TDS"])
    if tds > 600:
        msgs.append(f"🔬 **TDS élevés** — {tds:.1f} mg/L dépasse le seuil OMS (500 mg/L). "
                    "Eau non recommandée pour la consommation directe.")
    elif tds > 300:
        msgs.append(f"⚠️ **TDS modérés** — {tds:.1f} mg/L. Acceptable mais surveiller la minéralisation.")
    else:
        msgs.append(f"✅ **TDS conformes** — {tds:.1f} mg/L. Eau de très bonne qualité physico-chimique.")

    # ── Tendances ──
    temp_trend = recent["Temperature"].diff().mean()
    do_trend   = recent["DO"].diff().mean()
    if abs(temp_trend) > 0.1:
        dir_t = "hausse" if temp_trend > 0 else "baisse"
        msgs.append(f"📈 **Tendance T°** — La température est en **{dir_t}** ({temp_trend:+.3f} °C/mesure).")
    if abs(do_trend) > 0.05:
        dir_d = "baisse" if do_trend < 0 else "hausse"
        msgs.append(f"📉 **Tendance DO** — L'oxygène dissous est en **{dir_d}** ({do_trend:+.3f} mg/L/mesure).")

    turb_std = recent["Turbidity"].std()
    if turb_std > 3:
        msgs.append(f"📊 **Instabilité turbidité** — σ = {turb_std:.1f} NTU. Possible événement hydrique (pluie, ruissellement).")

    return msgs


def get_ai_response(question: str, df: pd.DataFrame) -> str:
    """Réponse contextuelle AI enrichie avec tous les paramètres."""
    if df.empty:
        return "Aucune donnée de capteur disponible pour répondre à votre question."

    last = df.iloc[-1]
    q = question.lower()

    context_full = (
        f"T={float(last['Temperature']):.2f}°C | pH={float(last['pH']):.3f} | "
        f"Turbidité={float(last['Turbidity']):.2f} NTU | "
        f"DO={float(last['DO']):.2f} mg/L | "
        f"EC={float(last['Conductivity']):.1f} µS/cm | "
        f"TDS={float(last['TDS']):.1f} mg/L"
    )

    # ── Température ──
    if any(w in q for w in ["temp", "chaud", "froid", "°c", "thermique"]):
        t = float(last["Temperature"])
        s, col, _ = get_status("Temperature", t)
        trend = df["Temperature"].tail(12).diff().mean()
        dir_t = "↗ hausse" if trend > 0.05 else "↘ baisse" if trend < -0.05 else "→ stable"
        return (f"**Température actuelle : {t:.2f} °C** — statut {s}\n\n"
                f"Tendance : {dir_t} ({trend:+.3f} °C/mesure)\n\n"
                f"La plage optimale OMS est **15–25 °C**. "
                f"{'⚠️ Risque de prolifération bactérienne au-dessus de 30 °C.' if t > 25 else '✅ Valeur dans la norme.'}")

    # ── pH ──
    if any(w in q for w in ["ph", "acide", "alcalin", "neutre", "potentiel hydrogène"]):
        ph = float(last["pH"])
        s, col, _ = get_status("pH", ph)
        acidite = "acide" if ph < 7 else ("neutre" if abs(ph - 7) < 0.2 else "alcalin")
        return (f"**pH actuel : {ph:.3f}** — eau {acidite}, statut {s}\n\n"
                f"Norme OMS : **6.5–8.5**\n\n"
                f"{'⚠️ Un pH acide peut corroder les canalisations métalliques.' if ph < 6.5 else ''}"
                f"{'⚠️ Un pH alcalin peut indiquer contamination aux carbonates.' if ph > 8.5 else ''}"
                f"{'✅ pH dans la plage recommandée pour eau potable.' if 6.5 <= ph <= 8.5 else ''}")

    # ── Turbidité ──
    if any(w in q for w in ["turbid", "trouble", "ntu", "clair", "propre", "optique"]):
        turb = float(last["Turbidity"])
        s, col, _ = get_status("Turbidity", turb)
        return (f"**Turbidité actuelle : {turb:.2f} NTU** — statut {s}\n\n"
                f"Seuils OMS : **< 5 NTU** (potable) | **< 10 NTU** (limite)\n\n"
                f"{'🚨 Filtration urgente recommandée !' if turb > 10 else '⚠️ Qualité marginale, traitement conseillé.' if turb > 5 else '✅ Eau parfaitement claire.'}")

    # ── Oxygène Dissous ──
    if any(w in q for w in ["oxygène", "oxygen", "do", "dissous", "anoxie", "hypoxie", "aération"]):
        do = float(last["DO"])
        s, col, _ = get_status("DO", do)
        saturation_pct = min(do / 9.0 * 100, 100)
        return (f"**Oxygène Dissous : {do:.2f} mg/L** — statut {s}\n\n"
                f"Taux de saturation estimé : **{saturation_pct:.0f} %** (réf. 20°C)\n\n"
                f"Seuils : **> 6 mg/L** optimal | **4–6 mg/L** hypoxie | **< 4 mg/L** anoxie critique\n\n"
                f"{'🚨 Aération immédiate requise ! Risque mortalité piscicole.' if do < 4 else '⚠️ Conditions de stress pour la faune aquatique.' if do < 6 else '✅ Bonne oxygénation du milieu.'}")

    # ── Conductivité ──
    if any(w in q for w in ["conductiv", "ec", "µs", "salinité", "minéralisation", "électrique"]):
        ec = float(last["Conductivity"])
        s, col, _ = get_status("Conductivity", ec)
        tds_est = ec * 0.64
        return (f"**Conductivité Électrique : {ec:.1f} µS/cm** — statut {s}\n\n"
                f"TDS estimé depuis EC : **{tds_est:.0f} mg/L** (facteur 0.64)\n\n"
                f"Seuils : **< 500 µS/cm** (eau douce) | **500–1000** (modéré) | **> 1000** (élevé)\n\n"
                f"La conductivité reflète la concentration ionique totale de l'eau.")

    # ── TDS ──
    if any(w in q for w in ["tds", "solides", "dissous", "minéraux", "total dissolved"]):
        tds = float(last["TDS"])
        s, col, _ = get_status("TDS", tds)
        return (f"**TDS : {tds:.1f} mg/L** — statut {s}\n\n"
                f"Norme OMS : **< 500 mg/L** recommandé\n\n"
                f"Classification :\n"
                f"• < 300 mg/L : Excellente (eau de source)\n"
                f"• 300–600 mg/L : Bonne qualité\n"
                f"• 600–900 mg/L : Acceptable\n"
                f"• > 900 mg/L : Non recommandé\n\n"
                f"Valeur actuelle : **{'✅ Conforme' if tds < 500 else '⚠️ Au-dessus de la recommandation OMS'}**")

    # ── Qualité globale ──
    if any(w in q for w in ["qualité", "potable", "boire", "global", "résumé", "resume", "général"]):
        msgs = analyze_data_auto(df)
        return "**Analyse globale de qualité d'eau (6 paramètres) :**\n\n" + "\n\n".join(msgs)

    # ── Tendances ──
    if any(w in q for w in ["tendance", "évolution", "variation", "trend"]):
        recent = df.tail(24)
        trends = {}
        for p in ["Temperature", "pH", "Turbidity", "DO", "Conductivity", "TDS"]:
            trends[p] = recent[p].diff().mean()
        icons = {p: ("↗" if trends[p] > 0.01 else "↘" if trends[p] < -0.01 else "→") for p in trends}
        return (f"**Tendances récentes (dernières {len(recent)} mesures) :**\n\n"
                f"🌡 Température : {icons['Temperature']} ({trends['Temperature']:+.3f} °C/mesure)\n"
                f"🧪 pH : {icons['pH']} ({trends['pH']:+.4f}/mesure)\n"
                f"🌊 Turbidité : {icons['Turbidity']} ({trends['Turbidity']:+.3f} NTU/mesure)\n"
                f"💧 Oxygène Dissous : {icons['DO']} ({trends['DO']:+.3f} mg/L/mesure)\n"
                f"⚡ Conductivité : {icons['Conductivity']} ({trends['Conductivity']:+.2f} µS/cm/mesure)\n"
                f"🔬 TDS : {icons['TDS']} ({trends['TDS']:+.2f} mg/L/mesure)")

    # ── Normes OMS ──
    if any(w in q for w in ["seuil", "norme", "oms", "who", "limite", "standard"]):
        return (
            "**Normes de référence — OMS / WHO (eau potable) :**\n\n"
            "🌡 **Température** : 15–25 °C optimal, < 30 °C acceptable\n"
            "🧪 **pH** : 6.5–8.5 recommandé (neutre = 7.0)\n"
            "🌊 **Turbidité** : < 5 NTU idéal, < 10 NTU limite critique\n"
            "💧 **DO** : > 6 mg/L optimal, < 4 mg/L anoxie critique\n"
            "⚡ **Conductivité** : < 500 µS/cm (eau douce), < 1000 acceptable\n"
            "🔬 **TDS** : < 500 mg/L recommandé (OMS), < 1000 limite\n\n"
            "_Source : WHO Guidelines for Drinking-water Quality, 4ème édition_"
        )

    # ── Corrélation EC/TDS ──
    if any(w in q for w in ["corrélation", "relation", "lien", "ec tds", "tds ec"]):
        corr = df["Conductivity"].corr(df["TDS"])
        return (f"**Corrélation EC ↔ TDS :**\n\n"
                f"Coefficient de corrélation de Pearson : **r = {corr:.3f}**\n\n"
                f"La relation EC–TDS est généralement linéaire avec un facteur de conversion "
                f"de **0.5 à 0.7** selon la composition ionique. "
                f"{'✅ Très forte corrélation — données cohérentes.' if abs(corr) > 0.9 else '⚠️ Corrélation modérée — composition ionique variable.'}")

    # ── Réponse générique ──
    return (f"**Données capteur actuelles :**\n\n"
            f"{context_full}\n\n"
            f"Posez-moi des questions sur la **température**, le **pH**, la **turbidité**, "
            f"l'**oxygène dissous (DO)**, la **conductivité (EC)**, les **TDS**, "
            f"les **tendances**, les **normes OMS** ou la **qualité globale**. 💬")


# ─────────────────────────────────────────────────────────────
#  SECTION 6 :  METRIC CARD BUILDER
# ─────────────────────────────────────────────────────────────

def metric_card_html(label: str, symbol: str, value, unit: str,
                     status_label: str, status_color: str, status_emoji: str,
                     delta: str, accent_color: str = "#4FC3F7",
                     accent_color2: str = "#818cf8") -> str:
    delta_arrow = "▲" if delta.startswith("Δ +") or "+" in delta else "▼" if "-" in delta else "·"
    delta_col   = "#34d399" if "+" in delta else "#f87171" if "-" in delta else "#7090b8"
    return f"""
    <div class="metric-card" style="--card-accent: linear-gradient(90deg, {accent_color}, {accent_color2});">
        <div class="metric-symbol">{symbol}</div>
        <div class="metric-label">{label}</div>
        <div style="display:flex; align-items:baseline; gap:4px; margin-top:2px;">
            <span class="metric-value">{value}</span>
            <span class="metric-unit">{unit}</span>
        </div>
        <div class="metric-status" style="color:{status_color}">
            {status_emoji}&nbsp;{status_label}
        </div>
        <div class="metric-delta" style="color:{delta_col}">{delta_arrow} {delta}</div>
    </div>
    """


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
        return score
    elif score >= 55:
        return score
    else:
        return score
    
# ─────────────────────────────────────────────────────────────
#  SECTION 7 :  MAIN RENDER FUNCTION
# ─────────────────────────────────────────────────────────────

def render_realtime(df_real, theme: str = "dark"):
    """
    Point d'entrée principal.
    df_real : DataFrame du capteur réel (doit contenir les colonnes :
              Timestamp/created_at, Temperature, pH, Conductivity, TDS, DO, Turbidity)
    """
    is_dark = (theme == "dark")

    print(f"df_real: {len(df_real)}")
    df = df_real.sort_values("created_at").copy()
    latest = df_real.iloc[-1]
    last_t = latest.get("created_at", pd.NaT)
    last_t = last_t.strftime("%H:%M:%S") if pd.notna(last_t) else "—"

    # ── Init session state ────────────────────────────────
    for key, default in [
        ("rt_sensor",     "ESP32-A1"),
        ("rt_time_range", "24 Heures"),
        ("rt_chat",       []),
        ("rt_sim_data",   {}),
        ("rt_refresh_ts", datetime.now()),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ── Inject CSS ────────────────────────────────────────
    inject_realtime_css(theme)

    # ── PAGE HEADER ───────────────────────────────────────
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.markdown("""
        <div class="rt-page-header">
            🌊 AquaMonitor
            <span style="font-size:0.85rem; font-weight:400; opacity:0.55;">· Real-Time</span>
        </div>
        <div class="rt-page-subtitle">
            Live sensor feed &nbsp;·&nbsp; 6-parameter environmental quality analysis &nbsp;·&nbsp; ESP32 / ThingSpeak
        </div>
        """, unsafe_allow_html=True)
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.rt_sim_data  = {}
            st.session_state.rt_refresh_ts = datetime.now()
            st.rerun()

    # ── CONTROLS ROW ──────────────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 3])
    with ctrl1:
        sensor_id = st.selectbox(
            "📌 Capteur",
            ["ESP32-A1", "ESP32-A2", "ESP32-B1", "ESP32-B2"],
            index=["ESP32-A1","ESP32-A2","ESP32-B1","ESP32-B2"].index(
                st.session_state.rt_sensor),
            key="rt_sensor_sel",
        )
        st.session_state.rt_sensor = sensor_id

    with ctrl2:
        time_label = st.selectbox(
            "⏱ Période",
            ["1 Heure", "6 Heures", "24 Heures", "7 Jours"],
            index=["1 Heure","6 Heures","24 Heures","7 Jours"].index(
                st.session_state.rt_time_range),
            key="rt_time_sel",
        )
        st.session_state.rt_time_range = time_label

    with ctrl3:
        ts = st.session_state.rt_refresh_ts
        latency_ms = random.randint(42, 180)
        dot_cls = "status-dot"
        st.markdown(f"""
        <div class="status-panel" style="margin-top:4px; height:62px;">
            <div class="{dot_cls}"></div>
            <div>
                <div class="status-label">🟢 Connecté — Firebase</div>
                <div class="status-sub">{sensor_id} · Dernière synchro {ts.strftime('%H:%M:%S')}</div>
            </div>
            <div class="latency-badge">⚡ {latency_ms} ms</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── DATA PREPARATION ──────────────────────────────────
    raw_df = df_real.copy()
    if "created_at" in raw_df.columns:
        raw_df = raw_df.rename(columns={"created_at": "Timestamp"})

    required_cols = ["Timestamp", "Temperature", "pH", "Conductivity", "TDS", "DO", "Turbidity"]
    missing = [c for c in required_cols if c not in raw_df.columns]
    if missing:
        st.error(f"❌ Colonnes manquantes dans le DataFrame : {missing}")
        return

    raw_df = raw_df[required_cols].dropna()

    # Ensure Timestamp is timezone-aware UTC
    if raw_df["Timestamp"].dt.tz is None:
        raw_df["Timestamp"] = raw_df["Timestamp"].dt.tz_localize("UTC")
    else:
        raw_df["Timestamp"] = raw_df["Timestamp"].dt.tz_convert("UTC")

    df = filter_by_range(raw_df, time_label)
    print(f"df: {len(df)}")

    if df.empty:
        st.warning("⚠️ Aucune donnée disponible pour cette plage temporelle.")
        return

    # ── EXTRACT LATEST VALUES ─────────────────────────────
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2] if len(df) > 1 else last_row

    vals = {p: round(float(last_row[p]), 3) for p in ["Temperature","pH","Turbidity","DO","Conductivity","TDS"]}
    prev = {p: round(float(prev_row[p]), 3) for p in vals}
    deltas = {p: vals[p] - prev[p] for p in vals}
    statuses = {p: get_status(p, vals[p]) for p in vals}

    # ── LIVE METRIC CARDS ─────────────────────────────────
    st.markdown('<div class="section-title">⚡ Valeurs en Direct</div>', unsafe_allow_html=True)

    # Row 1 : T, pH, Turbidity, Quality Score
    m1, m2, m3, m4 = st.columns(4)
    params_row1 = [
        ("Temperature", "T",   f"{vals['Temperature']:.2f}", "°C",     f"Δ {deltas['Temperature']:+.2f} °C"),
        ("pH",          "pH",  f"{vals['pH']:.3f}",          "",        f"Δ {deltas['pH']:+.4f}"),
        ("Turbidity",   "NTU", f"{vals['Turbidity']:.2f}",   "NTU",    f"Δ {deltas['Turbidity']:+.2f} NTU"),
    ]
    for col, (param, sym, v, unit, delta) in zip([m1, m2, m3], params_row1):
        s, c, e = statuses[param]
        meta    = PARAM_META[param]
        with col:
            st.markdown(metric_card_html(
                meta["label"], sym, v, unit, s, c, e, delta,
                meta["color"], meta["color2"]
            ), unsafe_allow_html=True)

    score = _water_quality_score(latest)

    # Global quality score (4th card)
    g_color, g_label, g_emoji = compute_quality_score(score)
    with m4:
        st.markdown(metric_card_html(
            f"Score Qualité: {score}", "IQE", score, "%", g_label, g_color, g_emoji,
            f"Basé sur {len(df)} mesures · 6 paramètres",
            g_color, "#818cf8"
        ), unsafe_allow_html=True)

    # Row 2 : DO, EC, TDS
    m5, m6, m7 = st.columns(3)
    params_row2 = [
        ("DO",           "DO",  f"{vals['DO']:.2f}",          "mg/L",    f"Δ {deltas['DO']:+.2f} mg/L"),
        ("Conductivity", "EC",  f"{vals['Conductivity']:.1f}", "µS/cm",   f"Δ {deltas['Conductivity']:+.1f} µS/cm"),
        ("TDS",          "TDS", f"{vals['TDS']:.1f}",          "mg/L",    f"Δ {deltas['TDS']:+.1f} mg/L"),
    ]
    for col, (param, sym, v, unit, delta) in zip([m5, m6, m7], params_row2):
        s, c, e = statuses[param]
        meta    = PARAM_META[param]
        with col:
            st.markdown(metric_card_html(
                meta["label"], sym, v, unit, s, c, e, delta,
                meta["color"], meta["color2"]
            ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PARAMETER LEGEND BAR ──────────────────────────────
    legend_html = '<div class="param-legend">'
    for param, meta in PARAM_META.items():
        s, c, e = statuses[param]
        legend_html += (
            f'<div class="param-pill">'
            f'<span class="param-dot" style="background:{meta["color"]}"></span>'
            f'{meta["icon"]} {meta["symbol"]} — <b style="color:{c}">{s}</b>'
            f'</div>'
        )
    legend_html += '</div>'
    st.markdown(legend_html, unsafe_allow_html=True)

    # ── CHARTS ROW 1 : Temperature + pH ───────────────────
    st.markdown('<div class="section-title">📈 Séries Temporelles</div>', unsafe_allow_html=True)

    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown('<div class="glass-card" style="padding:12px">', unsafe_allow_html=True)
        st.plotly_chart(build_temperature_chart(df, theme), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    with ch2:
        st.markdown('<div class="glass-card" style="padding:12px">', unsafe_allow_html=True)
        st.plotly_chart(build_ph_chart(df, theme), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── CHARTS ROW 2 : Turbidity + DO ─────────────────────
    ch3, ch4 = st.columns(2)
    with ch3:
        st.markdown('<div class="glass-card" style="padding:12px">', unsafe_allow_html=True)
        st.plotly_chart(build_turbidity_chart(df, theme), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    with ch4:
        st.markdown('<div class="glass-card" style="padding:12px">', unsafe_allow_html=True)
        st.plotly_chart(build_do_chart(df, theme), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── CHARTS ROW 3 : Conductivity + TDS ─────────────────
    ch5, ch6 = st.columns(2)
    with ch5:
        st.markdown('<div class="glass-card" style="padding:12px">', unsafe_allow_html=True)
        st.plotly_chart(build_conductivity_chart(df, theme), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    with ch6:
        st.markdown('<div class="glass-card" style="padding:12px">', unsafe_allow_html=True)
        st.plotly_chart(build_tds_chart(df, theme), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── CHARTS ROW 4 : Overview + Correlation ─────────────
    ch7, ch8 = st.columns(2)
    with ch7:
        st.markdown('<div class="glass-card" style="padding:12px">', unsafe_allow_html=True)
        st.plotly_chart(build_combined_overview(df, theme), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    with ch8:
        st.markdown('<div class="glass-card" style="padding:12px">', unsafe_allow_html=True)
        st.plotly_chart(build_correlation_chart(df, theme), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI ASSISTANT + DATA TABLE ─────────────────────────
    # left_col, right_col = st.columns([1, 1])

    # ── AI ASSISTANT ──────────────────────────────────────
    # with left_col:
    #     st.markdown('<div class="section-title">🤖 Assistant IA AquaMonitor</div>',
    #                 unsafe_allow_html=True)

    #     if not st.session_state.rt_chat:
    #         auto_msgs = analyze_data_auto(df)
    #         st.session_state.rt_chat = [
    #             {"role": "ai", "content":
    #                 "👋 Bonjour ! Je suis **AquaAI**, votre assistant d'analyse de qualité d'eau. "
    #                 "Voici mon rapport automatique sur les **6 paramètres** mesurés :"},
    #         ]
    #         for m in auto_msgs:
    #             st.session_state.rt_chat.append({"role": "ai", "content": m})
    #         st.session_state.rt_chat.append({
    #             "role": "ai",
    #             "content": "💬 Posez-moi une question sur la **température**, le **pH**, la **turbidité**, "
    #                        "l'**oxygène dissous (DO)**, la **conductivité (EC)**, les **TDS**, "
    #                        "ou demandez un **résumé global** ou les **normes OMS**."
    #         })

    #     # Render chat
    #     chat_html = '<div class="chat-container" id="chat-box">'
    #     chat_html += '<div class="ai-badge"><span></span> AquaAI · En ligne · 6 paramètres actifs</div>'
    #     for msg in st.session_state.rt_chat[-20:]:
    #         t_str = datetime.now().strftime("%H:%M")
    #         if msg["role"] == "ai":
    #             chat_html += f"""
    #             <div class="chat-msg">
    #                 <div class="chat-avatar ai">🤖</div>
    #                 <div>
    #                     <div class="chat-bubble ai">{msg['content']}</div>
    #                     <div class="chat-time">{t_str} · AquaAI</div>
    #                 </div>
    #             </div>"""
    #         else:
    #             chat_html += f"""
    #             <div class="chat-msg" style="flex-direction:row-reverse">
    #                 <div class="chat-avatar user">👤</div>
    #                 <div style="text-align:right">
    #                     <div class="chat-bubble user">{msg['content']}</div>
    #                     <div class="chat-time">{t_str} · Vous</div>
    #                 </div>
    #             </div>"""
    #     chat_html += '</div>'
    #     st.markdown(chat_html, unsafe_allow_html=True)

    #     # Input
    #     q_col, send_col = st.columns([5, 1])
    #     with q_col:
    #         user_question = st.text_input(
    #             "Message",
    #             placeholder="Ex: Quel est le DO ? Les TDS sont-ils conformes OMS ?",
    #             label_visibility="collapsed",
    #             key="rt_chat_input",
    #         )
    #     with send_col:
    #         send = st.button("➤", use_container_width=True, key="rt_send")

    #     if send and user_question.strip():
    #         st.session_state.rt_chat.append({"role": "user", "content": user_question.strip()})
    #         with st.spinner("AquaAI analyse..."):
    #             response = get_ai_response(user_question.strip(), df)
    #         st.session_state.rt_chat.append({"role": "ai", "content": response})
    #         st.rerun()

    #     # Quick questions
    #     st.markdown("**Questions rapides :**")
    #     qb1, qb2, qb3 = st.columns(3)
    #     qb4, qb5, qb6 = st.columns(3)
    #     quick_questions = [
    #         ("🧪 pH",          "Quel est le pH actuel ?"),
    #         ("💧 DO",          "L'oxygène dissous est-il correct ?"),
    #         ("🔬 TDS",         "Les TDS sont-ils conformes à l'OMS ?"),
    #         ("⚡ Conductivité", "Quelle est la conductivité électrique ?"),
    #         ("📈 Tendances",    "Montre-moi les tendances de tous les paramètres"),
    #         ("📊 Résumé",       "Donne-moi un résumé global de la qualité"),
    #     ]
    #     for (label, question), col in zip(quick_questions, [qb1, qb2, qb3, qb4, qb5, qb6]):
    #         with col:
    #             if st.button(label, use_container_width=True, key=f"quick_{label}"):
    #                 st.session_state.rt_chat.append({"role": "user", "content": question})
    #                 response = get_ai_response(question, df)
    #                 st.session_state.rt_chat.append({"role": "ai", "content": response})
    #                 st.rerun()

    #     if st.button("🗑 Effacer le chat", key="clear_chat"):
    #         st.session_state.rt_chat = []
    #         st.rerun()

    # # ── DATA TABLE ────────────────────────────────────────
    # with right_col:
    st.markdown('<div class="section-title">📋 Données Statistiques</div>',
                unsafe_allow_html=True)

    # Résumé statistique 6 paramètres
    stat_data = {
        "Paramètre": [
            f"{PARAM_META['Temperature']['icon']} Température",
            f"{PARAM_META['pH']['icon']} pH",
            f"{PARAM_META['Turbidity']['icon']} Turbidité",
            f"{PARAM_META['DO']['icon']} DO",
            f"{PARAM_META['Conductivity']['icon']} Conductivité",
            f"{PARAM_META['TDS']['icon']} TDS",
        ],
        "Actuelle": [
            f"{vals['Temperature']:.2f} °C",
            f"{vals['pH']:.3f}",
            f"{vals['Turbidity']:.2f} NTU",
            f"{vals['DO']:.2f} mg/L",
            f"{vals['Conductivity']:.1f} µS/cm",
            f"{vals['TDS']:.1f} mg/L",
        ],
        "Moyenne": [
            f"{df['Temperature'].mean():.2f} °C",
            f"{df['pH'].mean():.3f}",
            f"{df['Turbidity'].mean():.2f} NTU",
            f"{df['DO'].mean():.2f} mg/L",
            f"{df['Conductivity'].mean():.1f} µS/cm",
            f"{df['TDS'].mean():.1f} mg/L",
        ],
        "Min": [
            f"{df['Temperature'].min():.2f} °C",
            f"{df['pH'].min():.3f}",
            f"{df['Turbidity'].min():.2f} NTU",
            f"{df['DO'].min():.2f} mg/L",
            f"{df['Conductivity'].min():.1f} µS/cm",
            f"{df['TDS'].min():.1f} mg/L",
        ],
        "Max": [
            f"{df['Temperature'].max():.2f} °C",
            f"{df['pH'].max():.3f}",
            f"{df['Turbidity'].max():.2f} NTU",
            f"{df['DO'].max():.2f} mg/L",
            f"{df['Conductivity'].max():.1f} µS/cm",
            f"{df['TDS'].max():.1f} mg/L",
        ],
        "σ (Écart-type)": [
            f"{df['Temperature'].std():.3f}",
            f"{df['pH'].std():.4f}",
            f"{df['Turbidity'].std():.3f}",
            f"{df['DO'].std():.3f}",
            f"{df['Conductivity'].std():.2f}",
            f"{df['TDS'].std():.2f}",
        ],
        "Statut": [
            f"{statuses['Temperature'][2]} {statuses['Temperature'][0]}",
            f"{statuses['pH'][2]} {statuses['pH'][0]}",
            f"{statuses['Turbidity'][2]} {statuses['Turbidity'][0]}",
            f"{statuses['DO'][2]} {statuses['DO'][0]}",
            f"{statuses['Conductivity'][2]} {statuses['Conductivity'][0]}",
            f"{statuses['TDS'][2]} {statuses['TDS'][0]}",
        ],
    }
    stat_df = pd.DataFrame(stat_data)
    st.dataframe(stat_df, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tableau des 50 dernières mesures
    st.markdown('<div class="section-title">🕒 Historique Récent</div>', unsafe_allow_html=True)
    display_df = df[["Timestamp","Temperature","pH","Turbidity","DO","Conductivity","TDS"]].tail(50).copy()
    display_df = display_df.sort_values("Timestamp", ascending=False)
    display_df["Timestamp"] = display_df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    display_df = display_df.rename(columns={
        "Timestamp":    "🕒 Horodatage",
        "Temperature":  "T (°C)",
        "pH":           "pH",
        "Turbidity":    "NTU",
        "DO":           "DO (mg/L)",
        "Conductivity": "EC (µS/cm)",
        "TDS":          "TDS (mg/L)",
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=260)

    # Export CSV
    csv_data = df[["Timestamp","Temperature","pH","Turbidity","DO","Conductivity","TDS"]].copy()
    csv_data["Timestamp"] = csv_data["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    csv_data["Sensor"]    = sensor_id
    st.download_button(
        label="⬇️ Exporter CSV",
        data=csv_data.to_csv(index=False).encode("utf-8"),
        file_name=f"aquamonitor_{sensor_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # ── FOOTER ────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    refresh_ts_str = st.session_state.rt_refresh_ts.strftime("%d/%m/%Y à %H:%M:%S")
    footer_border  = "rgba(79,195,247,0.09)" if is_dark else "rgba(0,119,204,0.07)"
    footer_color   = "#4a6080" if is_dark else "#8090a8"
    st.markdown(f"""
    <div style="text-align:center; font-family:'Space Mono',monospace; font-size:0.68rem;
                color:{footer_color}; margin-top:8px;
                padding: 14px; border-top: 1px solid {footer_border};">
        📡 AquaMonitor · Firebase &nbsp;·&nbsp;
        {len(df)} mesures &nbsp;·&nbsp;
        Capteur : <b>{sensor_id}</b> &nbsp;·&nbsp;
        Période : <b>{time_label}</b> &nbsp;·&nbsp;
        6 paramètres actifs &nbsp;·&nbsp;
        Synchro : <b>{refresh_ts_str}</b>
    </div>
    """, unsafe_allow_html=True)