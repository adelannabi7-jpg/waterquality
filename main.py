import numpy as np
import streamlit as st
import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4
import base64
import requests
from streamlit_autorefresh import st_autorefresh
import json
import time
import hashlib
import os
from data_analysis_page import render_data_analysis
from dashboard_page import render_dashboard
from realtime_page import render_realtime
from AI_Assistant import render_ai

# ── MUST BE FIRST st.* CALL ─────────────────────────────────────
st.set_page_config(
    page_title="Water Quality Monitoring",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="auto",
)

# ════════════════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════════════════
data_source  = "firebase"
admin_usr    = "admin"
admin_pwd    = "1234"
FIREBASE_URL = "https://waterquality-47845-default-rtdb.europe-west1.firebasedatabase.app"

# ════════════════════════════════════════════════════════════════
#  FIREBASE REST API  —  aucune clé nécessaire
# ════════════════════════════════════════════════════════════════
def firebase_get(path: str):
    """Lit un nœud Firebase via l'API REST publique (règles .read = true)."""
    url = f"{FIREBASE_URL}{path}.json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

# ════════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════════
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

ADMIN_PWD_HASH = hash_password(admin_pwd)

def verify_credentials(username: str, password: str) -> bool:
    return username == admin_usr and hash_password(password) == ADMIN_PWD_HASH

# ════════════════════════════════════════════════════════════════
#  NOTIFICATION SYSTEM
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
    if s < 60:     return "just now"
    if s < 3600:   return f"{int(s//60)}m ago"
    if s < 86400:  return f"{int(s//3600)}h ago"
    if s < 172800: return "yesterday"
    if s < 604800: return f"{int(s//86400)}d ago"
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

PARAM_ICONS = {
    "pH":           "🧪",
    "Temperature":  "🌡️",
    "Turbidity":    "🌫️",
    "TDS":          "💧",
    "Conductivity": "⚡",
    "DO":           "🫧",
}

# ── Session state init ───────────────────────────────────────────
if "notifications_panel_open" not in st.session_state:
    st.session_state.notifications_panel_open = False
if "notifications" not in st.session_state:
    st.session_state.notifications = []
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = 0
if "lockout_until" not in st.session_state:
    st.session_state.lockout_until = 0



# ════════════════════════════════════════════════════════════════
#  LOAD DATA — Firebase REST (pas de clé de service)
# ════════════════════════════════════════════════════════════════

def load_dataV2():
    try:
        tds_sensor = ph_sensor = temp_sensor = turbidity_sensor = False
        feeds = []

        if data_source == "local":
            with open("offline-dataset.json", "r", errors="ignore") as f:
                data = json.load(f)
            feeds = data.get("feeds", [])

        elif data_source == "firebase":
            # -- données live --
            sensors = firebase_get("/water")
            if sensors and isinstance(sensors, dict):
                tds_sensor       = sensors.get("tds_sensor", False)
                ph_sensor        = sensors.get("ph_sensor", False)
                temp_sensor      = sensors.get("temp_sensor", False)
                turbidity_sensor = sensors.get("turbidity_sensor", False)

            # -- historique --
            history = firebase_get("/history")
            if history and isinstance(history, dict):
                for key, val in history.items():
                    if not isinstance(val, dict):
                        continue
                    feeds.append({
                        "created_at":   val.get("created_at", key.replace("_", "T")),
                        "temperature":  val.get("temperature", 0),
                        "ph":           val.get("ph", 0),
                        "tds":          val.get("tds", 0),
                        "turbidity":    val.get("turbidity", 0),
                        "conductivity": val.get("conductivity", 0),
                        "do":           val.get("do", 0),
                    })
            elif sensors and isinstance(sensors, dict):
                # pas d'historique → mesure live uniquement
                feeds = [{
                    "created_at":   sensors.get("created_at", ""),
                    "temperature":  sensors.get("temperature", 0),
                    "ph":           sensors.get("ph", 0),
                    "tds":          sensors.get("tds", 0),
                    "turbidity":    sensors.get("turbidity", 0),
                    "conductivity": sensors.get("conductivity", 0),
                    "do":           sensors.get("do", 0),
                }]

        else:
            url = "https://api.thingspeak.com/channels/3058451/feeds.json"
            feeds = requests.get(url, timeout=30).json().get("feeds", [])

        if not feeds:
            st.warning("No data yet.")
            return pd.DataFrame()

        df = pd.DataFrame(feeds)
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True).dt.tz_localize(None)
        df = df.sort_values("created_at").reset_index(drop=True)

        df["tds_sensor"]       = tds_sensor
        df["ph_sensor"]        = ph_sensor
        df["temp_sensor"]      = temp_sensor
        df["turbidity_sensor"] = turbidity_sensor

        df["Temperature"]  = pd.to_numeric(df.get("temperature",  0), errors="coerce")
        df["TDS"]          = pd.to_numeric(df.get("tds",          0), errors="coerce")
        df["pH"]           = pd.to_numeric(df.get("ph",           0), errors="coerce")
        df["Turbidity"]    = pd.to_numeric(df.get("turbidity",    0), errors="coerce")
        df["Conductivity"] = pd.to_numeric(df.get("conductivity", 0), errors="coerce")
        df["DO"]           = pd.to_numeric(df.get("do",           0), errors="coerce")

        return df

    except Exception as e:
        st.error(f"Data Error: {e}")
        with open("error.log", "a", errors="ignore") as f:
            f.write(f"load_dataV2: {e}\n")
        return pd.DataFrame()


