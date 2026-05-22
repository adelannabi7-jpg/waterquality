import numpy as np
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4
import base64
import requests
from streamlit_autorefresh import st_autorefresh
import json
from data_analysis_page import render_data_analysis
from dashboard_page import render_dashboard
from realtime_page import render_realtime
#from AI_Assistant import render_ai

import firebase_admin
from firebase_admin import credentials, db as firebase_db
import time
import hashlib

# ════════════════════════════════════════════════════════════════
#  NOTIFICATION SYSTEM  —  Data Model · State · UI
# ════════════════════════════════════════════════════════════════

@dataclass
class Notification:
    id: str
    title: str
    message: str
    type: Literal["info", "success", "warning", "error"]
    timestamp: datetime
    read: bool
    action_url: str | None = None

def _relative_time(dt: datetime) -> str:
    diff = datetime.now() - dt
    s = diff.total_seconds()
    if s < 60: return "just now"
    if s < 3600: return f"{int(s // 60)}m ago"
    if s < 86400: return f"{int(s // 3600)}h ago"
    if s < 172800: return "yesterday"
    if s < 604800: return f"{int(s // 86400)}d ago"
    return dt.strftime("%b %d")


def unread_count() -> int:
    return sum(1 for n in st.session_state.notifications if not n.read)

def mark_all_read():
    for n in st.session_state.notifications:
        n.read = True

def mark_read(nid: str):
    for n in st.session_state.notifications:
        if n.id == nid:
            n.read = True
            break

def toggle_panel():
    st.session_state.notifications_panel_open = not st.session_state.notifications_panel_open

data_source = "firebase"  # local | remote | firebase
admin_usr = "admin"
admin_pwd = "1234"

FIREBASE_URL = "https://waterquality-47845-default-rtdb.europe-west1.firebasedatabase.app"

# ── Secure password hashing ──────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """SHA-256 hash for secure comparison (upgrade to bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()

# Pre-hash the admin password once at startup
ADMIN_PWD_HASH = hash_password(admin_pwd)

def verify_credentials(username: str, password: str) -> bool:
    """Rate-limited credential check with hashed comparison."""
    return username == admin_usr and hash_password(password) == ADMIN_PWD_HASH

# Init Firebase only once (skip if using local mode)
if data_source == "firebase" and not firebase_admin._apps:
    cred = credentials.Certificate("./lib/firebase-key.json")
    firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_URL})

if "notifications_panel_open" not in st.session_state:
    st.session_state.notifications_panel_open = False

if "notifications" not in st.session_state:
    st.session_state.notifications = []

# ── Login attempt rate-limiting ──────────────────────────────────────────────
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = 0
if "lockout_until" not in st.session_state:
    st.session_state.lockout_until = 0


PARAM_ICONS = {
    "pH":           "🧪",
    "Temperature":  "🌡️",
    "Turbidity":    "🌫️",
    "TDS":          "💧",
    "Conductivity": "⚡",
    "DO":           "🫧",
}

st_autorefresh(interval=10_000, key="data_refresh")

@st.cache_data(ttl=5)
def load_dataV2():
    try:
        tds_sensor = False
        ph_sensor = False
        temp_sensor = False
        turbidity_sensor = False
        if data_source == "firebase":
            with open("offline-dataset.json", "r", errors="ignore") as f:
                data = json.load(f)
            feeds = data.get("feeds", [])
        elif data_source == "firebase":
            snapshot = firebase_db.reference("/history").get()
            feeds = list(snapshot.values()) if snapshot else []

            sensors = firebase_db.reference("/water").get()

            tds_sensor = sensors.get("tds_sensor", False)
            ph_sensor = sensors.get("ph_sensor", False)
            temp_sensor = sensors.get("temp_sensor", False)
            turbidity_sensor = sensors.get("turbidity_sensor", False)
   
        else:
            url = "https://api.thingspeak.com/channels/3058451/feeds.json"
            response = requests.get(url, timeout=30)
            feeds = response.json().get("feeds", [])

        if not feeds:
            st.warning("No data yet.")
            return pd.DataFrame()

        df = pd.DataFrame(feeds)
        df["tds_sensor"] = tds_sensor
        df["ph_sensor"] = ph_sensor
        df["temp_sensor"] = temp_sensor
        df["turbidity_sensor"] = turbidity_sensor

        for col in ["Temperature", "TDS", "pH", "Conductivity", "Turbidity", "DO"]:
            if col not in df.columns:
                df[col] = 0

       df["Temperature"] = pd.to_numeric(df.get("temperature", 0), errors="coerce")
       df["TDS"] = pd.to_numeric(df.get("tds", 0), errors="coerce")

df["pH"] = pd.to_numeric(df.get("ph", 0), errors="coerce")

df["Turbidity"] = pd.to_numeric(df.get("turbidity", 0), errors="coerce")

df["Conductivity"] = pd.to_numeric(df.get("conductivity", 0), errors="coerce")

df["DO"] = pd.to_numeric(df.get("do", 0), errors="coerce")

        df = df.sort_values("created_at").reset_index(drop=True)
        return df

   
    except Exception as e:
        st.error(f"Data Error: {e}")
        with open("error.log", "a", errors="ignore") as f:
            f.write("load_dataV2: "+str(e)+"\n")
        return pd.DataFrame()


