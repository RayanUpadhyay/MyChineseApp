import streamlit as st
import pandas as pd
import random
import time
import base64
from pathlib import Path
from groq import Groq
from database import init_db, migrate_from_csv, create_user, authenticate_user, get_user, update_xp, get_leaderboard, reset_password
from tts_helper import create_audio_button_html

# --------------------------------------------------
# PATHS
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users.csv"
RADICALS_FILE = BASE_DIR / "radicals.csv"
# Background supports png, jpg, or jpeg — whichever exists in the project folder
_BG_CANDIDATES = [
    (BASE_DIR / "background.png", "image/png"),
    (BASE_DIR / "background.jpg", "image/jpeg"),
    (BASE_DIR / "background.jpeg", "image/jpeg"),
]

# --------------------------------------------------
# PAGE CONFIG (FIRST)
# --------------------------------------------------
st.set_page_config(page_title="Mandalink", layout="wide")

# --------------------------------------------------
# BACKGROUND IMAGE (BASE64 EMBED)
# --------------------------------------------------
_bg_css = "linear-gradient(135deg, #f5f5f5 0%, #ebf3fc 100%)"
for _bg_path, _bg_mime in _BG_CANDIDATES:
    if _bg_path.exists():
        _bg_b64 = base64.b64encode(_bg_path.read_bytes()).decode()
        _bg_css = f"url('data:image/{_bg_mime};base64,{_bg_b64}')"
        break

# --------------------------------------------------
# GLOBAL CSS: PARCHMENT + CRIMSON THEME
# --------------------------------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap');

html, body, [class*="css"] {{
    font-family: 'Segoe UI','Noto Sans SC',sans-serif;
    color: #242424 !important;
}}

.stApp {{
    background-image: {_bg_css};
    background-size: cover;
    background-attachment: fixed;
    background-repeat: no-repeat;
    min-height: 100vh;
}}

/* Headings */
h1, h2, h3, h4, h5, h6, .stSubheader {{
    color: #0f6cbd !important;
    font-family: 'Segoe UI','Noto Sans SC',sans-serif;
    font-weight: 700 !important;
}}

/* Form labels */
label {{
    color: #115ea3 !important;
    font-weight: 600 !important;
}}

/* Placeholders */
input::placeholder, textarea::placeholder {{
    color: #616161 !important;
    -webkit-text-fill-color: #616161 !important;
}}

/* Body text */
.stMarkdown p, .stMarkdown li {{
    color: #242424 !important;
    font-size: 1.05rem;
}}

.stCaption {{
    color: #115ea3 !important;
    opacity: 0.9;
}}

/* Notifications */
[data-testid="stNotification"] {{
    background-color: rgba(255, 255, 255, 0.85) !important;
    border: 1px solid rgba(15, 108, 189, 0.35) !important;
    border-radius: 8px !important;
}}

[data-testid="stNotification"] p {{
    color: #242424 !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
}}

/* Input fields */
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] {{
    background-color: #ffffff !important;
    border: 2px solid #0f6cbd !important;
    border-radius: 8px !important;
}}

div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {{
    color: #242424 !important;
    background-color: #ffffff !important;
    -webkit-text-fill-color: #242424 !important;
}}

/* Dataframes */
[data-testid="stTable"], [data-testid="stDataFrame"] {{
    background-color: rgba(255, 255, 255, 0.7) !important;
    border-radius: 12px;
    padding: 10px;
}}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {{
    background: rgba(247, 240, 232, 0.98) !important;
    border-right: 2px solid rgba(15, 108, 189, 0.15);
}}

section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: #0f6cbd !important;
}}

section[data-testid="stSidebar"] button {{
    background-color: #0f6cbd !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: background-color 0.2s !important;
    margin-bottom: 3px !important;
    text-align: left !important;
}}

section[data-testid="stSidebar"] button:hover {{
    background-color: #0f6cbd !important;
    color: #ffffff !important;
}}

/* ── GAME / FLASHCARD CARD ── */
.game-card {{
    background: #0f6cbd;
    padding: 2.5rem 2rem;
    border-radius: 16px;
    max-width: 820px;
    margin: 1.2rem auto;
    text-align: center;
    box-shadow: 0 6px 24px rgba(15, 108, 189, 0.25);
}}

.radical-big {{
    font-size: 7rem;
    font-weight: 900;
    color: #ffffff;
    margin: 1.5rem 0;
    text-shadow: 0 2px 8px rgba(0,0,0,0.12);
}}

/* ── HOME PAGE ── */
.home-container {{
    max-width: 760px;
    margin: 0 auto;
    padding: 2.5rem 1rem;
    text-align: center;
}}