# ════════════════════════════════════════════════════════════════
#  MAIN CLASS
# ════════════════════════════════════════════════════════════════
class waterDash:
    def __init__(self): pass

    def run(self):
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False
        self.auth()

    def auth(self):
        if st.session_state.logged_in:
            self.dash_page()
        else:
            self.login_page()

    def set_css(self, theme="dark"):
        is_dark = theme == "dark"
        if is_dark:
            app_bg="#0a0f1e"; sidebar_from="rgba(10,20,50,0.55)"; sidebar_to="rgba(5,12,35,0.70)"
            glass_border="rgba(100,180,255,0.18)"; glass_shine="rgba(255,255,255,0.06)"
            text_color="#e8f0ff"; text_secondary="#7090b8"; card_bg="rgba(15,25,60,0.60)"
            input_bg="rgba(20,35,80,0.70)"; border_color="rgba(80,140,255,0.20)"
            accent="#38bdf8"; accent2="#818cf8"; glow="rgba(56,189,248,0.25)"
            nav_active_bg="rgba(56,189,248,0.18)"; nav_active_text="#38bdf8"
            nav_hover_bg="rgba(255,255,255,0.07)"; orb1="rgba(56,189,248,0.18)"
            orb2="rgba(129,140,248,0.15)"; orb3="rgba(34,211,238,0.12)"
            toggle_bg="rgba(56,189,248,0.15)"; toggle_border="#38bdf8"; toggle_text="#38bdf8"
            status_ok_bg="rgba(16,185,129,0.15)"; status_ok_text="#34d399"; status_ok_bdr="rgba(52,211,153,0.30)"
            status_err_bg="rgba(239,68,68,0.12)"; status_err_text="#f87171"; status_err_bdr="rgba(248,113,113,0.30)"
        else:
            app_bg="#e8f4fd"; sidebar_from="rgba(255,255,255,0.70)"; sidebar_to="rgba(220,240,255,0.85)"
            glass_border="rgba(0,120,220,0.18)"; glass_shine="rgba(255,255,255,0.60)"
            text_color="#1a2a4a"; text_secondary="#5070a0"; card_bg="rgba(255,255,255,0.75)"
            input_bg="rgba(230,242,255,0.80)"; border_color="rgba(0,100,200,0.15)"
            accent="#0077cc"; accent2="#6366f1"; glow="rgba(0,119,204,0.20)"
            nav_active_bg="rgba(0,119,204,0.12)"; nav_active_text="#0077cc"
            nav_hover_bg="rgba(0,80,160,0.07)"; orb1="rgba(0,119,204,0.12)"
            orb2="rgba(99,102,241,0.10)"; orb3="rgba(6,182,212,0.10)"
            toggle_bg="rgba(0,119,204,0.10)"; toggle_border="#0077cc"; toggle_text="#0077cc"
            status_ok_bg="rgba(16,185,129,0.10)"; status_ok_text="#059669"; status_ok_bdr="rgba(5,150,105,0.25)"
            status_err_bg="rgba(239,68,68,0.08)"; status_err_text="#dc2626"; status_err_bdr="rgba(220,38,38,0.25)"

        st.markdown(f"""<style>
        html {{ color-scheme: normal; }}
        .stApp {{ background: {app_bg} !important; }}
        div > button > span > span {{ color: {text_color}!important; }}
        .stMain, .stMainBlockContainer {{ background-color: transparent !important; padding-left:20px; padding-right:15px; padding-top:5px; padding-bottom:5px; }}
        .stAppDeployButton, #MainMenu {{ display: none; }}
        .stAppHeader {{ width: 0px; }}
        body, .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label, .stRadio label, .stSelectbox label {{ color: {text_color} !important; }}
        .stApp::before {{ content:""; position:fixed; inset:0; pointer-events:none;
            background: radial-gradient(ellipse 600px 500px at 15% 20%, {orb1}, transparent 70%),
                        radial-gradient(ellipse 500px 400px at 80% 70%, {orb2}, transparent 70%),
                        radial-gradient(ellipse 400px 350px at 55% 45%, {orb3}, transparent 70%);
            animation: orbDrift 18s ease-in-out infinite alternate; z-index:0; }}
        @keyframes orbDrift {{ 0% {{ transform:translate(0,0) scale(1); }} 50% {{ transform:translate(30px,-20px) scale(1.05); }} 100% {{ transform:translate(-20px,15px) scale(0.97); }} }}
        [data-testid="stSidebar"] {{ background: linear-gradient(160deg,{sidebar_from},{sidebar_to}) !important; backdrop-filter:blur(28px) saturate(180%) !important; -webkit-backdrop-filter:blur(28px) saturate(180%) !important; border-right:1px solid {glass_border} !important; box-shadow:4px 0 40px rgba(0,0,0,0.18),inset -1px 0 0 {glass_shine} !important; position:relative; overflow:hidden; }}
        [data-testid="stSidebar"]::before {{ content:""; position:absolute; top:0; left:0; right:0; height:3px; background:linear-gradient(90deg,transparent,{accent},{accent2},transparent); opacity:0.8; }}
        [data-testid="stSidebarHeader"] {{ margin-top:17px; height:0px; margin-bottom:0px; }}
        .stSidebar .stMarkdown, .stSidebar p, .stSidebar h3, .stSidebar label {{ color:{text_color} !important; }}
        .sidebar-logo {{ display:flex; align-items:center; gap:10px; padding:18px 16px 14px; border-bottom:1px solid {glass_border}; margin-bottom:12px; }}
        .sidebar-logo .logo-icon {{ font-size:28px; filter:drop-shadow(0 0 8px {glow}); }}
        .sidebar-logo .logo-text {{ font-size:15px; font-weight:700; color:{text_color} !important; line-height:1.2; }}
        .sidebar-logo .logo-sub {{ font-size:10px; color:{text_secondary} !important; letter-spacing:1px; text-transform:uppercase; }}
        .sidebar-section-title {{ font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{text_secondary} !important; padding:10px 4px 4px; margin-bottom:2px; }}
        [data-testid="stSidebar"] .stRadio > div {{ gap:4px; }}
        [data-testid="stSidebar"] .stRadio label {{ display:flex !important; align-items:center !important; padding:9px 14px !important; border-radius:10px !important; cursor:pointer !important; transition:all 0.2s ease !important; font-size:13.5px !important; font-weight:500 !important; color:{text_color} !important; border:1px solid transparent !important; }}
        [data-testid="stSidebar"] .stRadio label:hover {{ background:{nav_hover_bg} !important; border-color:{glass_border} !important; }}
        [data-testid="stSidebar"] .stRadio label[data-checked="true"], [data-testid="stSidebar"] .stRadio label[aria-checked="true"] {{ background:{nav_active_bg} !important; border-color:{accent} !important; color:{nav_active_text} !important; box-shadow:0 0 12px {glow} !important; }}
        [data-testid="stSidebar"] .stRadio input[type="radio"] {{ display:none !important; }}
        [data-testid="stSidebar"] div[data-baseweb="select"] > div {{ background:{input_bg} !important; border:1px solid {glass_border} !important; border-radius:10px !important; color:{text_color} !important; backdrop-filter:blur(10px); }}
        .status-badge {{ display:flex; align-items:center; gap:8px; padding:8px 12px; border-radius:10px; font-size:12.5px; font-weight:600; margin-bottom:6px; border:1px solid; backdrop-filter:blur(10px); }}
        .status-ok {{ background:{status_ok_bg}; color:{status_ok_text}; border-color:{status_ok_bdr}; }}
        .status-err {{ background:{status_err_bg}; color:{status_err_text}; border-color:{status_err_bdr}; }}
        .glass-divider {{ height:1px; background:linear-gradient(90deg,transparent,{glass_border},transparent); margin:10px 0; border:none; }}
        [data-testid="stSidebar"] .stButton > button {{ width:100% !important; background:{input_bg} !important; border:1px solid {glass_border} !important; color:{text_color} !important; border-radius:10px !important; font-size:13px !important; font-weight:500 !important; padding:8px 14px !important; transition:all 0.2s ease !important; backdrop-filter:blur(10px); }}
        [data-testid="stSidebar"] .stButton > button:hover {{ background:{nav_hover_bg} !important; border-color:{accent} !important; box-shadow:0 0 12px {glow} !important; transform:translateY(-1px); }}
        div[data-testid="metric-container"] {{ background:{card_bg} !important; border-radius:14px; padding:14px 18px; border:1px solid {glass_border}; backdrop-filter:blur(20px); box-shadow:0 4px 24px rgba(0,0,0,0.12); transition:transform 0.2s; }}
        div[data-testid="metric-container"]:hover {{ transform:translateY(-2px); }}
        .stTextInput input, div[data-baseweb="select"] > div {{ background-color:{input_bg} !important; color:{text_color} !important; border-color:{border_color} !important; border-radius:10px !important; }}
        .stDataFrame, .stDataFrame table, [data-testid="stDataFrame"] {{ background-color:{card_bg} !important; color:{text_color} !important; border-radius:12px; }}
        .notif-panel {{ margin-top:8px; background:{card_bg}; backdrop-filter:blur(35px) saturate(150%); border:1px solid {glass_border}; border-radius:14px; box-shadow:0 8px 32px rgba(0,0,0,0.18); max-height:400px; display:flex; flex-direction:column; overflow:hidden; animation:notifSlideDown 0.25s ease-out; }}
        @keyframes notifSlideDown {{ from {{ opacity:0; transform:translateY(-8px); }} to {{ opacity:1; transform:translateY(0); }} }}
        .notif-header {{ display:flex; align-items:center; justify-content:space-between; padding:12px 14px 8px; border-bottom:1px solid {glass_border}; flex-shrink:0; }}
        .notif-header-title {{ font-size:13px; font-weight:700; color:{text_color}; }}
        .notif-list {{ overflow-y:auto; padding:6px 8px; flex:1; }}
        .notif-card {{ display:flex; align-items:flex-start; gap:10px; padding:10px 12px; border-radius:10px; border-left:3px solid transparent; background:transparent; text-decoration:none; color:{text_color}; transition:background 0.15s ease; margin-bottom:4px; }}
        .notif-card:hover {{ background:{nav_hover_bg}; }}
        .notif-card-unread {{ background:rgba(56,189,248,0.05); }}
        .notif-card-body {{ flex:1; min-width:0; }}
        .notif-card-msg {{ font-size:11px; line-height:1.35; color:{text_secondary}; }}
        .notif-dot {{ width:7px; height:7px; border-radius:50%; background:{accent}; flex-shrink:0; margin-top:6px; }}
        .notif-empty {{ display:flex; flex-direction:column; align-items:center; padding:28px 16px; text-align:center; }}
        .notif-empty-icon {{ font-size:32px; margin-bottom:10px; opacity:0.6; }}
        .notif-empty-text {{ font-size:14px; font-weight:600; color:{text_secondary}; }}
        </style>""", unsafe_allow_html=True)

    # ── Notification params ──────────────────────────────────────
    def _handle_notification_params(self):
        params = st.query_params
        action = None; redirect = None
        if "toggle_panel"  in params: toggle_panel(); action = "toggle"
        if "close_panel"   in params: st.session_state.notifications_panel_open = False; action = "close"
        if "mark_all_read" in params: mark_all_read(); action = "mark_all"
        if "read_notif"    in params:
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
        st.sidebar.markdown(self._build_notification_panel(), unsafe_allow_html=True)

    def _build_notification_panel(self):
        colors = {"info":"#38bdf8","success":"#34d399","warning":"#fbbf24","error":"#f87171"}
        icons  = {"info":"ℹ️","success":"✅","warning":"⚠️","error":"🔴"}
        html = '<div class="notif-panel"><div class="notif-header"><span class="notif-header-title">Notifications</span></div><div class="notif-list">'
        if not st.session_state.notifications:
            html += '<div class="notif-empty"><span class="notif-empty-icon">🔔</span><span class="notif-empty-text">All caught up! 🎉</span></div>'
        else:
            for notif in st.session_state.notifications:
                c  = colors.get(notif.type, "#38bdf8")
                ic = icons.get(notif.type, "ℹ️")
                uc = " notif-card-unread" if not notif.read else ""
                dot = '<span class="notif-dot"></span>' if not notif.read else ""
                msg = notif.message[:80] + "…" if len(notif.message) > 80 else notif.message
                html += f'<a class="notif-card{uc}" style="border-left-color:{c};"><span style="font-size:15px">{ic}</span><div class="notif-card-body"><div class="notif-card-msg">{msg}</div></div>{dot}</a>'
        html += '</div></div>'
        return html

    def _handle_notification(self, df_latest: pd.Series):
        alerts = []
        rules = [
            ("pH",           lambda v: v < 6.5 or v > 9.2,               "error",   "pH hors normes critiques"),
            ("pH",           lambda v: 6.5 <= v < 6.8 or 8.2 < v <= 9.2, "warning", "pH légèrement hors de la plage idéale"),
            ("Temperature",  lambda v: v > 30,                             "error",   "Température trop élevée (>30 °C)"),
            ("Temperature",  lambda v: 25 < v <= 30,                       "warning", "Température légèrement haute (>25 °C)"),
            ("Turbidity",    lambda v: v > 5,                              "error",   "Turbidité critique (>5 NTU)"),
            ("Turbidity",    lambda v: 0.5 < v <= 5,                       "warning", "Turbidité au-dessus de l'idéal (>0.5 NTU)"),
            ("TDS",          lambda v: v < 50,                             "error",   "TDS trop bas (<50 ppm)"),
            ("TDS",          lambda v: v > 300,                            "warning", "TDS au-dessus du recommandé (>300 ppm)"),
            ("Conductivity", lambda v: v > 1400,                           "error",   "Conductivité trop élevée (>1400 µS/cm)"),
            ("Conductivity", lambda v: 900 < v <= 1400,                    "warning", "Conductivité au-dessus du recommandé"),
            ("DO",           lambda v: v < 5,                              "error",   "Oxygène dissous critique (<5 mg/L)"),
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
            self.add_notification("normal", "✅  Tous les paramètres sont dans les limites normales.", ntype="success")
        else:
            for level, msg in alerts:
                self.add_notification(level, msg, ntype=level)

    # ── Login page ───────────────────────────────────────────────
    def login_page(self):
        now = time.time()
        remaining_lock = max(0, int(st.session_state.lockout_until - now))

        st.markdown("""<style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Exo+2:wght@300;400;500;600&display=swap');
        .stApp { background: #020c1b !important; }
        .stAppHeader, .stAppDeployButton, #MainMenu { display: none !important; }
        .stMain, .stMainBlockContainer { padding: 0 !important; max-width: 100% !important; }
        [data-testid="column"] { padding: 0 !important; }
        .stTextInput > label { font-family:'Exo 2',sans-serif !important; font-size:11px !important; font-weight:500 !important; letter-spacing:2.5px !important; text-transform:uppercase !important; color:rgba(112,144,184,0.85) !important; }
        .stTextInput input { background:rgba(10,25,65,0.70) !important; border:1px solid rgba(56,189,248,0.22) !important; border-radius:12px !important; color:#e8f0ff !important; font-size:14px !important; padding:12px 16px !important; }
        .stTextInput input:focus { border-color:rgba(56,189,248,0.55) !important; box-shadow:0 0 0 3px rgba(56,189,248,0.10) !important; outline:none !important; }
        .stTextInput input::placeholder { color:rgba(112,144,184,0.45) !important; }
        .stButton > button { width:100% !important; background:linear-gradient(135deg,rgba(0,119,182,0.85),rgba(56,189,248,0.75)) !important; border:1px solid rgba(56,189,248,0.40) !important; border-radius:12px !important; color:#ffffff !important; font-family:'Rajdhani',sans-serif !important; font-size:14px !important; font-weight:700 !important; letter-spacing:3px !important; text-transform:uppercase !important; padding:13px !important; margin-top:8px !important; }
        .stButton > button:hover { background:linear-gradient(135deg,rgba(0,139,212,0.95),rgba(56,189,248,0.90)) !important; transform:translateY(-2px) !important; }
        .stMain .stMainBlockContainer { position:relative; z-index:20; }
        section.main > div { display:flex; flex-direction:column; justify-content:center; min-height:100vh; }
        .aq-footer { position:fixed; left:0; bottom:0; width:100%; background:rgba(2,12,27,0.82); backdrop-filter:blur(12px); border-top:1px solid rgba(56,189,248,0.10); text-align:center; padding:10px 0; z-index:100; }
        .aq-footer-name { font-family:'Rajdhani',sans-serif; font-size:13px; font-weight:600; letter-spacing:1px; color:rgba(56,189,248,0.75); }
        .aq-footer-sub { font-family:'Exo 2',sans-serif; font-size:10px; color:rgba(112,144,184,0.55); letter-spacing:0.5px; margin-top:2px; }
        </style>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="position:fixed;inset:0;z-index:0;background:
            radial-gradient(ellipse 900px 700px at 10% 15%,rgba(0,119,182,0.22) 0%,transparent 65%),
            radial-gradient(ellipse 700px 600px at 85% 80%,rgba(56,189,248,0.15) 0%,transparent 65%),
            linear-gradient(160deg,#020c1b 0%,#040e22 40%,#060f28 100%);">
        </div>
        <div style="position:fixed;inset:0;z-index:1;display:flex;align-items:center;justify-content:center;pointer-events:none;">
          <div style="text-align:center;margin-bottom:300px;">
            <div style="font-family:'Rajdhani',sans-serif;font-size:28px;font-weight:700;letter-spacing:4px;color:#e8f0ff;">
              AQUA<span style="color:#38bdf8;">MONITOR</span>
            </div>
            <div style="font-family:'Exo 2',sans-serif;font-size:10px;letter-spacing:4px;color:rgba(112,144,184,0.75);margin-top:6px;">
              WATER QUALITY INTELLIGENCE SYSTEM
            </div>
            <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(56,189,248,0.3),transparent);margin:16px auto;width:300px;"></div>
            <div style="font-family:'Rajdhani',sans-serif;font-size:12px;letter-spacing:3px;color:rgba(112,144,184,0.6);">
              SECURE ACCESS PORTAL
            </div>
          </div>
        </div>
        <div class="aq-footer">
            <div class="aq-footer-name">Developed by Ourabah Sanaa & ANNABI ADEL</div>
            <div class="aq-footer-sub">Master – Industrial Computer Science &nbsp;|&nbsp; University of Oran 1</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:220px;margin-top:40px;'></div>", unsafe_allow_html=True)
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            if remaining_lock > 0:
                st.error(f"⛔ Compte verrouillé. Réessayez dans {remaining_lock} secondes.")
            else:
                username = st.text_input("Username", placeholder="Enter your username", key="login_user")
                password = st.text_input("Password", type="password", placeholder="••••••••", key="login_pass")
                if st.button("AUTHENTICATE  →", key="login_btn"):
                    if verify_credentials(username.strip(), password):
                        st.session_state.logged_in = True
                        st.session_state.login_attempts = 0
                        st.session_state.lockout_until = 0
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        attempts_left = max(0, 5 - st.session_state.login_attempts)
                        if st.session_state.login_attempts >= 5:
                            st.session_state.lockout_until = time.time() + 60
                            st.session_state.login_attempts = 0
                            st.rerun()
                        else:
                            st.toast(f"⚠️ Invalid credentials — {attempts_left} attempt{'s' if attempts_left!=1 else ''} remaining")

    # ── Utilities ────────────────────────────────────────────────
    def add_notification(self, title: str, message: str = "", ntype: Literal["info","success","warning","error"] = "info", action_url: str | None = None):
        st.session_state.notifications.append(Notification(
            id=str(uuid4()), title=title, message=message or title,
            type=ntype, timestamp=datetime.now(), read=False, action_url=action_url,
        ))

    # ── Dashboard page ───────────────────────────────────────────
    def dash_page(self):
        if "theme" not in st.session_state:
            st.session_state.theme = "dark"

        self.set_css(st.session_state.theme)
        self._handle_notification_params()

        # ── Timer 30s — recharge Firebase en arrière-plan silencieusement ──
        count = st_autorefresh(interval=5000, key="refresh_main")
        if st.session_state.get("_last_refresh_count") != count:
            st.session_state["_last_refresh_count"] = count
            with st.spinner(""):   # spinner vide = invisible
                st.session_state["_cached_df"] = load_dataV2()

        # ── Premier chargement uniquement ──
        if "_cached_df" not in st.session_state or st.session_state["_cached_df"].empty:
            with st.spinner("Chargement des données..."):
                st.session_state["_cached_df"] = load_dataV2()

        # ── Tous les clics utilisent le cache — aucune requête Firebase ──
        self.df = st.session_state["_cached_df"]
        if self.df.empty:
            st.markdown("<h3 style='text-align:center;color:#f87171;'>No data available</h3>", unsafe_allow_html=True)
            return

        self.time         = self.df["created_at"].iloc[-1]
        self.temperature  = self.df["Temperature"].iloc[-1]
        self.ph           = self.df["pH"].iloc[-1]
        self.turbidity    = self.df["Turbidity"].iloc[-1]
        self.tds          = self.df["TDS"].iloc[-1]
        self.conductivity = self.df["Conductivity"].iloc[-1]
        self.do           = self.df["DO"].iloc[-1]

        is_dark = st.session_state.theme == "dark"

        st.sidebar.markdown("""
        <div class="sidebar-logo">
            <span class="logo-icon">💧</span>
            <div>
                <div class="logo-text">AquaMonitor</div>
                <div class="logo-sub">Water Quality System</div>
            </div>
        </div>""", unsafe_allow_html=True)

        menu_option = st.sidebar.radio(
            "Navigate to",
            ["🏠 Dashboard", "📡 Real-Time Data", "📊 Data Analysis", "🤖 AI Assistant"],
            index=0, label_visibility="collapsed"
        )
        st.session_state["_menu"] = menu_option

        self._render_notification()

        st.sidebar.markdown('<hr class="glass-divider">', unsafe_allow_html=True)
        st.sidebar.markdown('<div class="sidebar-section-title">System Status</div>', unsafe_allow_html=True)

        activesens = sum([
            (self.df["ph_sensor"]        == True).any(),
            (self.df["tds_sensor"]       == True).any(),
            (self.df["turbidity_sensor"] == True).any(),
            (self.df["temp_sensor"]      == True).any(),
        ])

        st.sidebar.markdown(f"""
        <div class="status-badge status-ok">🟢  Online — Connected</div>
        <div class="status-badge status-err">🔴  Sensors: {activesens} active</div>
        """, unsafe_allow_html=True)

        st.sidebar.markdown('<hr class="glass-divider">', unsafe_allow_html=True)
        st.sidebar.markdown('<div class="sidebar-section-title">Appearance</div>', unsafe_allow_html=True)
        theme_label = "☀️  Switch to Light Mode" if is_dark else "🌙  Switch to Dark Mode"
        if st.sidebar.button(theme_label, key="theme_toggle"):
            st.session_state.theme = "light" if is_dark else "dark"
            st.rerun()

        st.sidebar.markdown('<hr class="glass-divider">', unsafe_allow_html=True)
        if st.sidebar.button("🚪  Logout", key="logout"):
            st.session_state.logged_in = False
            st.rerun()

        st.sidebar.markdown(f"""
        <div style="margin-top:18px;text-align:center;font-size:10px;color:{'#5070a0' if not is_dark else '#4a6080'};padding:0 8px;">
            AquaMonitor v2.0<br>University of Oran 1<br>© 2026 Ourabah Sanaa & ANNABI ADEL
        </div>""", unsafe_allow_html=True)

        menu_clean = menu_option.strip()
        if "Dashboard"     in menu_clean:
            st.session_state.notifications = []
            render_dashboard(self.df, st.session_state.theme)
        elif "Real-Time"   in menu_clean:
            st.session_state.notifications = []
            render_realtime(self.df, st.session_state.theme)
        elif "Data Analysis" in menu_clean:
            st.session_state.notifications = []
            render_data_analysis(self.df, st.session_state.theme)
        elif "AI" in menu_clean:
            render_ai(self.df, st.session_state.theme)


if __name__ == "__main__":
    wDash = waterDash()
    wDash.run()
