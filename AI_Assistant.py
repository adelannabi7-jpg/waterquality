"""
AquaMonitor AI Assistant — OpenRouter-powered water quality chat.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional
import json

from utils.openrouter_client import OpenRouterClient
system_prompt = "You are a water quality AI assistant."
DEFAULT_MODEL = "poolside/laguna-m1-free"

st.set_page_config(
    page_title="AI Assistant — AquaMonitor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Theme ─────────────────────────────────────────────────────────

THEME = st.session_state.get("theme", "dark")
IS_DARK = THEME == "dark"

_DARK = {
    "bg": "#080e1a", "card": "rgba(10,20,50,0.55)",
    "border": "rgba(100,180,255,0.15)", "shine": "rgba(255,255,255,0.05)",
    "text": "#e8f0ff", "muted": "#7090b8",
    "accent": "#38bdf8", "accent2": "#818cf8",
    "glow": "rgba(56,189,248,0.25)",
    "user_bubble": "rgba(56,189,248,0.15)",
    "ai_bubble": "rgba(12,24,60,0.75)",
    "code_bg": "rgba(0,0,0,0.35)",
    "input_bg": "rgba(20,35,80,0.70)",
    "status_ok": "#34d399", "status_err": "#f87171", "status_warn": "#fbbf24",
    "orb1": "rgba(56,189,248,0.12)", "orb2": "rgba(129,140,248,0.10)", "orb3": "rgba(34,211,238,0.08)",
}
_LIGHT = {
    "bg": "#e8f4fd", "card": "rgba(255,255,255,0.80)",
    "border": "rgba(0,120,220,0.18)", "shine": "rgba(255,255,255,0.65)",
    "text": "#1a2a4a", "muted": "#5070a0",
    "accent": "#0077cc", "accent2": "#6366f1",
    "glow": "rgba(0,119,204,0.20)",
    "user_bubble": "rgba(0,119,204,0.10)",
    "ai_bubble": "rgba(220,240,255,0.75)",
    "code_bg": "rgba(255,255,255,0.50)",
    "input_bg": "rgba(230,242,255,0.85)",
    "status_ok": "#059669", "status_err": "#dc2626", "status_warn": "#d97706",
    "orb1": "rgba(0,119,204,0.08)", "orb2": "rgba(99,102,241,0.06)", "orb3": "rgba(6,182,212,0.06)",
}
C = _DARK if IS_DARK else _LIGHT

def get_latest_readings(df: pd.DataFrame) -> Optional[dict]:
    if df.empty:
        return None
    row = df.iloc[-1]
    ts = row.get("created_at", pd.NaT)
    return {
        "Temperature": round(float(row["Temperature"]), 2) if pd.notna(row["Temperature"]) else "N/A",
        "pH": round(float(row["pH"]), 3) if pd.notna(row["pH"]) else "N/A",
        "Turbidity": round(float(row["Turbidity"]), 2) if pd.notna(row["Turbidity"]) else "N/A",
        "DO": round(float(row["DO"]), 2) if pd.notna(row["DO"]) else "N/A",
        "Conductivity": round(float(row["Conductivity"]), 1) if pd.notna(row["Conductivity"]) else "N/A",
        "TDS": round(float(row["TDS"]), 1) if pd.notna(row["TDS"]) else "N/A",
        "timestamp": ts.strftime("%H:%M:%S %d/%m/%Y") if pd.notna(ts) else "N/A",
    }


# ── Parameter Status Helpers ──────────────────────────────────────

THRESHOLDS = {
    "Temperature":  {"ideal": (15, 25), "ok": (5, 30)},
    "pH":           {"ideal": (6.5, 8.5), "ok": (5.5, 9.5)},
    "Turbidity":    {"ideal": (0, 5), "ok": (0, 10)},
    "DO":           {"ideal": (6, 14), "ok": (4, 14)},
    "Conductivity": {"ideal": (0, 500), "ok": (0, 1000)},
    "TDS":          {"ideal": (0, 300), "ok": (0, 600)},
}

PARAM_ICONS = {
    "Temperature": "🌡", "pH": "🧪", "Turbidity": "🌊",
    "DO": "💧", "Conductivity": "⚡", "TDS": "🔬",
}
PARAM_UNITS = {
    "Temperature": "°C", "pH": "", "Turbidity": "NTU",
    "DO": "mg/L", "Conductivity": "µS/cm", "TDS": "mg/L",
}


def param_status(param: str, value):
    if value == "N/A" or pd.isna(value):
        return "N/A", C["muted"], "\u2014"
    t = THRESHOLDS[param]
    lo, hi = t["ideal"]
    if lo <= value <= hi:
        return "Optimal", C["status_ok"], "\U0001f7e2"
    elif t["ok"][0] <= value <= t["ok"][1]:
        return "Attention", C["status_warn"], "\U0001f7e1"
    else:
        return "Critique", C["status_err"], "\U0001f534"


# ── CSS Injection ─────────────────────────────────────────────────

def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

    .stApp {{ background: {C["bg"]} !important; }}
    .stApp::before {{
        content: ""; position: fixed; inset: 0; pointer-events: none;
        background:
            radial-gradient(ellipse 600px 500px at 15% 20%, {C["orb1"]}, transparent 70%),
            radial-gradient(ellipse 500px 400px at 80% 70%, {C["orb2"]}, transparent 70%),
            radial-gradient(ellipse 400px 350px at 55% 45%, {C["orb3"]}, transparent 70%);
        z-index: 0;
    }}
    .stApp > .main, .stApp > .main .block-container {{
        background: transparent !important; padding: 0 1.5rem 2rem !important;
        max-width: 100% !important; position: relative; z-index: 1;
    }}
    .stAppDeployButton, #MainMenu, footer {{ display: none !important; }}
    body, p, .stMarkdown, .stText, label, h1, h2, h3, h4, h5, h6 {{
        color: {C["text"]} !important;
        font-family: 'Inter', system-ui, sans-serif !important;
    }}
    ::-webkit-scrollbar {{ width: 5px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: {C["border"]}; border-radius: 4px; }}

    /* ── Header ── */
    .ai-header {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 14px 22px; margin: 8px 0 14px;
        background: {C["card"]}; border: 1px solid {C["border"]};
        border-radius: 18px; backdrop-filter: blur(24px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.18), inset 0 1px 0 {C["shine"]};
        animation: fadeDown 0.5s ease both;
    }}
    .ai-header-left {{ display: flex; align-items: center; gap: 14px; }}
    .ai-header-icon {{
        width: 44px; height: 44px; border-radius: 14px;
        background: linear-gradient(135deg, {C["accent"]}, {C["accent2"]});
        display: flex; align-items: center; justify-content: center;
        font-size: 22px; box-shadow: 0 0 24px {C["glow"]};
        position: relative; overflow: hidden;
    }}
    .ai-header-icon::after {{
        content: ""; position: absolute; inset: 0;
        background: linear-gradient(180deg, rgba(255,255,255,0.20) 0%, transparent 50%);
        border-radius: inherit;
    }}
    .ai-header-title {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 17px; font-weight: 700; color: {C["text"]}; letter-spacing: -0.3px;
    }}
    .ai-header-sub {{
        font-size: 10px; color: {C["muted"]};
        letter-spacing: 1.5px; text-transform: uppercase;
    }}
    .ai-header-right {{ display: flex; align-items: center; gap: 10px; }}
    .ai-model-badge {{
        font-family: 'JetBrains Mono', monospace; font-size: 10px;
        color: {C["accent"]}; background: {C["user_bubble"]};
        border: 1px solid {C["border"]}; border-radius: 20px;
        padding: 4px 12px; letter-spacing: 0.5px;
        white-space: nowrap;
    }}
    .ai-status-dot {{
        width: 8px; height: 8px; border-radius: 50%; display: inline-block;
        background: {C["status_ok"]}; box-shadow: 0 0 8px {C["status_ok"]};
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.5; transform: scale(0.8); }}
    }}

    /* ── Sensor Bar ── */
    .sensor-bar {{
        display: flex; flex-wrap: wrap; gap: 6px;
        padding: 10px 16px; margin-bottom: 16px;
        background: {C["card"]}; border: 1px solid {C["border"]};
        border-radius: 14px; backdrop-filter: blur(20px);
        animation: fadeUp 0.5s ease 0.1s both;
    }}
    .sensor-chip {{
        display: inline-flex; align-items: center; gap: 5px;
        font-family: 'JetBrains Mono', monospace; font-size: 11px;
        padding: 4px 10px; border-radius: 10px;
        background: {C["input_bg"]}; border: 1px solid {C["border"]};
        color: {C["text"]}; transition: all 0.2s;
    }}
    .sensor-chip:hover {{ border-color: {C["accent"]}; transform: translateY(-1px); }}
    .sensor-chip .dot {{
        width: 5px; height: 5px; border-radius: 50%; display: inline-block;
    }}
    .sensor-chip .val {{ font-weight: 600; }}
    .sensor-chip .unit {{ color: {C["muted"]}; font-size: 10px; }}

    /* ── Chat Messages ── */
    [data-testid="stChatMessage"] {{
        padding: 2px 0 !important;
        background: transparent !important;
        border: none !important;
        animation: msgIn 0.35s ease both;
    }}
    @keyframes msgIn {{
        from {{ opacity: 0; transform: translateY(10px) scale(0.98); }}
        to   {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    [data-testid="stChatMessageContent"] {{
        padding: 10px 16px !important;
        border-radius: 4px 16px 16px 16px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        line-height: 1.7 !important;
        color: {C["text"]} !important;
        border: 1px solid {C["border"]} !important;
        max-width: 88% !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.10) !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }}
    [data-testid="stChatMessage"][data-testid-user-chat-message="true"]
    [data-testid="stChatMessageContent"] {{
        background: {C["user_bubble"]} !important;
        border-radius: 16px 4px 16px 16px !important;
        margin-left: auto !important;
        backdrop-filter: blur(8px) !important;
        border-color: rgba(56,189,248,0.25) !important;
    }}
    [data-testid="stChatMessage"]:not([data-testid-user-chat-message="true"])
    [data-testid="stChatMessageContent"] {{
        background: {C["ai_bubble"]} !important;
        backdrop-filter: blur(12px) !important;
    }}
    [data-testid="chatAvatarIcon"] {{
        width: 32px !important; height: 32px !important;
        border-radius: 50% !important;
        font-size: 15px !important;
        display: flex !important; align-items: center !important;
        justify-content: center !important;
    }}
    [data-testid="stChatMessage"] [data-testid="chatAvatarIcon"] {{
        background: {C["user_bubble"]} !important;
        border: 1px solid {C["border"]} !important;
    }}
    [data-testid="stChatMessage"]:not([data-testid-user-chat-message="true"])
    [data-testid="chatAvatarIcon"] {{
        background: linear-gradient(135deg, {C["accent"]}, {C["accent2"]}) !important;
        border: none !important;
        box-shadow: 0 0 16px {C["glow"]} !important;
    }}
    [data-testid="stChatMessageContent"] p {{ margin: 0 0 6px !important; }}
    [data-testid="stChatMessageContent"] p:last-child {{ margin-bottom: 14px !important; }}
    [data-testid="stChatMessageContent"] ul, [data-testid="stChatMessageContent"] ol {{
        margin: 4px 0 !important; padding-left: 20px !important;
    }}
    [data-testid="stChatMessageContent"] li {{ margin: 2px 0 !important; }}
    [data-testid="stChatMessageContent"] h1, [data-testid="stChatMessageContent"] h2,
    [data-testid="stChatMessageContent"] h3, [data-testid="stChatMessageContent"] h4 {{
        margin: 8px 0 4px !important; color: {C["accent"]} !important;
    }}
    [data-testid="stChatMessageContent"] hr {{
        border: none; height: 1px;
        background: linear-gradient(90deg, transparent, {C["border"]}, transparent);
        margin: 8px 0;
    }}
    [data-testid="stChatMessageContent"] blockquote {{
        border-left: 3px solid {C["accent"]} !important;
        padding-left: 12px !important;
        margin: 6px 0 !important;
        color: {C["muted"]} !important;
    }}

    /* ── Code Blocks ── */
    [data-testid="stChatMessageContent"] code {{
        background: {C["code_bg"]} !important;
        padding: 2px 6px !important; border-radius: 4px !important;
        font-size: 12.5px !important;
        font-family: 'JetBrains Mono', monospace !important;
        border: 1px solid {C["border"]} !important;
    }}
    [data-testid="stChatMessageContent"] pre {{
        background: {C["code_bg"]} !important;
        border: 1px solid {C["border"]} !important;
        border-radius: 10px !important;
        padding: 12px 14px !important;
        overflow-x: auto !important;
        margin: 8px 0 !important;
    }}
    [data-testid="stChatMessageContent"] pre code {{
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        font-size: 12px !important;
        line-height: 1.5 !important;
    }}

    /* ── Tables ── */
    [data-testid="stChatMessageContent"] table {{
        font-size: 12px !important; border-collapse: collapse !important;
        margin: 6px 0 !important; width: 100% !important;
        display: block; overflow-x: auto;
    }}
    [data-testid="stChatMessageContent"] th, [data-testid="stChatMessageContent"] td {{
        border: 1px solid {C["border"]} !important;
        padding: 5px 10px !important; text-align: left !important;
    }}
    [data-testid="stChatMessageContent"] th {{
        background: {C["input_bg"]} !important; color: {C["accent"]} !important;
        font-weight: 600 !important;
    }}
    [data-testid="stChatMessageContent"] a {{
        color: {C["accent"]} !important; text-decoration: underline !important;
    }}

    /* ── Input ── */
    .stChatInputContainer {{
        background: {C["card"]} !important;
        border: 1px solid {C["border"]} !important;
        border-radius: 16px !important;
        backdrop-filter: blur(20px) !important;
        padding: 4px !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.15) !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }}
    .stChatInputContainer:focus-within {{
        border-color: {C["accent"]} !important;
        box-shadow: 0 0 0 3px {C["glow"]} !important;
    }}
    .stChatInputContainer input {{
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important; color: {C["text"]} !important;
        background: transparent !important; border: none !important;
    }}
    .stChatInputContainer input::placeholder {{
        color: {C["muted"]} !important; opacity: 0.6;
    }}
    .stChatInputContainer button {{
        background: linear-gradient(135deg, {C["accent"]}, {C["accent2"]}) !important;
        border: none !important; border-radius: 12px !important;
        color: white !important; font-weight: 600 !important;
        font-size: 13px !important; padding: 6px 18px !important;
        transition: all 0.2s !important;
    }}
    .stChatInputContainer button:hover {{
        transform: scale(1.04) !important;
        box-shadow: 0 0 20px {C["glow"]} !important;
    }}

    /* ── Suggested Questions ── */
    .suggestions {{
        display: flex; flex-wrap: wrap; gap: 8px;
        margin: 4px 0 14px; animation: fadeUp 0.5s ease 0.2s both;
    }}
    .suggestion-pill {{
        font-family: 'Inter', sans-serif; font-size: 12px;
        padding: 7px 18px; border-radius: 20px;
        border: 1px solid {C["border"]};
        background: {C["input_bg"]}; color: {C["text"]};
        cursor: pointer; transition: all 0.25s;
        backdrop-filter: blur(8px);
        display: inline-flex; align-items: center; gap: 6px;
    }}
    .suggestion-pill:hover {{
        border-color: {C["accent"]}; background: {C["user_bubble"]};
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(56,189,248,0.15);
    }}

    /* ── Typing Indicator ── */
    .typing-container {{
        display: flex; align-items: center; gap: 10px;
        padding: 8px 0; animation: fadeUp 0.3s ease both;
    }}
    .typing-dots {{
        display: flex; align-items: center; gap: 5px;
        padding: 10px 18px;
        background: {C["ai_bubble"]};
        border: 1px solid {C["border"]};
        border-radius: 4px 16px 16px 16px;
    }}
    .typing-dot {{
        width: 8px; height: 8px; border-radius: 50%;
        background: {C["accent"]};
        animation: typingBounce 1.4s ease-in-out infinite;
    }}
    .typing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
    .typing-dot:nth-child(3) {{ animation-delay: 0.4s; }}
    @keyframes typingBounce {{
        0%, 60%, 100% {{ transform: translateY(0); opacity: 0.4; }}
        30% {{ transform: translateY(-8px); opacity: 1; }}
    }}

    /* ── Empty State ── */
    .empty-state {{
        text-align: center; padding: 40px 24px 20px;
        animation: fadeUp 0.6s ease both;
    }}
    .empty-state-graphic {{
        font-size: 56px; margin-bottom: 10px;
        display: inline-block;
        filter: drop-shadow(0 0 20px {C["glow"]});
        animation: floatGraphic 4s ease-in-out infinite;
    }}
    @keyframes floatGraphic {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-8px); }}
    }}
    .empty-state-title {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 19px; font-weight: 700;
        color: {C["text"]}; margin-bottom: 6px;
    }}
    .empty-state-text {{
        font-size: 13px; color: {C["muted"]};
        max-width: 460px; margin: 0 auto; line-height: 1.7;
    }}
    .empty-state-features {{
        display: flex; flex-wrap: wrap; justify-content: center; gap: 6px;
        margin: 14px 0 10px;
    }}
    .empty-state-feature {{
        font-size: 11px; padding: 4px 12px;
        border-radius: 12px;
        background: {C["input_bg"]}; border: 1px solid {C["border"]};
        color: {C["muted"]};
    }}

    /* ── Controls row ── */
    .chat-controls {{
        display: flex; align-items: center; gap: 10px;
        margin-bottom: 10px; animation: fadeUp 0.5s ease 0.15s both;
    }}
    .chat-controls .msg-count {{
        font-size: 11px; color: {C["muted"]};
        font-family: 'JetBrains Mono', monospace;
    }}

    /* ── Footer ── */
    .ai-footer {{
        text-align: center; padding: 20px 0 8px;
        font-size: 11px; color: {C["muted"]}; letter-spacing: 0.3px;
    }}
    .ai-footer a {{ color: {C["accent"]}; text-decoration: none; }}

    /* ── Animations ── */
    @keyframes fadeUp {{
        from {{ opacity: 0; transform: translateY(12px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes fadeDown {{
        from {{ opacity: 0; transform: translateY(-12px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    </style>
    """, unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────

