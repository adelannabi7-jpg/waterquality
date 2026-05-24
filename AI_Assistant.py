"""
AquaMonitor AI Assistant — OpenRouter-powered water quality chat.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional
import json

from utils.openrouter_client import OpenRouterClient, build_system_prompt, DEFAULT_MODEL

# ── Theme ─────────────────────────────────────────────────────────

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


def get_latest_readings(df: pd.DataFrame) -> Optional[dict]:
    if df.empty:
        return None
    row = df.iloc[-1]
    ts = row.get("created_at", pd.NaT)
    return {
        "Temperature": round(float(row["Temperature"]), 2) if pd.notna(row["Temperature"]) else "N/A",
        "pH":          round(float(row["pH"]), 3)          if pd.notna(row["pH"])          else "N/A",
        "Turbidity":   round(float(row["Turbidity"]), 2)   if pd.notna(row["Turbidity"])   else "N/A",
        "DO":          round(float(row["DO"]), 2)           if pd.notna(row["DO"])           else "N/A",
        "Conductivity":round(float(row["Conductivity"]), 1) if pd.notna(row["Conductivity"]) else "N/A",
        "TDS":         round(float(row["TDS"]), 1)          if pd.notna(row["TDS"])          else "N/A",
        "timestamp":   ts.strftime("%H:%M:%S %d/%m/%Y")    if pd.notna(ts)                  else "N/A",
    }


def param_status(param: str, value, C: dict):
    if value == "N/A" or (isinstance(value, float) and np.isnan(value)):
        return "N/A", C["muted"], "—"
    t = THRESHOLDS[param]
    lo, hi = t["ideal"]
    if lo <= value <= hi:
        return "Optimal",   C["status_ok"],   "🟢"
    elif t["ok"][0] <= value <= t["ok"][1]:
        return "Attention", C["status_warn"],  "🟡"
    else:
        return "Critique",  C["status_err"],   "🔴"


def inject_css(C: dict):
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
    .ai-header {{ display:flex; align-items:center; justify-content:space-between; padding:14px 22px; margin:8px 0 14px; background:{C["card"]}; border:1px solid {C["border"]}; border-radius:18px; backdrop-filter:blur(24px); box-shadow:0 8px 32px rgba(0,0,0,0.18); animation:fadeDown 0.5s ease both; }}
    .ai-header-left {{ display:flex; align-items:center; gap:14px; }}
    .ai-header-icon {{ width:44px; height:44px; border-radius:14px; background:linear-gradient(135deg,{C["accent"]},{C["accent2"]}); display:flex; align-items:center; justify-content:center; font-size:22px; box-shadow:0 0 24px {C["glow"]}; }}
    .ai-header-title {{ font-family:'JetBrains Mono',monospace; font-size:17px; font-weight:700; color:{C["text"]}; }}
    .ai-header-sub {{ font-size:10px; color:{C["muted"]}; letter-spacing:1.5px; text-transform:uppercase; }}
    .ai-header-right {{ display:flex; align-items:center; gap:10px; }}
    .ai-model-badge {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:{C["accent"]}; background:{C["user_bubble"]}; border:1px solid {C["border"]}; border-radius:20px; padding:4px 12px; }}
    .ai-status-dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; background:{C["status_ok"]}; box-shadow:0 0 8px {C["status_ok"]}; animation:pulse 2s infinite; margin-right:4px; }}
    @keyframes pulse {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:0.5; transform:scale(0.8); }} }}
    .sensor-bar {{ display:flex; flex-wrap:wrap; gap:6px; padding:10px 16px; margin-bottom:16px; background:{C["card"]}; border:1px solid {C["border"]}; border-radius:14px; backdrop-filter:blur(20px); animation:fadeUp 0.5s ease 0.1s both; }}
    .sensor-chip {{ display:inline-flex; align-items:center; gap:5px; font-family:'JetBrains Mono',monospace; font-size:11px; padding:4px 10px; border-radius:10px; background:{C["input_bg"]}; border:1px solid {C["border"]}; color:{C["text"]}; }}
    .sensor-chip .dot {{ width:5px; height:5px; border-radius:50%; display:inline-block; }}
    .sensor-chip .val {{ font-weight:600; }}
    .sensor-chip .unit {{ color:{C["muted"]}; font-size:10px; }}
    [data-testid="stChatMessage"] {{ padding:2px 0 !important; background:transparent !important; border:none !important; animation:msgIn 0.35s ease both; }}
    @keyframes msgIn {{ from {{ opacity:0; transform:translateY(10px) scale(0.98); }} to {{ opacity:1; transform:translateY(0) scale(1); }} }}
    [data-testid="stChatMessageContent"] {{ padding:10px 16px !important; border-radius:4px 16px 16px 16px !important; font-size:14px !important; line-height:1.7 !important; color:{C["text"]} !important; border:1px solid {C["border"]} !important; max-width:88% !important; box-shadow:0 2px 12px rgba(0,0,0,0.10) !important; background:{C["ai_bubble"]} !important; backdrop-filter:blur(12px) !important; }}
    .stChatInputContainer {{ background:{C["card"]} !important; border:1px solid {C["border"]} !important; border-radius:16px !important; backdrop-filter:blur(20px) !important; padding:4px !important; }}
    .stChatInputContainer:focus-within {{ border-color:{C["accent"]} !important; box-shadow:0 0 0 3px {C["glow"]} !important; }}
    .stChatInputContainer button {{ background:linear-gradient(135deg,{C["accent"]},{C["accent2"]}) !important; border:none !important; border-radius:12px !important; color:white !important; font-weight:600 !important; }}
    .suggestions {{ display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 14px; }}
    .empty-state {{ text-align:center; padding:40px 24px 20px; animation:fadeUp 0.6s ease both; }}
    .empty-state-graphic {{ font-size:56px; margin-bottom:10px; display:inline-block; filter:drop-shadow(0 0 20px {C["glow"]}); animation:floatGraphic 4s ease-in-out infinite; }}
    @keyframes floatGraphic {{ 0%,100% {{ transform:translateY(0); }} 50% {{ transform:translateY(-8px); }} }}
    .empty-state-title {{ font-family:'JetBrains Mono',monospace; font-size:19px; font-weight:700; color:{C["text"]}; margin-bottom:6px; }}
    .empty-state-text {{ font-size:13px; color:{C["muted"]}; max-width:460px; margin:0 auto; line-height:1.7; }}
    .typing-dots {{ display:flex; align-items:center; gap:5px; padding:10px 18px; background:{C["ai_bubble"]}; border:1px solid {C["border"]}; border-radius:4px 16px 16px 16px; width:fit-content; }}
    .typing-dot {{ width:8px; height:8px; border-radius:50%; background:{C["accent"]}; animation:typingBounce 1.4s ease-in-out infinite; }}
    .typing-dot:nth-child(2) {{ animation-delay:0.2s; }}
    .typing-dot:nth-child(3) {{ animation-delay:0.4s; }}
    @keyframes typingBounce {{ 0%,60%,100% {{ transform:translateY(0); opacity:0.4; }} 30% {{ transform:translateY(-8px); opacity:1; }} }}
    @keyframes fadeUp {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @keyframes fadeDown {{ from {{ opacity:0; transform:translateY(-12px); }} to {{ opacity:1; transform:translateY(0); }} }}
    </style>
    """, unsafe_allow_html=True)