.home-logo {{
    width: 160px;
    height: 160px;
    border-radius: 20px;
    margin-bottom: 1rem;
    object-fit: contain;
}}

.home-title {{
    font-size: 4rem;
    font-weight: 900;
    color: #0f6cbd !important;
    -webkit-text-fill-color: #0f6cbd !important;
    background: none;
    -webkit-background-clip: unset !important;
    background-clip: unset !important;
    margin: 0 0 0.3rem 0;
    line-height: 1.1;
    font-family: 'Segoe UI','Noto Sans SC',sans-serif;
}}

.home-tagline {{
    font-size: 1.2rem;
    color: #115ea3;
    letter-spacing: 0.05em;
    margin: 0 0 1.8rem 0;
    font-weight: 600;
}}

.home-divider {{
    width: 60px;
    height: 2px;
    background: #0f6cbd;
    margin: 0 auto 2rem auto;
    border-radius: 2px;
}}

.home-desc-card {{
    background: #ffffff;
    border: 1px solid #f0f0f0;
    border-radius: 16px;
    padding: 1.8rem 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 0 2px rgba(0,0,0,.08), 0 4px 12px rgba(0,0,0,.06);
}}

.home-desc {{
    font-size: 1.1rem;
    color: #242424;
    line-height: 1.85;
    margin: 0;
    font-weight: 500;
}}

.feature-section {{
    margin-bottom: 2rem;
}}

.feature-label {{
    font-size: 0.78rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #115ea3;
    font-weight: 700;
    margin-bottom: 0.5rem;
}}

.feature-list {{
    color: #115ea3;
    font-size: 0.92rem;
    font-weight: 600;
    margin: 0;
    display: inline-block;
    background: #ebf3fc;
    padding: 0.5rem 1.2rem;
    border-radius: 9999px;
    letter-spacing: 0.01em;
}}

/* ── AUTH PAGE ── */
.auth-container {{
    max-width: 540px;
    margin: 0.5rem auto 1.5rem auto;
    padding: 1.8rem 2.5rem;
    text-align: center;
    background: #ffffff;
    border: 1px solid #f0f0f0;
    border-radius: 16px;
    box-shadow: 0 0 8px rgba(0,0,0,.06), 0 14px 28px rgba(0,0,0,.08);
}}

.auth-title {{
    font-size: 2rem;
    font-weight: 900;
    color: #0f6cbd;
    margin-bottom: 0.2rem;
    font-family: 'Segoe UI','Noto Sans SC',sans-serif;
}}

.auth-sub {{
    color: #115ea3;
    font-size: 1rem;
    margin-bottom: 0.8rem;
    font-weight: 500;
}}

/* ── TABS ── */
button[data-baseweb="tab"] {{
    font-size: 1rem !important;
    font-weight: 700 !important;
    padding: 0.6rem 2rem !important;
    color: #616161 !important;
    background-color: #f0f0f0 !important;
    border-radius: 8px 8px 0 0 !important;
    border: none !important;
}}

button[data-baseweb="tab"][aria-selected="true"] {{
    background-color: #0f6cbd !important;
    color: #ffffff !important;
    border-bottom: 3px solid #115ea3 !important;
}}

button[data-baseweb="tab"]:hover {{
    background-color: #115ea3 !important;
    color: #ffffff !important;
}}

/* ── PRIMARY BUTTONS ── */
.stButton > button[kind="primary"],
[data-testid="baseButton-primary"] {{
    background-color: #0f6cbd !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 0.65rem 1.5rem !important;
    box-shadow: 0 1px 2px rgba(0,0,0,.12), 0 2px 4px rgba(0,0,0,.14) !important;
}}

.stButton > button[kind="primary"]:hover,
[data-testid="baseButton-primary"]:hover {{
    background-color: #115ea3 !important;
}}