def render_sensor_bar(readings: Optional[dict]):
    if not readings:
        return
    chips = ""
    for param in ["Temperature", "pH", "Turbidity", "DO", "Conductivity", "TDS"]:
        val = readings.get(param, "N/A")
        _, color, _ = param_status(param, val)
        val_str = f"{val}" if val == "N/A" else f"{val}"
        unit = PARAM_UNITS.get(param, "")
        chips += f"""<div class="sensor-chip">
            <span class="dot" style="background:{color};box-shadow:0 0 6px {color};"></span>
            {PARAM_ICONS.get(param,"")}
            <span class="val">{val_str}</span>
            <span class="unit">{unit}</span>
        </div>"""
    ts = readings.get("timestamp", "")
    st.markdown(f"""<div class="sensor-bar">
        {chips}
        <div style="margin-left:auto;font-size:10px;color:{C["muted"]};
                    font-family:'JetBrains Mono',monospace;align-self:center;">
            \u23f0 {ts}
        </div>
    </div>
    """, unsafe_allow_html=True)


def build_api_messages(chat_history: list, readings: Optional[dict]) -> list:
    system_content = system_prompt

    return [{"role": "system", "content": system_content}] + [
        {"role": m["role"], "content": m["content"]}
        for m in chat_history
    ]
    