def render_sensor_bar(readings: Optional[dict], C: dict):
    if not readings:
        return
    chips = ""
    for param in ["Temperature", "pH", "Turbidity", "DO", "Conductivity", "TDS"]:
        val = readings.get(param, "N/A")
        _, color, _ = param_status(param, val, C)
        unit = PARAM_UNITS.get(param, "")
        chips += f"""<div class="sensor-chip">
            <span class="dot" style="background:{color};box-shadow:0 0 6px {color};"></span>
            {PARAM_ICONS.get(param,"")}
            <span class="val">{val}</span>
            <span class="unit">{unit}</span>
        </div>"""
    ts = readings.get("timestamp", "")
    st.markdown(f"""<div class="sensor-bar">{chips}
        <div style="margin-left:auto;font-size:10px;color:{C["muted"]};font-family:'JetBrains Mono',monospace;align-self:center;">⏰ {ts}</div>
    </div>""", unsafe_allow_html=True)


def build_api_messages(chat_history: list, readings: Optional[dict]) -> list:
    system_content = build_system_prompt(readings)
    return [{"role": "system", "content": system_content}] + [
        {"role": m["role"], "content": m["content"]} for m in chat_history
    ]


def render_ai(df: pd.DataFrame, theme: str = "dark"):
    C = _DARK if theme == "dark" else _LIGHT
    inject_css(C)

    # ── Init session state ──
    if "ai_messages"      not in st.session_state: st.session_state.ai_messages      = []
    if "ai_client"        not in st.session_state: st.session_state.ai_client        = OpenRouterClient()
    if "ai_new_chat_key"  not in st.session_state: st.session_state.ai_new_chat_key  = 0
    if "ai_model"         not in st.session_state: st.session_state.ai_model         = DEFAULT_MODEL

    client   = st.session_state.ai_client
    readings = get_latest_readings(df)
    model_name = st.session_state.ai_model.split("/")[-1].split(":")[0].replace("-", " ").title()

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
            <span class="ai-model-badge"><span class="ai-status-dot"></span>{model_name}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    render_sensor_bar(readings, C)

    # ── Controls ──
    msg_count = len([m for m in st.session_state.ai_messages if m["role"] == "assistant"])
    col1, col2 = st.columns([6, 2])
    with col1:
        if msg_count > 0:
            st.markdown(f'<div style="font-size:11px;color:{C["muted"]};font-family:JetBrains Mono,monospace;">💬 {msg_count} response{"s" if msg_count!=1 else ""}</div>', unsafe_allow_html=True)
    with col2:
        if st.button("🗑  New Chat", use_container_width=True, key=f"new_chat_{st.session_state.ai_new_chat_key}"):
            st.session_state.ai_messages = []
            st.session_state.ai_new_chat_key += 1
            st.rerun()

    # ── Chat History ──
    for msg in st.session_state.ai_messages:
        avatar = "🧑" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # ── Empty state + suggestions ──
    if not st.session_state.ai_messages:
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-graphic">🤖</div>
            <div class="empty-state-title">AquaBot is Ready</div>
            <div class="empty-state-text">
                I'm analyzing live sensor data from the AquaMonitor system.
                Ask me about water quality parameters, WHO standards, trends, or treatment recommendations.
            </div>
        </div>""", unsafe_allow_html=True)

        suggestions = [
            ("🌊", "How is the water quality today?"),
            ("🧪", "Interpret my pH level"),
            ("🌍", "What are the WHO standards?"),
            ("💧", "Is the water safe to drink?"),
            ("📊", "Explain the TDS level"),
        ]
        cols = st.columns(len(suggestions))
        for ci, (icon, text) in enumerate(suggestions):
            with cols[ci]:
                if st.button(f"{icon} {text}", use_container_width=True, key=f"sug_{ci}"):
                    st.session_state.ai_suggestion = text
                    st.rerun()

    # ── Handle suggestion / input ──
    suggestion_text = st.session_state.pop("ai_suggestion", None)
    prompt = suggestion_text or st.chat_input(
        "Ask about water quality, parameters, or recommendations...",
        key=f"chat_input_{st.session_state.ai_new_chat_key}",
    )

    if prompt and prompt.strip():
        user_msg = prompt.strip()
        st.session_state.ai_messages.append({"role": "user", "content": user_msg})

        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_msg, unsafe_allow_html=True)

        if not client.is_configured:
            error_msg = "⚠️ **OpenRouter API key not configured.**\n\nAdd `OPENROUTER_API_KEY` to `.streamlit/secrets.toml`. Get a free key at [openrouter.ai/keys](https://openrouter.ai/keys)."
            st.session_state.ai_messages.append({"role": "assistant", "content": error_msg})
            st.rerun()

        api_messages = build_api_messages(st.session_state.ai_messages, readings)

        typing_placeholder = st.empty()
        typing_placeholder.markdown("""
        <div style="padding:2px 0;">
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>""", unsafe_allow_html=True)

        full_response = ""
        stream = client.chat_stream(api_messages, model=st.session_state.ai_model)

        with st.chat_message("assistant", avatar="🤖"):
            container = st.empty()
            for chunk in stream:
                full_response += chunk
                container.markdown(full_response + "\u200b", unsafe_allow_html=True)
            container.markdown(full_response, unsafe_allow_html=True)

        typing_placeholder.empty()
        st.session_state.ai_messages.append({"role": "assistant", "content": full_response})
        st.rerun()