class waterDash:
    def __init__(self):
        pass

    def run(self):
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False
        self.auth()

    def auth(self):
        if st.session_state.logged_in:
            self.dash_page()
        else:
            self.login_page()

    def set_bg(self, local_img):
        with open(local_img, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{encoded}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    def getLocalImg(self, local_img):
        with open(local_img, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()
        return f"data:image/png;base64,{encoded}"

    def set_css(self, theme="dark"):
        is_dark = theme == "dark"

        if is_dark:
            app_bg          = "#0a0f1e"
            sidebar_from    = "rgba(10,20,50,0.55)"
            sidebar_to      = "rgba(5,12,35,0.70)"
            glass_border    = "rgba(100,180,255,0.18)"
            glass_shine     = "rgba(255,255,255,0.06)"
            text_color      = "#e8f0ff"
            text_secondary  = "#7090b8"
            card_bg         = "rgba(15,25,60,0.60)"
            input_bg        = "rgba(20,35,80,0.70)"
            border_color    = "rgba(80,140,255,0.20)"
            accent          = "#38bdf8"
            accent2         = "#818cf8"
            glow            = "rgba(56,189,248,0.25)"
            nav_active_bg   = "rgba(56,189,248,0.18)"
            nav_active_text = "#38bdf8"
            nav_hover_bg    = "rgba(255,255,255,0.07)"
            orb1            = "rgba(56,189,248,0.18)"
            orb2            = "rgba(129,140,248,0.15)"
            orb3            = "rgba(34,211,238,0.12)"
            toggle_bg       = "rgba(56,189,248,0.15)"
            toggle_border   = "#38bdf8"
            toggle_text     = "#38bdf8"
            status_ok_bg    = "rgba(16,185,129,0.15)"
            status_ok_text  = "#34d399"
            status_ok_bdr   = "rgba(52,211,153,0.30)"
            status_err_bg   = "rgba(239,68,68,0.12)"
            status_err_text = "#f87171"
            status_err_bdr  = "rgba(248,113,113,0.30)"
        else:
            app_bg          = "#e8f4fd"
            sidebar_from    = "rgba(255,255,255,0.70)"
            sidebar_to      = "rgba(220,240,255,0.85)"
            glass_border    = "rgba(0,120,220,0.18)"
            glass_shine     = "rgba(255,255,255,0.60)"
            text_color      = "#1a2a4a"
            text_secondary  = "#5070a0"
            card_bg         = "rgba(255,255,255,0.75)"
            input_bg        = "rgba(230,242,255,0.80)"
            border_color    = "rgba(0,100,200,0.15)"
            accent          = "#0077cc"
            accent2         = "#6366f1"
            glow            = "rgba(0,119,204,0.20)"
            nav_active_bg   = "rgba(0,119,204,0.12)"
            nav_active_text = "#0077cc"
            nav_hover_bg    = "rgba(0,80,160,0.07)"
            orb1            = "rgba(0,119,204,0.12)"
            orb2            = "rgba(99,102,241,0.10)"
            orb3            = "rgba(6,182,212,0.10)"
            toggle_bg       = "rgba(0,119,204,0.10)"
            toggle_border   = "#0077cc"
            toggle_text     = "#0077cc"
            status_ok_bg    = "rgba(16,185,129,0.10)"
            status_ok_text  = "#059669"
            status_ok_bdr   = "rgba(5,150,105,0.25)"
            status_err_bg   = "rgba(239,68,68,0.08)"
            status_err_text = "#dc2626"
            status_err_bdr  = "rgba(220,38,38,0.25)"

        st.markdown(f"""
        <style>
        html {{ color-scheme: normal; }}
        .stApp {{
            background: {app_bg} !important;
        }}
        div > button > span > span {{
            color: {text_color}!important;
        }}
        .stMain, .stMainBlockContainer {{
            background-color: transparent !important;
            padding-left: 20px;
            padding-right: 15px;
            padding-top: 5px;
            padding-bottom: 5px;
        }}
        .stAppDeployButton, #MainMenu {{ display: none; }}
        .stAppHeader {{ width: 0px; }}

        body, .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6,
        label, .stRadio label, .stSelectbox label {{
            color: {text_color} !important;
        }}

        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background:
                radial-gradient(ellipse 600px 500px at 15% 20%, {orb1}, transparent 70%),
                radial-gradient(ellipse 500px 400px at 80% 70%, {orb2}, transparent 70%),
                radial-gradient(ellipse 400px 350px at 55% 45%, {orb3}, transparent 70%);
            animation: orbDrift 18s ease-in-out infinite alternate;
            z-index: 0;
        }}
        @keyframes orbDrift {{
            0%   {{ transform: translate(0,0) scale(1); }}
            50%  {{ transform: translate(30px,-20px) scale(1.05); }}
            100% {{ transform: translate(-20px,15px) scale(0.97); }}
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(160deg, {sidebar_from}, {sidebar_to}) !important;
            backdrop-filter: blur(28px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(28px) saturate(180%) !important;
            border-right: 1px solid {glass_border} !important;
            box-shadow: 4px 0 40px rgba(0,0,0,0.18), inset -1px 0 0 {glass_shine} !important;
            position: relative;
            overflow: hidden;
        }}

        [data-testid="stSidebar"]::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, transparent, {accent}, {accent2}, transparent);
            opacity: 0.8;
        }}

        [data-testid="stSidebar"]::after {{
            content: "";
            position: absolute;
            width: 280px;
            height: 280px;
            border-radius: 50%;
            background: radial-gradient(circle, {orb1} 0%, transparent 70%);
            bottom: -80px;
            right: -80px;
            pointer-events: none;
            animation: sideOrb 10s ease-in-out infinite alternate;
        }}
        @keyframes sideOrb {{
            0%   {{ transform: translate(0,0) scale(1); opacity:0.6; }}
            100% {{ transform: translate(-20px,-20px) scale(1.2); opacity:1; }}
        }}

        [data-testid="stSidebarHeader"] {{
            margin-top: 17px;
            height: 0px;
            margin-bottom: 0px;
        }}

        .stSidebar .stMarkdown, .stSidebar p,
        .stSidebar h3, .stSidebar label {{
            color: {text_color} !important;
        }}
        .sidebar-logo {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 18px 16px 14px;
            border-bottom: 1px solid {glass_border};
            margin-bottom: 12px;
        }}
        .sidebar-logo .logo-icon {{
            font-size: 28px;
            filter: drop-shadow(0 0 8px {glow});
        }}
        .sidebar-logo .logo-text {{
            font-size: 15px;
            font-weight: 700;
            color: {text_color} !important;
            line-height: 1.2;
        }}
        .sidebar-logo .logo-sub {{
            font-size: 10px;
            color: {text_secondary} !important;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        .sidebar-section-title {{
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: {text_secondary} !important;
            padding: 10px 4px 4px;
            margin-bottom: 2px;
        }}

        [data-testid="stSidebar"] .stRadio > div {{
            gap: 4px;
        }}
        [data-testid="stSidebar"] .stRadio label {{
            display: flex !important;
            align-items: center !important;
            padding: 9px 14px !important;
            border-radius: 10px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            font-size: 13.5px !important;
            font-weight: 500 !important;
            color: {text_color} !important;
            border: 1px solid transparent !important;
        }}
        [data-testid="stSidebar"] .stRadio label:hover {{
            background: {nav_hover_bg} !important;
            border-color: {glass_border} !important;
        }}
        [data-testid="stSidebar"] .stRadio label[data-checked="true"],
        [data-testid="stSidebar"] .stRadio label[aria-checked="true"] {{
            background: {nav_active_bg} !important;
            border-color: {accent} !important;
            color: {nav_active_text} !important;
            box-shadow: 0 0 12px {glow} !important;
        }}
        [data-testid="stSidebar"] .stRadio input[type="radio"] {{
            display: none !important;
        }}

        [data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            background: {input_bg} !important;
            border: 1px solid {glass_border} !important;
            border-radius: 10px !important;
            color: {text_color} !important;
            backdrop-filter: blur(10px);
        }}

        .status-badge {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 10px;
            font-size: 12.5px;
            font-weight: 600;
            margin-bottom: 6px;
            border: 1px solid;
            backdrop-filter: blur(10px);
        }}
        .status-ok {{
            background: {status_ok_bg};
            color: {status_ok_text};
            border-color: {status_ok_bdr};
        }}
        .status-err {{
            background: {status_err_bg};
            color: {status_err_text};
            border-color: {status_err_bdr};
        }}

        .glass-divider {{
            height: 1px;
            background: linear-gradient(90deg, transparent, {glass_border}, transparent);
            margin: 10px 0;
            border: none;
        }}

        [data-testid="stSidebar"] .stButton > button {{
            width: 100% !important;
            background: {input_bg} !important;
            border: 1px solid {glass_border} !important;
            color: {text_color} !important;
            border-radius: 10px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 8px 14px !important;
            transition: all 0.2s ease !important;
            backdrop-filter: blur(10px);
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background: {nav_hover_bg} !important;
            border-color: {accent} !important;
            box-shadow: 0 0 12px {glow} !important;
            transform: translateY(-1px);
        }}

        [data-testid="stSidebar"] .stButton > button[kind="secondary"],
        .theme-toggle-btn button {{
            background: {toggle_bg} !important;
            border: 1px solid {toggle_border} !important;
            color: {toggle_text} !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px;
            box-shadow: 0 0 14px {glow} !important;
        }}

        div[data-testid="metric-container"] {{
            background: {card_bg} !important;
            border-radius: 14px;
            padding: 14px 18px;
            border: 1px solid {glass_border};
            backdrop-filter: blur(20px);
            box-shadow: 0 4px 24px rgba(0,0,0,0.12);
            transition: transform 0.2s;
        }}
        div[data-testid="metric-container"]:hover {{
            transform: translateY(-2px);
        }}

        .stTextInput input, div[data-baseweb="select"] > div {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border-color: {border_color} !important;
            border-radius: 10px !important;
        }}

        .stDataFrame, .stDataFrame table, [data-testid="stDataFrame"] {{
            background-color: {card_bg} !important;
            color: {text_color} !important;
            border-radius: 12px;
        }}
        .circle {{
            position: absolute;
            border-radius: 50%;
        }}
        .circles {{
            position: absolute;
            height: 270px;
            width: 450px;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 0;
        }}
        @keyframes float {{
            0%   {{ transform: rotateX(0deg) translateY(0px); }}
            50%  {{ transform: rotateX(0deg) translateY(10px) translateX(5px); }}
            100% {{ transform: rotateX(0deg) translateY(0px) translateX(1px); }}
        }}
        .circle-1 {{
            height:300px; width:300px;
            top:100px; left:-50px; opacity:0.8;
            animation: float 6s cubic-bezier(.54,.085,.5,.92) 3.5s infinite alternate;
            background: rgba(0,119,182,0.25);
        }}
        .circle-2 {{
            height:240px; width:240px;
            bottom:40px; right:-100px; opacity:0.8;
            animation: float 6s cubic-bezier(.54,.085,.5,.92) 2s infinite alternate;
            background: rgba(0,180,216,0.25);
        }}
        .circle-3 {{
            height:540px; width:540px;
            top:10px; right:-500px; opacity:0.8;
            animation: float 6s cubic-bezier(.54,.085,.5,.92) 2s infinite alternate;
            background: rgba(72,202,228,0.25);
        }}
        .circle-4 {{
            height:440px; width:440px;
            bottom:-150px; right:500px; opacity:0.8;
            animation: float 6s cubic-bezier(.54,.085,.5,.92) 2s infinite alternate;
            background: rgba(144,224,239,0.20);
        }}

        .st-emotion-cache-r7ut5z h4 {{ padding: 0 !important; }}
        .st-emotion-cache-8ezv7j {{ margin-left: 0 !important; }}

        /* ── Notification System ─────────────────────────────── */
        .notif-bell-wrapper {{
            padding: 4px 16px 6px;
            margin-bottom: 4px;
        }}
        .notif-bell-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 36px; height: 36px;
            border-radius: 10px;
            border: 1px solid {glass_border};
            background: {input_bg};
            color: {text_color};
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            position: relative;
            backdrop-filter: blur(10px);
        }}
        .notif-bell-btn:hover {{
            border-color: {accent};
            box-shadow: 0 0 12px {glow};
            transform: translateY(-1px);
        }}
        .notif-bell-btn svg {{ display: block; }}
        .notif-badge {{
            position: absolute;
            top: -4px; right: -4px;
            min-width: 16px; height: 16px;
            padding: 0 4px;
            border-radius: 8px;
            background: #ef4444;
            color: #fff;
            font-size: 10px;
            font-weight: 700;
            line-height: 16px;
            text-align: center;
            box-shadow: 0 0 8px rgba(239,68,68,0.4);
        }}
        .notif-badge.pulse {{
            animation: notifPulse 2s ease-in-out infinite;
        }}
        @keyframes notifPulse {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.2); opacity: 0.85; }}
        }}
        .notif-panel {{
            margin-top: 8px;
            background: {card_bg};
            backdrop-filter: blur(35px) saturate(150%);
            -webkit-backdrop-filter: blur(35px) saturate(150%);
            border: 1px solid {glass_border};
            border-radius: 14px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.18), 0 0 0 1px {glass_shine} inset;
            max-height: 400px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            animation: notifSlideDown 0.25s ease-out;
        }}
        @keyframes notifSlideDown {{
            from {{ opacity: 0; transform: translateY(-8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .notif-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 14px 8px;
            border-bottom: 1px solid {glass_border};
            flex-shrink: 0;
        }}
        .notif-header-title {{
            font-size: 13px;
            font-weight: 700;
            color: {text_color};
        }}
        .notif-mark-all {{
            font-size: 11px;
            color: {accent};
            text-decoration: none;
            cursor: pointer;
            font-weight: 600;
        }}
        .notif-mark-all:hover {{ text-decoration: underline; }}
        .notif-list {{
            overflow-y: auto;
            padding: 6px 8px;
            flex: 1;
        }}
        .notif-list::-webkit-scrollbar {{ width: 4px; }}
        .notif-list::-webkit-scrollbar-thumb {{
            background: {glass_border};
            border-radius: 4px;
        }}
        .notif-card {{
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 10px;
            border-left: 3px solid transparent;
            background: transparent;
            text-decoration: none;
            color: {text_color};
            transition: background 0.15s ease;
            margin-bottom: 4px;
            position: relative;
        }}
        .notif-card:hover {{ background: {nav_hover_bg}; }}
        .notif-card-unread {{ background: rgba(56,189,248,0.05); }}
        .notif-card-left {{
            flex-shrink: 0;
            width: 24px;
            text-align: center;
            padding-top: 1px;
        }}
        .notif-icon {{ font-size: 15px; }}
        .notif-card-body {{ flex: 1; min-width: 0; }}
        .notif-card-title {{
            font-size: 12.5px;
            font-weight: 600;
            line-height: 1.3;
            margin-bottom: 2px;
            color: {text_color};
        }}
        .notif-card-unread .notif-card-title {{ font-weight: 700; }}
        .notif-card-msg {{
            font-size: 11px;
            line-height: 1.35;
            color: {text_secondary};
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            word-break: break-word;
        }}
        .notif-card-time {{
            font-size: 10px;
            color: {text_secondary};
            margin-top: 3px;
            opacity: 0.7;
        }}
        .notif-dot {{
            width: 7px; height: 7px;
            border-radius: 50%;
            background: {accent};
            flex-shrink: 0;
            margin-top: 6px;
            box-shadow: 0 0 6px {glow};
        }}
        .notif-empty {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 28px 16px;
            text-align: center;
        }}
        .notif-empty-icon {{
            font-size: 32px;
            margin-bottom: 10px;
            opacity: 0.6;
        }}
        .notif-empty-text {{
            font-size: 14px;
            font-weight: 600;
            color: {text_secondary};
        }}
        .notif-overlay {{
            position: fixed;
            inset: 0;
            z-index: 998;
            background: rgba(0,0,0,0.2);
            backdrop-filter: blur(2px);
            -webkit-backdrop-filter: blur(2px);
            cursor: default;
            display: block;
            text-decoration: none;
        }}
        [data-testid="stSidebar"] {{
            position: relative;
            z-index: 1000 !important;
        }}
        </style>
        """, unsafe_allow_html=True)

    # ── Notification UI ──────────────────────────────────────────
    def _handle_notification_params(self):
        params = st.query_params
        action = None
        redirect = None
        if "toggle_panel" in params:
            toggle_panel(); action = "toggle"
        if "close_panel" in params:
            st.session_state.notifications_panel_open = False; action = "close"
        if "mark_all_read" in params:
            mark_all_read(); action = "mark_all"
        if "read_notif" in params:
            nid = params["read_notif"]
            for n in st.session_state.notifications:
                if n.id == nid:
                    n.read = True
                    if n.action_url: redirect = n.action_url
                    break
            action = "read"
        if action:
            for k in list(params.keys()):
                if k in ("toggle_panel","close_panel","mark_all_read","read_notif"):
                    del params[k]
            if redirect:
                st.markdown(f'<meta http-equiv="refresh" content="0; url={redirect}">', unsafe_allow_html=True)
                st.stop()
            st.rerun()

    def _render_notification(self):
      
        self._handle_notification(self.df.iloc[-1])
        html = self._build_notification_panel()
        st.sidebar.markdown(html, unsafe_allow_html=True)

    def _build_notification_panel(self):
        colors = {"info":"#38bdf8","success":"#34d399","warning":"#fbbf24","error":"#f87171"}
        icons  = {"info":"ℹ️","success":"✅","warning":"⚠️","error":"🔴"}
        mark_all = f'<a class="notif-mark-all">Mark all read</a>' if unread_count() > 0 else ""
        html = f'''<div class="notif-panel">
            <div class="notif-header">
                <span class="notif-header-title">Notifications</span>
            </div>
            <div class="notif-list">
        '''
        if not st.session_state.notifications:
            html += '''<div class="notif-empty">
                <span class="notif-empty-icon">🔔</span>
                <span class="notif-empty-text">All caught up! 🎉</span>
            </div>'''
        else:
            for notif in st.session_state.notifications:
                c = colors.get(notif.type, "#38bdf8")
                ic = icons.get(notif.type, "ℹ️")
                uc = " notif-card-unread" if not notif.read else ""
                dot = '<span class="notif-dot"></span>' if not notif.read else ""
                msg = notif.message[:80] + "…" if len(notif.message) > 80 else notif.message
                html += f'''<a class="notif-card{uc}" style="border-left-color:{c};">
                    <div class="notif-card-left"><span class="notif-icon">{ic}</span></div>
                    <div class="notif-card-body">
                        <div class="notif-card-msg">{msg}</div>
                        <!--<div class="notif-card-time">{_relative_time(notif.timestamp)}</div>-->
                    </div>
                    {dot}</a>'''
        html += '''</div></div>'''
        return html

    def _handle_notification(self, df_latest: pd.Series):
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
            self.add_notification("normal", "✅&nbsp; Tous les paramètres sont dans les limites normales.", ntype="success")

        else:
            for level, msg in alerts:
                self.add_notification(level, msg, ntype=level)

    # ────────────────────────────────────────────────────────────
    #  LOGIN PAGE  —  Glassmorphism · Scientific · Premium
    # ────────────────────────────────────────────────────────────
    def login_page(self):
        # ── Global resets for login view ──────────────────────────
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Exo+2:wght@300;400;500;600&display=swap');
        .stApp {
            background: #020c1b !important;
        }
        .stAppHeader, .stAppDeployButton, #MainMenu { display: none !important; }
        .stMain, .stMainBlockContainer {
            padding: 0 !important;
            max-width: 100% !important;
        }
        /* Hide Streamlit column gaps */
        [data-testid="column"] { padding: 0 !important; }
        </style>
        """, unsafe_allow_html=True)

        # ── Determine if locked out ────────────────────────────────
        now = time.time()
        remaining_lock = max(0, int(st.session_state.lockout_until - now))

        # ══════════════════════════════════════════════════════════
        #  FULL-SCREEN LOGIN HTML / CSS
        # ══════════════════════════════════════════════════════════
        st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Exo+2:wght@300;400;500;600&display=swap');
        .login-bg {{
            position: fixed;
            inset: 0;
            z-index: 0;
            background:
                radial-gradient(ellipse 900px 700px at 10% 15%, rgba(0,119,182,0.22) 0%, transparent 65%),
                radial-gradient(ellipse 700px 600px at 85% 80%, rgba(56,189,248,0.15) 0%, transparent 65%),
                radial-gradient(ellipse 500px 500px at 50% 40%, rgba(129,140,248,0.08) 0%, transparent 60%),
                linear-gradient(160deg, #020c1b 0%, #040e22 40%, #060f28 100%);
            overflow: hidden;
        }}
        .login-bg::before {{
            content: "";
            position: absolute;
            inset: 0;
            background-image:
                linear-gradient(rgba(56,189,248,0.04) 1px, transparent 1px),
                linear-gradient(90deg, rgba(56,189,248,0.04) 1px, transparent 1px);
            background-size: 60px 60px;
            animation: gridShift 25s linear infinite;
        }}
        @keyframes gridShift {{
            0%   {{ transform: translate(0,0); }}
            100% {{ transform: translate(60px,60px); }}
        }}
        .orb {{
            position: absolute;
            border-radius: 50%;
            filter: blur(60px);
            pointer-events: none;
            animation: orbFloat var(--dur, 14s) ease-in-out infinite alternate;
        }}
        .orb-1 {{ width:520px; height:520px; top:-120px; left:-80px;
                  background: radial-gradient(circle, rgba(0,119,182,0.28), transparent 70%);
                  --dur: 16s; }}
        .orb-2 {{ width:420px; height:420px; bottom:-80px; right:-60px;
                  background: radial-gradient(circle, rgba(56,189,248,0.22), transparent 70%);
                  --dur: 12s; animation-delay: -4s; }}
        .orb-3 {{ width:320px; height:320px; top:40%; left:55%;
                  background: radial-gradient(circle, rgba(129,140,248,0.16), transparent 70%);
                  --dur: 18s; animation-delay: -8s; }}
        @keyframes orbFloat {{
            0%   {{ transform: translate(0,0) scale(1); }}
            50%  {{ transform: translate(25px,-20px) scale(1.06); }}
            100% {{ transform: translate(-15px,18px) scale(0.96); }}
        }}
        .particle {{
            position: absolute;
            border-radius: 50%;
            background: rgba(56,189,248,0.6);
            animation: particleDrift var(--pd, 20s) linear infinite;
            opacity: var(--po, 0.4);
        }}
        @keyframes particleDrift {{
            0%   {{ transform: translateY(100vh) translateX(0); opacity: 0; }}
            10%  {{ opacity: var(--po, 0.4); }}
            90%  {{ opacity: var(--po, 0.4); }}
            100% {{ transform: translateY(-100px) translateX(var(--px, 30px)); opacity: 0; }}
        }}
        .login-wrapper {{
            position: fixed;
            inset: 0;
            z-index: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .login-card {{
            margin-bottom: 352px;
            width: 100%;
            max-width: 440px;
            background: rgba(8,18,48,0.65);
            backdrop-filter: blur(40px) saturate(180%);
            -webkit-backdrop-filter: blur(40px) saturate(180%);
            border-radius: 28px;
            border: 1px solid rgba(56,189,248,0.20);
            box-shadow:
                0 32px 80px rgba(0,0,0,0.50),
                0 0 0 1px rgba(255,255,255,0.04) inset,
                0 1px 0 rgba(255,255,255,0.08) inset;
            padding: 42px 42px 36px;
            position: relative;
            overflow: hidden;
            animation: cardEnter 0.7s cubic-bezier(0.22,1,0.36,1) both;
        }}
        @keyframes cardEnter {{
            from {{ opacity:0; transform: translateY(30px) scale(0.96); }}
            to   {{ opacity:1; transform: translateY(0)    scale(1);    }}
        }}
        .login-card::before {{
            content: "";
            position: absolute;
            top: 0; left: 10%; right: 10%;
            height: 2px;
            background: linear-gradient(90deg, transparent, #38bdf8, #818cf8, transparent);
            opacity: 0.9;
            border-radius: 2px;
        }}
        .login-card::after {{
            content: "";
            position: absolute;
            top: -60px; right: -60px;
            width: 200px; height: 200px;
            background: radial-gradient(circle, rgba(56,189,248,0.12), transparent 70%);
            pointer-events: none;
        }}
        .logo-section {{
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-bottom: 32px;
            animation: fadeUp 0.6s ease 0.15s both;
        }}
        @keyframes fadeUp {{
            from {{ opacity:0; transform: translateY(15px); }}
            to   {{ opacity:1; transform: translateY(0); }}
        }}
        .logo-ring {{
            width: 80px; height: 80px;
            border-radius: 50%;
            background: rgba(56,189,248,0.10);
            border: 1.5px solid rgba(56,189,248,0.30);
            display: flex; align-items: center; justify-content: center;
            margin-bottom: 14px;
            box-shadow: 0 0 28px rgba(56,189,248,0.18), inset 0 0 20px rgba(56,189,248,0.08);
            position: relative;
            animation: ringPulse 3s ease-in-out infinite;
        }}
        @keyframes ringPulse {{
            0%, 100% {{ box-shadow: 0 0 28px rgba(56,189,248,0.18), inset 0 0 20px rgba(56,189,248,0.08); }}
            50%       {{ box-shadow: 0 0 44px rgba(56,189,248,0.32), inset 0 0 28px rgba(56,189,248,0.14); }}
        }}
        .logo-ring::before {{
            content: "";
            position: absolute;
            inset: -6px;
            border-radius: 50%;
            border: 1px dashed rgba(56,189,248,0.20);
            animation: ringRotate 12s linear infinite;
        }}
        @keyframes ringRotate {{
            to {{ transform: rotate(360deg); }}
        }}
        .logo-title {{
            font-family: 'Rajdhani', sans-serif;
            font-size: 26px;
            font-weight: 700;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: #e8f0ff;
            line-height: 1;
        }}
        .logo-title span {{
            color: #38bdf8;
        }}
        .logo-subtitle {{
            font-family: 'Exo 2', sans-serif;
            font-size: 10px;
            font-weight: 400;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: rgba(112,144,184,0.85);
            margin-top: 5px;
        }}
        .login-heading {{
            font-family: 'Rajdhani', sans-serif;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: rgba(112,144,184,0.75);
            text-align: center;
            margin-bottom: 26px;
            animation: fadeUp 0.6s ease 0.25s both;
        }}
        .login-divider {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 0 0 22px;
            animation: fadeUp 0.6s ease 0.30s both;
        }}
        .login-divider-line {{
            flex: 1;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(56,189,248,0.20), transparent);
        }}
        .login-divider-dot {{
            width: 6px; height: 6px;
            border-radius: 50%;
            background: #38bdf8;
            box-shadow: 0 0 8px rgba(56,189,248,0.6);
        }}
        .login-info-strip {{
            display: flex;
            gap: 6px;
            margin-bottom: 26px;
            animation: fadeUp 0.6s ease 0.35s both;
        }}
        .info-chip {{
            flex: 1;
            background: rgba(56,189,248,0.07);
            border: 1px solid rgba(56,189,248,0.14);
            border-radius: 8px;
            padding: 7px 10px;
            text-align: center;
        }}
        .info-chip-icon {{ font-size: 14px; display: block; }}
        .info-chip-label {{
            font-family: 'Exo 2', sans-serif;
            font-size: 9px;
            font-weight: 500;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: rgba(56,189,248,0.70);
            display: block;
            margin-top: 3px;
        }}
        .login-footer {{
            text-align: center;
            margin-top: 28px;
            padding-top: 18px;
            border-top: 1px solid rgba(56,189,248,0.10);
            animation: fadeUp 0.6s ease 0.55s both;
        }}
        .login-footer-name {{
            font-family: 'Rajdhani', sans-serif;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 1px;
            color: rgba(56,189,248,0.80);
        }}
        .login-footer-sub {{
            font-family: 'Exo 2', sans-serif;
            font-size: 10px;
            color: rgba(112,144,184,0.60);
            letter-spacing: 0.5px;
            margin-top: 3px;
        }}
        .stTextInput > label {{
            font-family: 'Exo 2', sans-serif !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            letter-spacing: 2.5px !important;
            text-transform: uppercase !important;
            color: rgba(112,144,184,0.85) !important;
        }}
        .stTextInput input {{
            background: rgba(10,25,65,0.70) !important;
            border: 1px solid rgba(56,189,248,0.22) !important;
            border-radius: 12px !important;
            color: #e8f0ff !important;
            font-family: 'Exo 2', sans-serif !important;
            font-size: 14px !important;
            padding: 12px 16px !important;
            transition: border-color 0.25s, box-shadow 0.25s !important;
        }}
        .stTextInput input:focus {{
            border-color: rgba(56,189,248,0.55) !important;
            box-shadow: 0 0 0 3px rgba(56,189,248,0.10), 0 0 18px rgba(56,189,248,0.12) !important;
            outline: none !important;
        }}
        .stTextInput input::placeholder {{
            color: rgba(112,144,184,0.45) !important;
        }}
        .stButton > button {{
            width: 100% !important;
            background: linear-gradient(135deg, rgba(0,119,182,0.85), rgba(56,189,248,0.75)) !important;
            border: 1px solid rgba(56,189,248,0.40) !important;
            border-radius: 12px !important;
            color: #ffffff !important;
            font-family: 'Rajdhani', sans-serif !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            letter-spacing: 3px !important;
            text-transform: uppercase !important;
            padding: 13px !important;
            margin-top: 8px !important;
            transition: all 0.25s ease !important;
            box-shadow: 0 4px 24px rgba(56,189,248,0.20), inset 0 1px 0 rgba(255,255,255,0.12) !important;
            cursor: pointer !important;
        }}
        .stButton > button:hover {{
            background: linear-gradient(135deg, rgba(0,139,212,0.95), rgba(56,189,248,0.90)) !important;
            box-shadow: 0 8px 36px rgba(56,189,248,0.35), inset 0 1px 0 rgba(255,255,255,0.18) !important;
            transform: translateY(-2px) !important;
            border-color: rgba(56,189,248,0.60) !important;
        }}
        .stButton > button:active {{
            transform: translateY(0px) !important;
        }}
        </style>
        <div class="login-bg">
            <div class="orb orb-1"></div>
            <div class="orb orb-2"></div>
            <div class="orb orb-3"></div>
            <div class="particle" style="width:3px;height:3px;left:12%;--pd:22s;--po:0.35;--px:40px;animation-delay:-5s;"></div>
            <div class="particle" style="width:2px;height:2px;left:28%;--pd:18s;--po:0.25;--px:-30px;animation-delay:-12s;"></div>
            <div class="particle" style="width:4px;height:4px;left:45%;--pd:26s;--po:0.30;--px:20px;animation-delay:-2s;"></div>
            <div class="particle" style="width:2px;height:2px;left:62%;--pd:20s;--po:0.40;--px:-50px;animation-delay:-9s;"></div>
            <div class="particle" style="width:3px;height:3px;left:78%;--pd:24s;--po:0.28;--px:35px;animation-delay:-16s;"></div>
            <div class="particle" style="width:2px;height:2px;left:88%;--pd:19s;--po:0.32;--px:-20px;animation-delay:-7s;"></div>
        </div>           
        <div class="login-wrapper" style="margin-bottom: 385px;">
          <div>
            <div class="logo-section">
              <div class="logo-ring">
                <svg width="42" height="42" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M21 6 C21 6 9 18 9 25 C9 32.18 14.37 37 21 37 C27.63 37 33 32.18 33 25 C33 18 21 6 21 6Z"
                        fill="url(#dropGrad)" stroke="rgba(56,189,248,0.5)" stroke-width="0.8"/>           
                  <circle cx="21" cy="25" r="4" fill="none" stroke="rgba(56,189,248,0.90)" stroke-width="1.2"/>
                  <circle cx="21" cy="25" r="7.5" fill="none" stroke="rgba(56,189,248,0.45)" stroke-width="0.8" stroke-dasharray="3 2"/>
                  <circle cx="21" cy="25" r="2" fill="#38bdf8"/>
                  <ellipse cx="17.5" cy="17" rx="2.5" ry="4" fill="rgba(255,255,255,0.22)" transform="rotate(-20 17.5 17)"/>
                  <defs>
                    <linearGradient id="dropGrad" x1="21" y1="6" x2="21" y2="37" gradientUnits="userSpaceOnUse">
                      <stop offset="0%"   stop-color="rgba(56,189,248,0.75)"/>
                      <stop offset="100%" stop-color="rgba(0,80,160,0.60)"/>
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              <div class="logo-title">Aqua<span>Monitor</span></div>
              <div class="logo-subtitle">Water Quality Intelligence System</div>
            </div>
            <div class="login-divider">
              <div class="login-divider-line"></div>
              <div class="login-divider-dot"></div>
              <div class="login-divider-line"></div>
            </div>
            <div class="login-heading">Secure Access Portal</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Streamlit form inputs (rendered over the card via z-index) ──
        # We use a transparent overlay trick: push inputs into position
        st.markdown("""
        <style>
        .stMain .stMainBlockContainer {
            position: relative;
            z-index: 20;
        } 
        section.main > div {
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 100vh;
        }
        </style>
        """, unsafe_allow_html=True)

        # Spacer + centered column layout
        st.markdown("<div style='height:260px;margin-top:40px;'></div>", unsafe_allow_html=True)

        _, col, _ = st.columns([1, 1.2, 1])

        with col:
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
                key="login_user",
                
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
                key="login_pass",
            )

            if st.button("AUTHENTICATE  →", key="login_btn"):
                if verify_credentials(username.strip(), password):
                    # Success
                    st.session_state.logged_in = True
                    st.session_state.login_attempts = 0
                    st.session_state.lockout_until = 0
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    attempts_left = max(0, 5 - st.session_state.login_attempts)

                    if st.session_state.login_attempts >= 5:
                        # Lock for 60 seconds
                        st.session_state.lockout_until = time.time() + 60
                        st.session_state.login_attempts = 0
                        st.rerun()
                    else:
                        st.toast(f"⚠️ Invalid credentials — {attempts_left} attempt{'s' if attempts_left != 1 else ''} remaining")
                      

        # ── Footer (always visible) ──────────────────────────────
        st.markdown("""
        <style>
        .aq-footer {
            position: fixed;
            left: 0; bottom: 0; width: 100%;
            background: rgba(2,12,27,0.82);
            backdrop-filter: blur(12px);
            border-top: 1px solid rgba(56,189,248,0.10);
            text-align: center;
            padding: 10px 0;
            z-index: 100;
        }
        .aq-footer-name {
            font-family: 'Rajdhani', sans-serif;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 1px;
            color: rgba(56,189,248,0.75);
        }
        .aq-footer-sub {
            font-family: 'Exo 2', sans-serif;
            font-size: 10px;
            color: rgba(112,144,184,0.55);
            letter-spacing: 0.5px;
            margin-top: 2px;
        }
        </style>
        <div class="aq-footer">
            <div class="aq-footer-name">Developed by Ourabah Sanaa & ANNABI ADEL</div>
            <div class="aq-footer-sub">Master – Industrial Computer Science &nbsp;|&nbsp; University of Oran 1</div>
        </div>
        """, unsafe_allow_html=True)

    # ────────────────────────────────────────────────────────────
    #  HELPER UTILITIES
    # ────────────────────────────────────────────────────────────
    def add_notification(self, title: str, message: str = "", ntype: Literal["info","success","warning","error"] = "info", action_url: str | None = None):
        st.session_state.notifications.append(Notification(
            id=str(uuid4()), title=title, message=message or title,
            type=ntype, timestamp=datetime.now(), read=False, action_url=action_url,
        ))

    def get_base64(self, file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()

    # ────────────────────────────────────────────────────────────
    #  DASHBOARD PAGE
    # ────────────────────────────────────────────────────────────
    def dash_page(self):
        
        if "notifications_panel_open" not in st.session_state:
            st.session_state.notifications_panel_open = False
        if "theme" not in st.session_state:
            st.session_state.theme = "dark"

        self.set_css(st.session_state.theme)
        self._handle_notification_params()

        self.df = load_dataV2()

        if not self.df.empty:
            self.time         = self.df["created_at"].iloc[-1]
            self.temperature  = self.df["Temperature"].iloc[-1]
            self.ph           = self.df["pH"].iloc[-1]
            self.turbidity    = self.df["Turbidity"].iloc[-1]
            self.tds          = self.df["TDS"].iloc[-1]
            self.conductivity = self.df["Conductivity"].iloc[-1]
            self.do           = self.df["DO"].iloc[-1]
        else:
            st.markdown("<h3 style='text-align:center; color:#f87171;'>No data available</h3>", unsafe_allow_html=True)
            return

        st.set_page_config(
            page_title="Water Quality Monitoring",
            page_icon="💧",
            layout="wide",
            initial_sidebar_state="auto",
        )

        is_dark = st.session_state.theme == "dark"

        st.sidebar.markdown(f"""
        <div class="sidebar-logo">
            <span class="logo-icon">💧</span>
            <div>
                <div class="logo-text">AquaMonitor</div>
                <div class="logo-sub">Water Quality System</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


        menu_option = st.sidebar.radio(
            "Navigate to",
            ["🏠 Dashboard", "📡 Real-Time Data", "📊 Data Analysis", "🤖 AI Assistant"],
            index=0,
            label_visibility="collapsed"
        )

        self._render_notification()

        st.sidebar.markdown('<hr class="glass-divider">', unsafe_allow_html=True)

        st.sidebar.markdown('<div class="sidebar-section-title">System Status</div>', unsafe_allow_html=True)
        
        activesens = 0

        if (self.df["ph_sensor"] == True).any():
            activesens +=1
        if (self.df["tds_sensor"] == True).any():
            activesens +=1
        if (self.df["turbidity_sensor"] == True).any():
            activesens +=1
        if (self.df["temp_sensor"] == True).any():
            activesens +=1
        
        st.sidebar.markdown(f"""
        <div class="status-badge status-ok">🟢  Online — Connected</div>
        <div class="status-badge status-err">🔴  Sensors: {activesens} active</div>
        """, unsafe_allow_html=True)

        st.sidebar.markdown('<hr class="glass-divider">', unsafe_allow_html=True)

        theme_label = "☀️  Switch to Light Mode" if is_dark else "🌙  Switch to Dark Mode"
        st.sidebar.markdown('<div class="sidebar-section-title">Appearance</div>', unsafe_allow_html=True)
        if st.sidebar.button(theme_label, key="theme_toggle"):
            st.session_state.theme = "light" if is_dark else "dark"
            st.rerun()

        st.sidebar.markdown('<hr class="glass-divider">', unsafe_allow_html=True)

        if st.sidebar.button("🚪  Logout", key="logout"):
            st.session_state.notifications_panel_open = False
            st.session_state.logged_in = False
            st.rerun()

        st.sidebar.markdown(f"""
        <div style="margin-top:18px; text-align:center; font-size:10px;
                    color: {'#5070a0' if not is_dark else '#4a6080'}; padding: 0 8px;">
            AquaMonitor v2.0<br>
            University of Oran 1<br>
            © 2026 Ourabah Sanaa & ANNABI ADEL
        </div>
        """, unsafe_allow_html=True)

        menu_clean = menu_option.strip()

        if "Dashboard" in menu_clean:
            st.session_state.notifications = []
            render_dashboard(self.df, st.session_state.theme)
        elif "Real-Time" in menu_clean:
            st.session_state.notifications = []
            render_realtime(self.df, st.session_state.theme)
        elif "Data Analysis" in menu_clean:
            st.session_state.notifications = []
            render_data_analysis(self.df, st.session_state.theme)
        elif "AI Assistant" in menu_clean:
            st.warning("AI Assistant disabled on cloud version")

if __name__ == "__main__":
    wDash = waterDash()
    wDash.run()
