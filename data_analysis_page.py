"""
📊 Data Analysis Page — Water Quality Monitoring System
Drop-in replacement for the `elif menu_option == "📊 Data Analysis":` block in main.py
Can also be used standalone by calling: render_data_analysis(df)
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta
import io


# ─────────────────────────────────────────────
# THRESHOLDS (WHO / standard water quality norms)
# ─────────────────────────────────────────────
THRESHOLDS = {
    "pH":           {"min": 6.5,  "max": 8.5,   "unit": "",       "ideal": (6.5, 8.5)},
    "Temperature":  {"min": 5.0,  "max": 30.0,  "unit": "°C",     "ideal": (15.0, 25.0)},
    "Turbidity":    {"min": 0.0,  "max": 5.0,   "unit": "NTU",    "ideal": (0.0, 1.0)},
    "TDS":          {"min": 50.0, "max": 500.0, "unit": "ppm",    "ideal": (50.0, 250.0)},
    "Conductivity": {"min": 0.0,  "max": 900.0, "unit": "µS/cm",  "ideal": (200.0, 800.0)},
    "DO":           {"min": 5.0,  "max": 14.0,  "unit": "mg/L",   "ideal": (7.0, 12.0)},
}

PARAM_COLORS = {
    "pH":           "#00b4d8",
    "Temperature":  "#f77f00",
    "Turbidity":    "#359497",
    "TDS":          "#e9c46a",
    "Conductivity": "#2fa721",
    "DO":           "#52b788",
}

PARAM_ICONS = {
    "pH":           "🧪",
    "Temperature":  "🌡️",
    "Turbidity":    "🌊",
    "TDS":          "💧",
    "Conductivity": "⚡",
    "DO":           "🫧",
}

INTERPRETATIONS = {
    "pH": {
        "low":  "Le pH est trop acide — risque de corrosion des canalisations et d'irritation pour les usagers.",
        "high": "Le pH est trop basique — peut indiquer une contamination par des produits chimiques industriels.",
        "ok":   "Le pH est dans la plage normale. L'eau est chimiquement équilibrée.",
    },
    "Temperature": {
        "low":  "Température inhabituellement basse — peut indiquer un problème de capteur ou une saison froide extrême.",
        "high": "Température élevée — favorise la prolifération bactérienne et réduit l'oxygène dissous.",
        "ok":   "Température dans la plage idéale. Aucune anomalie détectée.",
    },
    "Turbidity": {
        "low":  "Turbidité très faible — eau extrêmement claire, résultats dans la norme.",
        "high": "Une variation anormale de la turbidité a été observée, ce qui peut indiquer une pollution ponctuelle ou un événement de ruissellement.",
        "ok":   "Turbidité acceptable. L'eau est visuellement claire.",
    },
    "TDS": {
        "low":  "TDS trop bas — l'eau peut manquer de minéraux essentiels.",
        "high": "TDS élevé — présence possible de contaminants dissous ou de sels minéraux excessifs.",
        "ok":   "Total des solides dissous dans la norme recommandée.",
    },
    "Conductivity": {
        "low":  "Conductivité faible — eau très pure, peut manquer de minéraux.",
        "high": "Conductivité élevée — indique une forte concentration de sels ou d'ions, risque de contamination.",
        "ok":   "Conductivité électrique dans les limites acceptables.",
    },
    "DO": {
        "low":  "Oxygène dissous insuffisant — conditions défavorables pour la vie aquatique et signe possible de pollution organique.",
        "high": "Taux d'oxygène dissous très élevé — peut résulter d'une photosynthèse intense ou d'une aération mécanique.",
        "ok":   "Oxygène dissous à un niveau optimal pour la santé aquatique.",
    },
}


# ─────────────────────────────────────────────
# CSS INJECTION
# ─────────────────────────────────────────────
def _inject_css(theme: str = "dark"):
    is_dark = theme == "dark"

    if is_dark:
        text_color = "#ffffff"  
        bg_color = "#111111"  

    else:
        text_color = "#111111"
        bg_color = "#ffffff"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');

    /* ── Page-level reset ── */
    .da-root * {{ box-sizing: border-box; }}

    /* ── Page title ── */
    .da-page-title {{
        font-family: 'DM Sans', sans-serif;
        font-size: 2.1rem;
        font-weight: 700;
        color: {text_color};
        letter-spacing: -0.5px;
        margin-bottom: 4px;
    }}
    .da-page-subtitle {{
        font-family: 'DM Sans', sans-serif;
        font-size: 0.9rem;
        color: {text_color};
        margin-bottom: 24px;
    }}
    .da-param-name {{
        font-family:'DM Sans',sans-serif;font-size:0.72rem;
        color: {text_color};
        text-transform:uppercase;
        letter-spacing:1px;margin:4px 0
    }}
    .da-period-info {{
        color: {text_color};
        font-family:'DM Sans',sans-serif;font-size:0.82rem;margin:-8px 0 16px;
    }}

    div.stDownloadButton > button {{
        background-color: {bg_color}!important;
        color: {text_color}!important;
        border-radius: 10px;
        border: none;
        padding: 0.6em 1.2em;
        font-weight: 600;
        transition: all 0.3s ease;
    }}
    div.stDownloadButton > button:hover {{
        background-color: black!important;
        color: white!important;
    }}
    .da-period-info2 {{
        font-size:0.62rem;color:{text_color};text-transform:uppercase
    }}

    .da-period-value {{
    font-family:'Space Mono',monospace;font-size:0.82rem;color:{text_color};
    }}

    /* ── Glassmorphism card ── */
    .da-card {{
        background: rgba(255,255,255,0.07);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 30px rgba(0,0,0,0.15);
    }}
    .da-card-title {{
        font-family: 'DM Sans', sans-serif;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: {text_color};
        margin-bottom: 8px;
    }}

    /* ── Stats cards ── */
    .da-stat-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 0;
    }}
    .da-stat-box {{
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 14px 16px;
        text-align: center;
        transition: background 0.2s;
    }}
    .da-stat-box:hover {{ background: rgba(255,255,255,0.10); }}
    .da-stat-label {{
        font-family: 'DM Sans', sans-serif;
        font-size: 0.72rem;
        font-weight: 500;
        color: rgba(255,255,255,0.45);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }}
    .da-stat-value {{
        font-family: 'Space Mono', monospace;
        font-size: 1.35rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1;
    }}

    /* ── Anomaly badges ── */
    .da-anomaly-list {{ display:flex; flex-direction:column; gap:8px; }}
    .da-anomaly-item {{
        display: flex;
        align-items: flex-start;
        gap: 10px;
        background: rgba(255,80,80,0.12);
        border: 1px solid rgba(255,80,80,0.25);
        border-radius: 10px;
        padding: 10px 14px;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.85rem;
        color: #ffaaaa;
    }}
    .da-anomaly-item.warn {{
        background: rgba(255,173,20,0.12);
        border-color: rgba(255,173,20,0.25);
        color: #ffd470;
    }}
    .da-anomaly-item.ok {{
        background: rgba(82,196,26,0.10);
        border-color: rgba(82,196,26,0.2);
        color: #a3f0a0;
    }}
    .da-anomaly-icon {{ font-size: 1.1rem; flex-shrink:0; margin-top:1px; }}
    .da-anomaly-text {{ line-height:1.4; color: {text_color}; }}

    /* ── Interpretation box ── */
    .da-interpret {{
        background: rgba(0,180,216,0.10);
        border-left: 3px solid #00b4d8;
        border-radius: 0 10px 10px 0;
        padding: 12px 16px;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.88rem;
        color: {text_color};
        line-height: 1.6;
        margin-top: 8px;
        font-style: italic;
    }}
    .da-interpret.warn {{
        background: rgba(255,173,20,0.10);
        border-left-color: #faad14;
    }}
    .da-interpret.error {{
        background: rgba(255,77,79,0.10);
        border-left-color: #ff4d4f;
    }}

    /* ── Period selector pills ── */
    .da-period-pill {{
        display: inline-block;
        padding: 5px 14px;
        border-radius: 20px;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem;
        font-weight: 500;
        border: 1px solid rgba(255,255,255,0.15);
        background: rgba(255,255,255,0.06);
        color: rgba(255,255,255,0.6);
        cursor: pointer;
        margin-right: 6px;
    }}

    /* ── Section divider ── */
    .da-section-header {{
        font-family: 'DM Sans', sans-serif;
        font-size: 1.05rem;
        font-weight: 600;
        color: {text_color};
        margin: 28px 0 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .da-section-header::after {{
        content: '';
        flex: 1;
        height: 1px;
        background: rgba(255,255,255,0.08);
        margin-left: 8px;
    }}

    /* ── Download button override ── */
    .da-download-row {{
        display: flex;
        justify-content: flex-end;
        margin-top: 8px;
    }}

    /* ── Param selector tabs ── */
    div[data-testid="stHorizontalBlock"] .da-param-tab button {{
        border-radius: 8px;
        font-family: 'DM Sans';
    }}
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPER: filter by period
# ─────────────────────────────────────────────
def _filter_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    if df.empty:
        return df
    now = df["created_at"].max()
    deltas = {
        "Dernière heure":   timedelta(hours=1),
        "Dernier jour":     timedelta(days=1),
        "Dernière semaine": timedelta(weeks=1),
        "Tout":             None,
    }
    delta = deltas.get(period)
    if delta is None:
        return df
    return df[df["created_at"] >= now - delta].copy()


# ─────────────────────────────────────────────
# HELPER: statistics table
# ─────────────────────────────────────────────
def _compute_stats(df: pd.DataFrame, params: list) -> pd.DataFrame:
    rows = []
    for p in params:
        if p not in df.columns:
            continue
        s = df[p].dropna()
        if s.empty:
            continue
        thr = THRESHOLDS.get(p, {})
        mean_v = s.mean()
        rows.append({
            "Paramètre": f"{PARAM_ICONS.get(p,'')} {p}",
            "Unité": thr.get("unit", ""),
            "Moyenne": round(mean_v, 3),
            "Min": round(s.min(), 3),
            "Max": round(s.max(), 3),
            "Écart-type": round(s.std(), 3),
            "Médiane": round(s.median(), 3),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# HELPER: anomaly detection
# ─────────────────────────────────────────────
def _detect_anomalies(df: pd.DataFrame) -> list:
    """Returns list of dicts: {param, n_critical, n_warning, last_value, level, msg}"""
    anomalies = []
    for param, thr in THRESHOLDS.items():
        if param not in df.columns:
            continue
        col = df[param].dropna()
        if col.empty:
            continue
        last = col.iloc[-1]
        lo, hi = thr["min"], thr["max"]
        ilo, ihi = thr["ideal"]
        n_crit = int(((col < lo) | (col > hi)).sum())
        n_warn = int(((col < ilo) | (col > ihi)).sum()) - n_crit

        if last < lo or last > hi:
            level = "error"
            direction = "low" if last < lo else "high"
        elif last < ilo or last > ihi:
            level = "warning"
            direction = "low" if last < ilo else "high"
        else:
            level = "ok"
            direction = "ok"

        anomalies.append({
            "param": param,
            "icon": PARAM_ICONS.get(param, ""),
            "last": last,
            "unit": thr.get("unit", ""),
            "n_crit": n_crit,
            "n_warn": n_warn,
            "level": level,
            "direction": direction,
            "interpretation": INTERPRETATIONS.get(param, {}).get(direction, ""),
        })
    return anomalies


# ─────────────────────────────────────────────
# SECTION: Period selector
# ─────────────────────────────────────────────
def _render_period_selector():
    st.markdown('<div class="da-section-header">⏱ Sélecteur de période</div>', unsafe_allow_html=True)
    period = st.radio(
        "",
        ["Dernière heure", "Dernier jour", "Dernière semaine", "Tout"],
        index=1,
        horizontal=True,
        label_visibility="collapsed",
        key="da_period",
    )
    return period


# ─────────────────────────────────────────────
# SECTION: Advanced charts
# ─────────────────────────────────────────────
def _render_charts(df: pd.DataFrame, params: list):
    st.markdown('<div class="da-section-header">📈 Graphiques avancés</div>', unsafe_allow_html=True)

    # --- Trend chart (multi-param overlay) ---
    with st.container():
        st.markdown('<div class="da-card-title">Analyse des tendances</div>', unsafe_allow_html=True)

        selected_params = st.multiselect(
            "Paramètres à afficher",
            params,
            default=params[:2] if len(params) >= 2 else params,
            key="da_trend_params",
        )

        if selected_params and not df.empty:
            # normalise for comparison
            plot_df = df[["created_at"] + selected_params].copy().dropna()
            melted = plot_df.melt(id_vars="created_at", value_vars=selected_params,
                                   var_name="Paramètre", value_name="Valeur")

            color_map = {p: PARAM_COLORS.get(p, "#ffffff") for p in selected_params}

            chart = (
                alt.Chart(melted)
                .mark_line(interpolate="monotone", strokeWidth=2)
                .encode(
                    x=alt.X("created_at:T", title="Temps", axis=alt.Axis(labelColor="#aaa", titleColor="#aaa", gridColor="rgba(255,255,255,0.05)")),
                    y=alt.Y("Valeur:Q", title="Valeur", axis=alt.Axis(labelColor="#aaa", titleColor="#aaa", gridColor="rgba(255,255,255,0.05)")),
                    color=alt.Color("Paramètre:N", scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values())),
                                    legend=alt.Legend(labelColor="#ccc", titleColor="#ccc")),
                    tooltip=["created_at:T", "Paramètre:N", alt.Tooltip("Valeur:Q", format=".3f")],
                )
                .properties(height=280)
                .configure_view(fill="transparent", stroke="transparent")
                .configure(background="transparent")
            )
            st.altair_chart(chart, width="stretch")
        else:
            st.info("Sélectionnez au moins un paramètre.")

    # --- Comparison scatter ---
    with st.container():
        st.markdown('<div class="da-card-title">Comparaison entre paramètres</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            x_param = st.selectbox("Axe X", params, index=0, key="da_x_param")
        with col2:
            y_param = st.selectbox("Axe Y", params, index=min(1, len(params)-1), key="da_y_param")

        if x_param and y_param and not df.empty and x_param != y_param:
            scatter_df = df[[x_param, y_param, "created_at"]].dropna()
            if not scatter_df.empty:
                scatter = (
                    alt.Chart(scatter_df)
                    .mark_circle(size=60, opacity=0.7)
                    .encode(
                        x=alt.X(f"{x_param}:Q", title=f"{x_param} ({THRESHOLDS.get(x_param,{}).get('unit','')})",
                                axis=alt.Axis(labelColor="#aaa", titleColor="#aaa", gridColor="rgba(255,255,255,0.05)")),
                        y=alt.Y(f"{y_param}:Q", title=f"{y_param} ({THRESHOLDS.get(y_param,{}).get('unit','')})",
                                axis=alt.Axis(labelColor="#aaa", titleColor="#aaa", gridColor="rgba(255,255,255,0.05)")),
                        color=alt.value(PARAM_COLORS.get(x_param, "#00b4d8")),
                        tooltip=["created_at:T",
                                 alt.Tooltip(f"{x_param}:Q", format=".3f"),
                                 alt.Tooltip(f"{y_param}:Q", format=".3f")],
                    )
                    .properties(height=260)
                    .configure_view(fill="transparent", stroke="transparent")
                    .configure(background="transparent")
                )
                st.altair_chart(scatter, width="stretch")
        elif x_param == y_param:
            st.warning("Sélectionnez deux paramètres différents.")

    # --- Matrice de corrélation (multi-paramètres) ---
    with st.container():
        st.markdown('<div class="da-card-title">Matrice de corrélation</div>', unsafe_allow_html=True)

        # L'utilisateur choisit les paramètres à croiser (tous par défaut)
        corr_params = st.multiselect(
            "Paramètres à croiser",
            params,
            default=params,
            key="da_corr_params",
        )

        # Il faut au moins 2 paramètres et des données
        if len(corr_params) < 2:
            st.info("Sélectionnez au moins deux paramètres pour la matrice.")
        elif df.empty:
            st.info("Aucune donnée disponible.")
        else:
            # On ne garde que les colonnes numériques réellement présentes
            cols = [p for p in corr_params if p in df.columns]
            num_df = df[cols].apply(pd.to_numeric, errors="coerce").dropna()

            # Une colonne constante (variance nulle, ex: EC=0) ne peut pas
            # être corrélée → on l'écarte pour éviter une case vide/NaN.
            varying = [c for c in cols if num_df[c].nunique() > 1]
            dropped = [c for c in cols if c not in varying]

            if len(varying) < 2:
                st.warning(
                    "Pas assez de paramètres variables pour une corrélation. "
                    "Les paramètres constants (valeur figée, ex. capteur à 0) "
                    "ne peuvent pas être corrélés : " + ", ".join(dropped)
                )
            else:
                if dropped:
                    st.caption("⚠️ Écartés car constants : " + ", ".join(dropped))

                # Calcul de la matrice de corrélation (coefficient de Pearson)
                corr = num_df[varying].corr().round(2)

                # Mise en forme « longue » pour Altair (paire X, paire Y, valeur)
                corr_long = corr.reset_index().melt(
                    id_vars="index", var_name="Paramètre Y", value_name="Corrélation"
                )
                corr_long = corr_long.rename(columns={"index": "Paramètre X"})

                base = alt.Chart(corr_long).encode(
                    x=alt.X("Paramètre X:O", title="",
                            axis=alt.Axis(labelColor="#ccc", labelAngle=-40)),
                    y=alt.Y("Paramètre Y:O", title="",
                            axis=alt.Axis(labelColor="#ccc")),
                )
                heat = base.mark_rect(cornerRadius=3).encode(
                    color=alt.Color(
                        "Corrélation:Q",
                        scale=alt.Scale(scheme="redblue", domain=[-1, 1]),
                        legend=alt.Legend(title="r", labelColor="#ccc", titleColor="#ccc"),
                    ),
                    tooltip=["Paramètre X", "Paramètre Y",
                             alt.Tooltip("Corrélation:Q", format=".2f")],
                )
                # Valeur du coefficient écrite dans chaque case
                text = base.mark_text(fontSize=12, fontWeight="bold").encode(
                    text=alt.Text("Corrélation:Q", format=".2f"),
                    color=alt.condition(
                        "abs(datum.Corrélation) > 0.5",
                        alt.value("white"), alt.value("#222"),
                    ),
                )
                matrix = (heat + text).properties(height=320).configure_view(
                    fill="transparent", stroke="transparent"
                ).configure(background="transparent")

                st.altair_chart(matrix, width="stretch")
                st.caption(
                    "Lecture : +1 (bleu) = les deux paramètres augmentent ensemble · "
                    "−1 (rouge) = l'un monte quand l'autre descend · 0 = aucun lien."
                )

    # --- Heatmap (hourly average) ---
    if not df.empty and len(df) > 10:
        with st.container():
            st.markdown('<div class="da-card-title">Carte de chaleur — moyenne horaire</div>', unsafe_allow_html=True)

            heat_param = st.selectbox("Paramètre", params, key="da_heat_param")
            if heat_param in df.columns:
                hdf = df[["created_at", heat_param]].dropna().copy()
                hdf["heure"] = hdf["created_at"].dt.hour
                hdf["jour"]  = hdf["created_at"].dt.strftime("%d/%m")
                hdf_avg = hdf.groupby(["jour", "heure"])[heat_param].mean().reset_index()
                hdf_avg.columns = ["Jour", "Heure", "Valeur"]

                heat = (
                    alt.Chart(hdf_avg)
                    .mark_rect(cornerRadius=2)
                    .encode(
                        x=alt.X("Heure:O", title="Heure", axis=alt.Axis(labelColor="#aaa", titleColor="#aaa")),
                        y=alt.Y("Jour:O",  title="Date",  axis=alt.Axis(labelColor="#aaa", titleColor="#aaa")),
                        color=alt.Color("Valeur:Q",
                                        scale=alt.Scale(scheme="blues"),
                                        legend=alt.Legend(labelColor="#ccc", titleColor="#ccc")),
                        tooltip=["Jour:O", "Heure:O", alt.Tooltip("Valeur:Q", format=".3f")],
                    )
                    .properties(height=200)
                    .configure_view(fill="transparent", stroke="transparent")
                    .configure(background="transparent")
                )
                st.altair_chart(heat, width="stretch")


# ─────────────────────────────────────────────
# SECTION: Statistics
# ─────────────────────────────────────────────
def _render_stats(df: pd.DataFrame, params: list):
    st.markdown('<div class="da-section-header">📊 Statistiques descriptives</div>', unsafe_allow_html=True)

    with st.container():

        stats_df = _compute_stats(df, params)
        if not stats_df.empty:
            # Styled metric cards per param
            cols = st.columns(len(params))
            for i, param in enumerate(params):
                if param not in df.columns:
                    continue
                s = df[param].dropna()
                if s.empty:
                    continue
                val = df[param].iloc[-1]

                unit = THRESHOLDS.get(param, {}).get("unit", "")
                icon = PARAM_ICONS.get(param, "")
                color = PARAM_COLORS.get(param, "#ffffff")
                with cols[i]:
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.05);border:1px solid {color}33;
                                border-top: 3px solid {color};border-radius:12px;
                                padding:14px 12px;text-align:center;margin-bottom:8px;">
                        <div style="font-size:1.4rem">{icon}</div>
                        <div class="da-param-name">{param}</div>
                        <div style="font-family:'Space Mono',monospace;font-size:1.25rem;font-weight:700;color:{color}">
                            {val}
                            <span style="font-size:0.7rem;color:rgba(255,255,255,0.4)"> {unit}</span>
                        </div>
                        <div style="display:flex;justify-content:space-around;margin-top:8px;">
                            <div>
                                <div class="da-period-info2">Min</div>
                                <div class="da-period-value">{round(s.min(),2)}</div>
                            </div>
                            <div>
                                <div class="da-period-info2">Moy</div>
                                <div class="da-period-value">{round(s.mean(),2)}</div>
                            </div>
                            <div>
                                <div class="da-period-info2">Max</div>
                                <div class="da-period-value">{round(s.max(),2)}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()
            st.markdown("**Tableau complet (df.describe())**")
            describe_cols = [p for p in params if p in df.columns]
            if describe_cols:
                desc = df[describe_cols].describe().round(3)
                st.dataframe(desc,width="stretch")


# ─────────────────────────────────────────────
# SECTION: Anomaly detection
# ─────────────────────────────────────────────
def _render_anomalies(df: pd.DataFrame):
    st.markdown('<div class="da-section-header">🚨 Détection d\'anomalies</div>', unsafe_allow_html=True)

    with st.container():
        anomalies = _detect_anomalies(df)

        # Summary badges
        n_errors   = sum(1 for a in anomalies if a["level"] == "error")
        n_warnings = sum(1 for a in anomalies if a["level"] == "warning")
        n_ok       = sum(1 for a in anomalies if a["level"] == "ok")

        badge_cols = st.columns(3)
        with badge_cols[0]:
            st.markdown(f"""
            <div style="background:rgba(255,80,80,0.12);border:1px solid rgba(255,80,80,0.3);
                        border-radius:10px;padding:12px;text-align:center">
                <div style="font-size:1.6rem">🚨</div>
                <div style="font-family:'Space Mono',monospace;font-size:1.5rem;font-weight:700;color:#ff7070">{n_errors}</div>
                <div class="da-period-info2">Critiques</div>
            </div>""", unsafe_allow_html=True)
        with badge_cols[1]:
            st.markdown(f"""
            <div style="background:rgba(255,173,20,0.12);border:1px solid rgba(255,173,20,0.3);
                        border-radius:10px;padding:12px;text-align:center">
                <div style="font-size:1.6rem">⚠️</div>
                <div style="font-family:'Space Mono',monospace;font-size:1.5rem;font-weight:700;color:#ffd470">{n_warnings}</div>
                <div class="da-period-info2">Avertissements</div>
            </div>""", unsafe_allow_html=True)
        with badge_cols[2]:
            st.markdown(f"""
            <div style="background:rgba(82,196,26,0.10);border:1px solid rgba(82,196,26,0.25);
                        border-radius:10px;padding:12px;text-align:center">
                <div style="font-size:1.6rem">✅</div>
                <div style="font-family:'Space Mono',monospace;font-size:1.5rem;font-weight:700;color:#a3f0a0">{n_ok}</div>
                <div class="da-period-info2">Normaux</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Detail per parameter
        for a in anomalies:
            level_css = {"error": "", "warning": "warn", "ok": "ok"}.get(a["level"], "")
            level_icon = {"error": "🚨", "warning": "⚠️", "ok": "✅"}.get(a["level"], "")
            thr = THRESHOLDS.get(a["param"], {})
            lo, hi = thr.get("min","?"), thr.get("max","?")
            n_total = len(df[a["param"]].dropna()) if a["param"] in df.columns else 0
            n_anom = a["n_crit"] + a["n_warn"]

            st.markdown(f"""
            <div class="da-anomaly-item {level_css}">
                <span class="da-anomaly-icon">{level_icon}</span>
                <div class="da-anomaly-text">
                    <strong>{a['icon']} {a['param']}</strong>
                    — dernière valeur : <strong>{round(a['last'],3)} {a['unit']}</strong>
                    &nbsp;|&nbsp; seuils : [{lo} – {hi} {a['unit']}]
                    &nbsp;|&nbsp; {n_anom}/{n_total} mesures hors norme
                </div>
            </div>
            """, unsafe_allow_html=True)