/* ── DEFAULT BUTTONS ── */
.stButton > button {{
    background-color: #0f6cbd !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}}

.stButton > button:hover {{
    background-color: #115ea3 !important;
    color: #ffffff !important;
}}

/* ── GAME ANSWER BUTTONS (outlined style via wrapper) ── */
.answer-opt .stButton > button {{
    background-color: #ffffff !important;
    color: #242424 !important;
    border: 1.5px solid #0f6cbd !important;
    border-radius: 8px !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    text-align: left !important;
}}

.answer-opt .stButton > button:hover {{
    background-color: #f5f5f5 !important;
    border-color: #0f6cbd !important;
    color: #242424 !important;
}}

.answer-opt .stButton > button:disabled {{
    opacity: 0.6 !important;
}}

/* Checkbox */
.stCheckbox label {{
    color: #242424 !important;
}}

/* FAQ expander */
[data-testid="stExpander"] {{
    background: rgba(255,255,255,0.28) !important;
    border: 1px solid rgba(15,108,189,0.18) !important;
    border-radius: 10px !important;
    margin-bottom: 0.5rem !important;
}}

[data-testid="stExpander"] summary {{
    color: #0f6cbd !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
}}

[data-testid="stExpander"] p,
[data-testid="stExpander"] div {{
    color: #242424 !important;
}}

/* Text area */
textarea {{
    color: #242424 !important;
    background-color: #ffffff !important;
}}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# GROQ
# --------------------------------------------------
client = Groq(api_key="your_api_key_here")

# --------------------------------------------------
# DATABASE INITIALIZATION (ONLY ONCE PER SESSION)
# --------------------------------------------------
if "db_initialized" not in st.session_state:
    init_db()
    migrate_from_csv()
    st.session_state.db_initialized = True

# --------------------------------------------------
# LOAD RADICALS
# --------------------------------------------------
if not RADICALS_FILE.exists():
    st.error("❌ radicals.csv not found")
    st.stop()

raw = pd.read_csv(RADICALS_FILE)
raw.columns = [c.strip().lower() for c in raw.columns]

def find_col(name):
    for c in raw.columns:
        if name in c:
            return c
    return None

rad_col = find_col("radical")
mean_col = find_col("meaning")
pin_col = find_col("pinyin")

if not rad_col or not mean_col:
    st.error("❌ radicals.csv must contain Radical and Meaning columns")
    st.stop()

RADICALS = raw.rename(columns={
    rad_col: "radical",
    mean_col: "meaning",
    pin_col: "pinyin" if pin_col else None
})[["radical", "meaning"] + (["pinyin"] if pin_col else [])].dropna()

if len(RADICALS) < 4:
    st.error("❌ Not enough radicals to run app")
    st.stop()

# --------------------------------------------------
# NOTE: User management now handled by database.py
# --------------------------------------------------

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
for key, val in {
    "logged_in": False,
    "user": None,
    "page": "Learn",
    "app_page": "home",   # home | auth | app
    "auth_tab": "login",  # login | register
    "question": None,
    "answered": False,
    "correct": False,
    "attempts": 0,
    "already_earned_xp": False,
    "timer_running": False,
    "time_left": 0,
    "timed_score": 0,
    "timed_correct": 0,
    "timed_total": 0,
    "timed_feedback": None,
    "timed_results": False,
}.items():
    st.session_state.setdefault(key, val)

# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------
if not st.session_state.logged_in and st.session_state.app_page == "home":
    logo_html = '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABBAAAAPgCAYAAACLUI9nAAABCGlDQ1BJQ0MgUHJvZmlsZQAAeJxjYGA8wQAELAYMDLl5JUVB7k4KEZFRCuwPGBiBEAwSk4sLGHADoKpv1yBqL+viUYcLcKakFi[...]'

    st.markdown(f"""
<div class="home-container">
{logo_html}
<h1 class="home-title">Mandalink</h1>
<p class="home-tagline">Chinese Radicals Simplified</p>
<div class="home-divider"></div>
<div class="home-desc-card">
<p class="home-desc">
Mandalink is your gateway to mastering the building blocks of Chinese — radicals.
Through interactive flashcards, AI-powered hints, timed challenges, and animated
stroke-order guides, we make learning Chinese characters intuitive, engaging, and
effective. Whether you're a complete beginner or brushing up your skills,
Mandalink adapts to your pace and helps you build lasting knowledge.
</p>
</div>
<div class="feature-section">
<p class="feature-label">Featuring</p>
<p class="feature-list">Flashcards &bull; Quiz Games &bull; Stroke Order &bull; Timed Mode &bull; AI Help &bull; Leaderboard</p>
</div>
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        st.markdown('<div style="text-align:center; margin-top:0.5rem;">', unsafe_allow_html=True)
        if st.button("Login", use_container_width=True, type="primary", key="home_login_btn"):
            st.session_state.app_page = "auth"
            st.session_state.auth_tab = "login"
            st.rerun()
        st.markdown('<div style="margin-top:0.5rem;"></div>', unsafe_allow_html=True)
        if st.button("Register", use_container_width=True, key="home_register_btn"):
            st.session_state.app_page = "auth"
            st.session_state.auth_tab = "register"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# --------------------------------------------------
# AUTH PAGE (LOGIN / REGISTER)
# --------------------------------------------------
if not st.session_state.logged_in and st.session_state.app_page == "auth":
    logo_html = '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABBAAAAPgCAYAAACLUI9nAAABCGlDQ1BJQ0MgUHJvZmlsZQAAeJxjYGA8wQAELAYMDLl5JUVB7k4KEZFRCuwPGBiBEAwSk4sLGHADoKpv1yBqL+viUYcLcKakFi[...]'