# ── Main ─────────────────────────────────────────────────────────

def render_ai(df: pd.DataFrame, theme: str = "dark"):
    inject_css()

    # ── Init session state ──
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []
    if "ai_client" not in st.session_state:
        st.session_state.ai_client = OpenRouterClient()
    if "ai_new_chat_key" not in st.session_state:
        st.session_state.ai_new_chat_key = 0
    if "ai_model" not in st.session_state:
        st.session_state.ai_model = DEFAULT_MODEL

    client = st.session_state.ai_client
    readings = get_latest_readings(df)

    model_name = (
        st.session_state.ai_model.split("/")[-1]
        .split(":")[0]
        .replace("-", " ")
        .title()
    )

    # ── Header ──
    st.markdown(f"""
    <div class="ai-header">
        <div class="ai-header-left">
            <div class="ai-header-icon">🤖</div>
            <div>
                <div class="ai-header-title">AquaBot AI</div>
                <div class="ai-header-sub">Water Quality Intelligence</div>
            </div>
        </div>
        <div class="ai-header-right">
            <span class="ai-model-badge">
                <span class="ai-status-dot"></span> {model_name}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_sensor_bar(readings)

    # ── Controls ──
    msg_count = len([m for m in st.session_state.ai_messages if m["role"] == "assistant"])
    col1, col2 = st.columns([6, 2])

    with col1:
        if msg_count > 0:
            st.markdown(f'<div class="chat-controls"><span class="msg-count">\U0001f4ac {msg_count} response{"s" if msg_count != 1 else ""}</span></div>', unsafe_allow_html=True)

    with col2:
        if st.button("\U0001f5d1  New Chat", use_container_width=True,
                     key=f"new_chat_{st.session_state.ai_new_chat_key}"):
            st.session_state.ai_messages = []
            st.session_state.ai_new_chat_key += 1
            st.rerun()

    # ── Chat History ──
    for i, msg in enumerate(st.session_state.ai_messages):
        avatar = "\U0001f9d1" if msg["role"] == "user" else "\U0001f916"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # ── Suggested Questions (only on empty chat) ──
    if not st.session_state.ai_messages:
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-graphic">🤖</div>
            <div class="empty-state-title">AquaBot is Ready</div>
            <div class="empty-state-text">
                I'm analyzing live sensor data from the AquaMonitor system.
                Ask me about water quality parameters, WHO standards,
                trends, or treatment recommendations.
            </div>
            <div class="empty-state-features">
                <span class="empty-state-feature">🌊 6 Parameters</span>
                <span class="empty-state-feature">🌍 WHO Standards</span>
                <span class="empty-state-feature">⚡ Real-time Analysis</span>
                <span class="empty-state-feature">💡 Recommendations</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        suggestions = [
            ("\U0001f30a", "How is the water quality today?"),
            ("\U0001f9ea", "Interpret my pH level"),
            ("\U0001f30d", "What are the WHO standards?"),
            ("\U0001f4a7", "Is the water safe to drink?"),
            ("\U0001f4ca", "Explain the DO level trend"),
        ]
        st.markdown("<div class='suggestions'>", unsafe_allow_html=True)
        cols = st.columns(len(suggestions))
        for ci, (icon, text) in enumerate(suggestions):
            with cols[ci]:
                if st.button(f"{icon} {text}", use_container_width=True,
                             key=f"sug_{ci}"):
                    st.session_state.ai_suggestion = text
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Handle suggestion click ──
    suggestion_text = st.session_state.pop("ai_suggestion", None)
    if suggestion_text:
        prompt = suggestion_text
    else:
        prompt = st.chat_input(
            "Ask about water quality, parameters, or recommendations...",
            key=f"chat_input_{st.session_state.ai_new_chat_key}",
        )

    if prompt and prompt.strip():
        user_msg = prompt.strip()
        st.session_state.ai_messages.append({"role": "user", "content": user_msg})

        with st.chat_message("user", avatar="\U0001f9d1"):
            st.markdown(user_msg, unsafe_allow_html=True)

        api_messages = build_api_messages(st.session_state.ai_messages, readings)

        if not client.is_configured:
            error_msg = (
                "\u26a0\ufe0f **OpenRouter API key not configured.**\n\n"
                "Add `OPENROUTER_API_KEY` to `.streamlit/secrets.toml`. "
                "Get a free key at [openrouter.ai/keys](https://openrouter.ai/keys)."
            )
            st.session_state.ai_messages.append({"role": "assistant", "content": error_msg})
            st.rerun()
# ── Show typing indicator ──
typing_placeholder = st.empty()

typing_placeholder.markdown(f"""
<div class="typing-container">
    <div style="width:32px;"></div>
    <div class="typing-dots">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    </div>
</div>
""", unsafe_allow_html=True)

response = client.ask(user_msg)

with st.chat_message("assistant", avatar="🤖"):
    st.markdown(response, unsafe_allow_html=True)

typing_placeholder.empty()

st.session_state.ai_messages.append({
    "role": "assistant",
    "content": response
})

st.rerun()