# ─────────────────────────────────────────────
# SECTION: Interpretation
# ─────────────────────────────────────────────
def _render_interpretations(df: pd.DataFrame):
    st.markdown('<div class="da-section-header">🧠 Interprétation intelligente</div>', unsafe_allow_html=True)

    with st.container():
        anomalies = _detect_anomalies(df)

        has_issue = False
        for a in anomalies:
            if a["level"] in ("error", "warning") and a["interpretation"]:
                has_issue = True
                css_class = "error" if a["level"] == "error" else "warn"
                st.markdown(f"""
                <div class="da-interpret {css_class}">
                    {a['icon']} <strong>{a['param']}</strong> — {a['interpretation']}
                </div>
                """, unsafe_allow_html=True)

        if not has_issue:
            st.markdown("""
            <div class="da-interpret">
                ✅ Tous les paramètres sont dans les plages normales.
                L'eau analysée présente des caractéristiques conformes aux normes de qualité recommandées.
                Aucune intervention n'est nécessaire pour le moment.
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION: Download
# ─────────────────────────────────────────────
def _render_download(df: pd.DataFrame):
    st.markdown('<div class="da-section-header">⬇️ Téléchargement des données</div>', unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            start_d = st.date_input("📅 Date de début", value=df["created_at"].min().date() if not df.empty else None, key="da_dl_start")
        with col2:
            end_d = st.date_input("📅 Date de fin", value=df["created_at"].max().date() if not df.empty else None, key="da_dl_end")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            fmt = st.selectbox("Format", ["CSV", "JSON"], key="da_dl_fmt")

        # Filter by dates
        if not df.empty and start_d and end_d:
            mask = (df["created_at"].dt.date >= start_d) & (df["created_at"].dt.date <= end_d)
            export_df = df[mask]
        else:
            export_df = df

        n_rows = len(export_df)
        st.markdown(f"<small class='da-period-info2'>{n_rows} enregistrements sélectionnés</small>", unsafe_allow_html=True)

        if fmt == "CSV":
            file_data = export_df.to_csv(index=False).encode("utf-8")
            mime = "text/csv"
            fname = f"water_quality_{start_d}_{end_d}.csv"
        else:
            file_data = export_df.to_json(orient="records", date_format="iso").encode("utf-8")
            mime = "application/json"
            fname = f"water_quality_{start_d}_{end_d}.json"

        st.download_button(
            label=f"⬇️ Exporter {n_rows} enregistrements ({fmt})",
            data=file_data,
            file_name=fname,
            mime=mime,
            width="stretch",
            
        )


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────
def render_data_analysis(df: pd.DataFrame, theme: str = "dark"):
    """
    Call this function inside your `elif menu_option == "📊 Data Analysis":` block.
    Pass the full dataframe (with `created_at` column already as datetime).
    """
    _inject_css(theme)

    st.markdown("""
    <div class="da-root">
        <div class="da-page-title">📊 Analyse des Données</div>
        <div class="da-page-subtitle">Explorez les tendances historiques, comparez les paramètres et détectez les anomalies en temps réel.</div>
    </div>
    """, unsafe_allow_html=True)

    PARAMS = ["pH", "Temperature", "Turbidity", "TDS", "Conductivity", "DO"]
    available_params = [p for p in PARAMS if p in df.columns]

    if df.empty:
        st.warning("⚠️ Aucune donnée disponible. Vérifiez la connexion à la source de données.")
        return

    # ── Period selector ──
    period = _render_period_selector()
    df_filtered = _filter_by_period(df, period)

    if df_filtered.empty:
        st.info(f"Aucune donnée disponible pour la période : **{period}**. Essayez une période plus longue.")
        df_filtered = df  # fallback to all

    st.markdown(f"""
    <div class="da-period-info">
        📦 {len(df_filtered)} mesures &nbsp;|&nbsp;
        🕒 {df_filtered['created_at'].min().strftime('%d/%m/%Y %H:%M')}
        → {df_filtered['created_at'].max().strftime('%d/%m/%Y %H:%M')}
    </div>
    """, unsafe_allow_html=True)

    # ── Charts ──
    _render_charts(df_filtered, available_params)

    # ── Stats ──
    _render_stats(df_filtered, available_params)

    # ── Anomalies ──
    _render_anomalies(df_filtered)

    # ── Interpretations ──
    _render_interpretations(df_filtered)

    # ── Download ──
    _render_download(df_filtered)
