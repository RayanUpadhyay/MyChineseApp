import streamlit as st
import pandas as pd
import random
import time
from pathlib import Path
from groq import Groq
from database import init_db, migrate_from_csv, create_user, authenticate_user, get_user, update_xp, get_leaderboard
from tts_helper import create_audio_button_html

# --------------------------------------------------
# PATHS
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users.csv"
RADICALS_FILE = BASE_DIR / "radicals.csv"
BACKGROUND_FILE = BASE_DIR / "background.png"

# --------------------------------------------------
# PAGE CONFIG (FIRST)
# --------------------------------------------------
st.set_page_config(page_title="Mandalink", layout="wide")

# --------------------------------------------------
# THEME (layout-only styling)
# --------------------------------------------------
st.session_state.setdefault("theme", "current")  # current | black | white

THEME_OPTIONS = ["black", "white", "current"]
THEME_LABEL = {"current": "Current", "black": "Black", "white": "White"}

_THEME_PRESETS = {
    "current": {"text_primary": "#fef3c7", "text_soft": "#fef3c7", "panel_bg": "#fef3c7"},
    "black": {"text_primary": "#fef3c7", "text_soft": "#fef3c7", "panel_bg": "#111827"},
    "white": {"text_primary": "#111827", "text_soft": "#374151", "panel_bg": "#ffffff"},
}

_theme = st.session_state.theme if st.session_state.theme in _THEME_PRESETS else "current"
text_primary = _THEME_PRESETS[_theme]["text_primary"]
text_soft = _THEME_PRESETS[_theme]["text_soft"]
panel_bg = _THEME_PRESETS[_theme]["panel_bg"]

# --------------------------------------------------
# GLOBAL CSS: GRADIENT BG + CHINESE FONT + GAME STYLES
# --------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Serif SC', SimSun, '宋体', serif;
    color: #fef3c7 !important;
}

.stApp {
    background: linear-gradient(160deg,
        #1a0505 0%,
        #2d0a0a 25%,
        #3d0f0f 50%,
        #1f0808 75%,
        #0f0303 100%);
    background-attachment: fixed;
    min-height: 100vh;
}

/* Global headings visibility */
h1, h2, h3, h4, h5, h6, .stSubheader {
    color: #D4AF37 !important;
    font-family: 'Noto Serif SC', serif;
    font-weight: 700 !important;
}

/* Form labels and placeholders */
label {
    color: #fde047 !important;
    font-weight: 500 !important;
}

input::placeholder, textarea::placeholder {
    color: #6b7280 !important;
    -webkit-text-fill-color: #6b7280 !important;
}

/* Streamlit component contrasts */
.stMarkdown p, .stMarkdown li {
    color: #fef3c7 !important;
    font-size: 1.05rem;
}

.stCaption {
    color: #fde047 !important;
    opacity: 0.8;
}

/* Meanings / Success / Info boxes legibility */
[data-testid="stNotification"] {
    background-color: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(212, 175, 55, 0.3) !important;
}

[data-testid="stNotification"] p {
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 1.1rem !important;
}

/* Input fields (search, etc) */
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] {
    background-color: #ffffff !important;
    border: 2px solid #D4AF37 !important;
    border-radius: 8px !important;
}

div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {
    color: #000000 !important;
    background-color: #ffffff !important;
    -webkit-text-fill-color: #000000 !important;
}

/* Dataframes / Tables legibility */
[data-testid="stTable"], [data-testid="stDataFrame"] {
    background-color: rgba(255, 255, 255, 0.05) !important;
    border-radius: 12px;
    padding: 10px;
}

/* Sidebar contrasts */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #7f1d1d 0%, #991b1b 50%, #7f1d1d 100%);
    border-right: 1px solid rgba(212, 175, 55, 0.3);
}

section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #fef3c7 !important;
}

section[data-testid="stSidebar"] button {
    background-color: rgba(0, 0, 0, 0.2) !important;
    color: #fde047 !important;
    border: 1px solid rgba(212, 175, 55, 0.2) !important;
    transition: all 0.3s;
}

section[data-testid="stSidebar"] button:hover {
    background-color: rgba(212, 175, 55, 0.1) !important;
    border-color: #D4AF37 !important;
}

/* Game card */
.game-card {
    background: rgba(139, 0, 0, 0.88);
    padding: 2.5rem;
    border-radius: 24px;
    max-width: 720px;
    margin: 2rem auto;
    text-align: center;
    box-shadow: 0 20px 60px rgba(0,0,0,0.6), 0 0 0 1px rgba(212,175,55,0.2);
    border: 1px solid rgba(212, 175, 55, 0.15);
}

.radical-big {
    font-size: 7rem;
    font-weight: 900;
    color: #fde047;
    margin: 1.5rem 0;
    text-shadow: 0 4px 20px rgba(253,224,71,0.4);
}

.game-option button {
    width: 100%;
    padding: 1.2rem;
    font-size: 1.25rem;
    border-radius: 16px;
    margin-bottom: 1rem;
    background: #111827;
    color: white;
    border: none;
}

.game-option button:hover {
    background: #1f2937;
}

/* HOME PAGE STYLES */
.home-container {
    max-width: 860px;
    margin: 0 auto;
    padding: 2rem 1rem;
    text-align: center;
}

.home-logo {
    width: 160px;
    height: 160px;
    border-radius: 32px;
    box-shadow: 0 8px 40px rgba(212,175,55,0.35), 0 0 0 3px rgba(212,175,55,0.25);
    margin-bottom: 1.5rem;
    object-fit: cover;
}

.home-title {
    font-size: 4.5rem;
    font-weight: 900;
    background: linear-gradient(135deg, #D4AF37, #FFD700, #C8960C);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
    margin: 0;
    line-height: 1.1;
    font-family: 'Noto Serif SC', SimSun, serif;
}

.home-tagline {
    font-size: 1.3rem;
    color: #fde047;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 0.6rem 0 2rem 0;
    font-weight: 500;
    opacity: 0.9;
}

.home-divider {
    width: 80px;
    height: 3px;
    background: linear-gradient(90deg, transparent, #D4AF37, transparent);
    margin: 0 auto 2.5rem auto;
    border-radius: 2px;
}

.home-desc-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(212, 175, 55, 0.15);
    border-radius: 24px;
    padding: 2.5rem;
    margin-bottom: 3rem;
    backdrop-filter: blur(12px);
    box-shadow: inset 0 0 20px rgba(212, 175, 55, 0.05);
}

.home-desc {
    font-size: 1.15rem;
    color: #fef3c7;
    line-height: 1.8;
    margin: 0;
    opacity: 0.9;
    font-weight: 300;
}

.feature-row {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 2.5rem;
}

.feature-pill {
    background: rgba(212,175,55,0.12);
    border: 1px solid rgba(212,175,55,0.3);
    border-radius: 50px;
    padding: 0.5rem 1.2rem;
    color: #fde047;
    font-size: 0.9rem;
    font-weight: 500;
    letter-spacing: 0.05em;
}

.home-btn-row {
    display: flex;
    gap: 1.2rem;
    justify-content: center;
    flex-wrap: wrap;
    margin-top: 0.5rem;
}

.home-btn-login {
    padding: 1rem 3rem;
    font-size: 1.1rem;
    font-weight: 700;
    border-radius: 50px;
    background: linear-gradient(135deg, #C41E3A, #8B0000);
    color: white;
    border: none;
    cursor: pointer;
    letter-spacing: 0.05em;
    box-shadow: 0 8px 24px rgba(196,30,58,0.45);
    transition: all 0.25s;
    font-family: 'Noto Serif SC', sans-serif;
}

.home-btn-login:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 32px rgba(196,30,58,0.6);
    background: linear-gradient(135deg, #dc143c, #9b0000);
}

.home-btn-register {
    padding: 1rem 2.8rem;
    font-size: 1.1rem;
    font-weight: 700;
    border-radius: 50px;
    background: transparent;
    color: #D4AF37;
    border: 2px solid #D4AF37;
    cursor: pointer;
    letter-spacing: 0.05em;
    transition: all 0.25s;
    font-family: 'Noto Serif SC', sans-serif;
}

.home-btn-register:hover {
    background: rgba(212,175,55,0.15);
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(212,175,55,0.25);
}

.chinese-watermark {
    font-size: 11rem;
    color: rgba(212,175,55,0.05);
    position: fixed;
    bottom: -2rem;
    right: 2rem;
    pointer-events: none;
    z-index: 0;
    line-height: 1;
}

/* AUTH PAGE STYLES */
.auth-container {
    max-width: 480px;
    margin: 2rem auto;
    padding: 2.5rem;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(212,175,55,0.2);
    border-radius: 24px;
    backdrop-filter: blur(12px);
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}

.auth-title {
    font-size: 2rem;
    font-weight: 700;
    color: #D4AF37;
    text-align: center;
    margin-bottom: 0.3rem;
    font-family: 'Noto Serif SC', SimSun, serif;
}

.auth-sub {
    text-align: center;
    color: #fde047;
    opacity: 0.7;
    font-size: 0.95rem;
    margin-bottom: 2.5rem;
}

/* Streamlit Tabs Customization for Auth / General */
button[data-baseweb="tab"] {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    padding-bottom: 0.8rem !important;
    color: rgba(254, 243, 199, 0.6) !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #D4AF37 !important;
    border-bottom: 4px solid #D4AF37 !important;
}

button[data-baseweb="tab"]:hover {
    color: #fde047 !important;
}
</style>
""", unsafe_allow_html=True)

# Theme overrides: keep "current" as the default CSS above
if _theme == "black":
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(160deg, #000000 0%, #0b0b0b 30%, #050505 100%) !important;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b0b0b 0%, #111827 50%, #0b0b0b 100%) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #fef3c7 !important;
    }
    .game-card {
        background: rgba(0, 0, 0, 0.75) !important;
        box-shadow: 0 18px 50px rgba(0,0,0,0.75), 0 0 0 1px rgba(212,175,55,0.2) !important;
    }
    .home-desc-card {
        background: rgba(255, 255, 255, 0.04) !important;
    }
    .auth-container {
        background: rgba(255,255,255,0.06) !important;
    }
    </style>
    """, unsafe_allow_html=True)
elif _theme == "white":
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(160deg, #ffffff 0%, #f3f4f6 35%, #ffffff 100%) !important;
    }
    html, body, [class*="css"] {
        color: #111827 !important;
    }
    .stMarkdown p, .stMarkdown li {
        color: #111827 !important;
    }
    label {
        color: #b45309 !important;
    }
    .stCaption {
        color: #b45309 !important;
    }
    [data-testid="stNotification"] p {
        color: #111827 !important;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f3f4f6 50%, #ffffff 100%) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #111827 !important;
    }
    .home-desc-card {
        background: rgba(0, 0, 0, 0.03) !important;
    }
    .home-desc {
        color: #374151 !important;
    }
    .auth-container {
        background: rgba(255,255,255,0.72) !important;
        box-shadow: 0 20px 60px rgba(0,0,0,0.10) !important;
    }
    .game-card {
        background: rgba(255, 255, 255, 0.86) !important;
        box-shadow: 0 18px 55px rgba(0,0,0,0.10), 0 0 0 1px rgba(212,175,55,0.22) !important;
    }
    .home-tagline {
        color: #b45309 !important;
    }
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
    "app_page": "about",   # about | auth | app
    "auth_tab": "login", # login | register
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
if not st.session_state.logged_in and st.session_state.app_page == "about":
    import base64
    LOGO_FILE = BASE_DIR / "Mandalink (1).jpg.jpeg"
    logo_html = ""
    if LOGO_FILE.exists():
        logo_b64 = base64.b64encode(LOGO_FILE.read_bytes()).decode()
        logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" class="home-logo" alt="Mandalink Logo" />'

    st.radio(
        "Theme",
        options=THEME_OPTIONS,
        format_func=lambda t: THEME_LABEL[t],
        horizontal=True,
        key="theme",
    )

    st.markdown(f"""
<div class="chinese-watermark">文</div>
<div class="home-container">
{logo_html}
<h1 class="home-title">About Mandalink</h1>
<p class="home-tagline">Chinese Radicals Simplified</p>
<div class="home-divider"></div>
<div class="home-desc-card">
<p class="home-desc">
Mandalink is a learning app built to help you master Chinese radicals—the building blocks
of Chinese characters. Use interactive flashcards, guided stroke order, and quiz-style
practice to build recognition and understanding. When you want extra help, the AI helper
can give targeted hints to keep you moving forward.
</p>
</div>
<div class="feature-row">
<span class="feature-pill">📘 Radical Meanings</span>
<span class="feature-pill">🃏 Flashcards</span>
<span class="feature-pill">🎮 Quiz Games</span>
<span class="feature-pill">✍️ Stroke Order</span>
<span class="feature-pill">⏱️ Timed Mode</span>
<span class="feature-pill">🤖 AI Help</span>
<span class="feature-pill">🏆 Leaderboard</span>
</div>
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        st.markdown('<div style="text-align:center; margin-top:0.5rem;">', unsafe_allow_html=True)
        if st.button("🔐  Login", use_container_width=True, type="primary", key="home_login_btn"):
            st.session_state.app_page = "auth"
            st.session_state.auth_tab = "login"
            st.rerun()
        st.markdown('<div style="margin-top:0.7rem;"></div>', unsafe_allow_html=True)
        if st.button("📝  Register", use_container_width=True, key="home_register_btn"):
            st.session_state.app_page = "auth"
            st.session_state.auth_tab = "register"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# --------------------------------------------------
# AUTH PAGE (LOGIN / REGISTER)
# --------------------------------------------------
if not st.session_state.logged_in and st.session_state.app_page == "auth":
    import base64
    LOGO_FILE = BASE_DIR / "Mandalink (1).jpg.jpeg"
    logo_html = ""
    if LOGO_FILE.exists():
        logo_b64 = base64.b64encode(LOGO_FILE.read_bytes()).decode()
        logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" style="width:70px;height:70px;border-radius:16px;margin-bottom:0.8rem;box-shadow:0 4px 20px rgba(212,175,55,0.3);object-fit:cover;" alt="Logo" />'

    st.radio(
        "Theme",
        options=THEME_OPTIONS,
        format_func=lambda t: THEME_LABEL[t],
        horizontal=True,
        key="theme",
    )

    # Back button (top-left)
    if st.button("← Back", key="auth_back_btn"):
        st.session_state.app_page = "about"
        st.rerun()

    tab_label = "Login" if st.session_state.auth_tab == "login" else "Register"

    st.markdown(f"""
    <div class="auth-container">
        <div style="text-align:center;">{logo_html}</div>
        <div class="auth-title">{tab_label}</div>
        <div class="auth-sub">{'Welcome back to Mandalink' if tab_label == 'Login' else 'Join Mandalink today'}</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    # Sync active tab if coming from home buttons
    with tab1:
        login_username = st.text_input("Username", key="login_user", placeholder="Enter your username")
        login_password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")

        if st.button("Login", type="primary", use_container_width=True, key="auth_login_btn"):
            if login_username and login_password:
                success, message = authenticate_user(login_username, login_password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user = login_username
                    st.session_state.app_page = "app"
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Please enter both username and password")

    with tab2:
        signup_username = st.text_input("Username", key="signup_user", placeholder="Choose a username")
        signup_email = st.text_input("Email", key="signup_email", placeholder="your@email.com")
        signup_password = st.text_input("Password", type="password", key="signup_pass", placeholder="At least 4 characters")
        signup_confirm = st.text_input("Confirm Password", type="password", key="signup_confirm", placeholder="Repeat password")

        if st.button("Create Account", type="primary", use_container_width=True, key="auth_signup_btn"):
            if not all([signup_username, signup_email, signup_password, signup_confirm]):
                st.warning("Please fill in all fields")
            elif signup_password != signup_confirm:
                st.error("Passwords do not match")
            elif len(signup_password) < 4:
                st.error("Password must be at least 4 characters")
            else:
                success, message = create_user(signup_username, signup_email, signup_password)
                if success:
                    st.success(f"{message} You can now login!")
                else:
                    st.error(message)

    st.stop()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("🔥 Menu")

st.sidebar.radio(
    "Theme",
    options=THEME_OPTIONS,
    format_func=lambda t: THEME_LABEL[t],
    horizontal=True,
    key="theme",
)
st.sidebar.markdown("---")

for label in [
    "Learn",
    "Flashcards",
    "Game",
    "Timed Mode",
    "Leaderboard",
    "Stroke Order",
    "AI Help"
]:
    if st.sidebar.button(label):
        st.session_state.page = label

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.app_page = "about"
    st.rerun()

# --------------------------------------------------
# USER INFO
# --------------------------------------------------
user_data = get_user(st.session_state.user)
if user_data:
    st.sidebar.markdown("---")
    st.sidebar.metric("⭐ XP", int(user_data['xp']))
    st.sidebar.metric("🏅 Level", int(user_data['level']))
    st.sidebar.caption(f"👤 {user_data['username']}")

# --------------------------------------------------
# LEARN (WITH SEARCH AND AUDIO)
# --------------------------------------------------
if st.session_state.page == "Learn":
    st.title("📘 Radical Meanings")
    
    # Search bar
    search_query = st.text_input("🔍 Search radicals by meaning, pinyin, or character...", key="learn_search")
    
    # Filter radicals based on search
    if search_query:
        filtered = RADICALS[
            RADICALS['radical'].str.contains(search_query, case=False, na=False) |
            RADICALS['meaning'].str.contains(search_query, case=False, na=False) |
            (RADICALS['pinyin'].str.contains(search_query, case=False, na=False) if 'pinyin' in RADICALS.columns else False)
        ]
    else:
        filtered = RADICALS
    
    # Display results
    if len(filtered) == 0:
        st.warning("No radicals found matching your search.")
    else:
        st.caption(f"Showing {len(filtered)} radical(s)")
        for _, r in filtered.iterrows():
            col1, col2 = st.columns([1, 10])
            with col1:
                st.markdown(f"## {r.radical}")
            with col2:
                st.markdown(f"### {r.meaning}")
                if "pinyin" in r and pd.notna(r.pinyin):
                    st.markdown(f'<p style="color: #fde047; font-size: 1.1rem; margin-top: -0.5rem; font-weight: 500;">{r.pinyin}</p>', unsafe_allow_html=True)
                    audio_html = create_audio_button_html(r.pinyin, "🔊 Listen")
                    if audio_html:
                        st.components.v1.html(audio_html, height=50)
            st.markdown('<div style="border-bottom: 1px solid rgba(212,175,55,0.2); margin: 1rem 0;"></div>', unsafe_allow_html=True)

# --------------------------------------------------
# FLASHCARDS (WITH AUDIO)
# --------------------------------------------------
elif st.session_state.page == "Flashcards":
    st.title("🃏 Flashcards")

    if "card" not in st.session_state:
        st.session_state.card = RADICALS.sample(1).iloc[0]

    st.markdown(f"""
    <div class="game-card">
        <div style="color: #fde047; font-size: 1.1rem; letter-spacing: 0.15rem; font-weight: 700; margin-bottom: -0.5rem;">MANDALINK RADICAL STUDY</div>
        <div class="radical-big">{st.session_state.card.radical}</div>
    """, unsafe_allow_html=True)
    
    # Add audio button for pinyin
    if "pinyin" in st.session_state.card and pd.notna(st.session_state.card.pinyin):
        audio_html = create_audio_button_html(st.session_state.card.pinyin, "🔊 Pronunciation")
        if audio_html:
            st.components.v1.html(audio_html, height=50)

    show = st.checkbox("Show Meaning", key="flash_show")
    
    if show:
        st.markdown(f"""
        <div style="
            background: rgba(212, 175, 55, 0.1);
            border: 1px solid #D4AF37;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1.5rem 0;
        ">
            <h2 style="color: #fde047; margin: 0; font-size: 2rem;">{st.session_state.card.meaning}</h2>
            {f'<p style="color: {text_soft}; font-size: 1.2rem; margin-top: 0.5rem;">Pinyin: {st.session_state.card.pinyin}</p>' if "pinyin" in st.session_state.card and pd.notna(st.session_state.card.pinyin) else ''}
        </div>
        """, unsafe_allow_html=True)

    if st.button("Next Card ➡"):
        st.session_state.card = RADICALS.sample(1).iloc[0]
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------------------------------
# GAME 
# --------------------------------------------------
elif st.session_state.page == "Game":
    st.title("🎮 Guess the Meaning")

    if st.session_state.question is None or st.session_state.correct:
        q = RADICALS.sample(1).iloc[0]
        opts = RADICALS.sample(4)["meaning"].tolist()
        if q.meaning not in opts:
            opts[0] = q.meaning
        random.shuffle(opts)

        st.session_state.question = (q, opts)
        st.session_state.answered = False
        st.session_state.correct = False
        st.session_state.attempts = 0
        st.session_state.already_earned_xp = False

    q, opts = st.session_state.question

    st.markdown(f"""
    <div class="game-card">
        <div style="color: #fde047; font-size: 1.1rem; letter-spacing: 0.15rem; font-weight: 700; margin-bottom: -0.5rem;">MANDALINK QUIZ CHALLENGE</div>
        <div class="radical-big">{q.radical}</div>
    """, unsafe_allow_html=True)
    
    # Show attempt counter if user has tried
    if st.session_state.attempts > 0:
        st.caption(f"Attempt #{st.session_state.attempts + 1}")

    for opt in opts:
        if st.button(opt, key=f"game_{opt}", disabled=st.session_state.correct):
            st.session_state.attempts += 1
            
            if opt == q.meaning:
                # Correct answer!
                if not st.session_state.already_earned_xp:
                    # First time getting it right - award XP
                    update_xp(st.session_state.user, 10)
                    st.success("✅ Perfect! +10 XP")
                    st.session_state.already_earned_xp = True
                else:
                    # Got it right after retries - no XP
                    st.success("✅ Correct!")
                
                st.session_state.correct = True
            else:
                # Wrong answer - allow retry
                if st.session_state.attempts == 1:
                    st.error("❌ Not quite! Try again")
                else:
                    st.error("❌ Keep trying! You'll get it")

    if st.session_state.correct:
        if st.button("➡ Next Question"):
            st.session_state.question = None
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# TIMED MODE 
# --------------------------------------------------
elif st.session_state.page == "Timed Mode":
    st.title("⏱️ Timed Mode")

    # RESULTS SCREEN
    if st.session_state.timed_results:
        st.markdown('<div class="game-card">', unsafe_allow_html=True)
        st.markdown('<h1 style="color: #D4AF37;">🎮 Challenge Complete!</h1>', unsafe_allow_html=True)
        
        acc = (st.session_state.timed_correct / st.session_state.timed_total * 100) if st.session_state.timed_total > 0 else 0
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-around; gap: 1rem; margin: 2rem 0;">
            <div style="background: rgba(212, 175, 55, 0.15); border: 2px solid #D4AF37; padding: 1.5rem; border-radius: 16px; text-align: center; flex: 1;">
                <div style="color: {text_soft}; font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1rem;">⭐ Final Score</div>
                <div style="color: #ffffff; font-size: 2.2rem; font-weight: 900; margin-top: 0.5rem;">{st.session_state.timed_score}</div>
            </div>
            <div style="background: rgba(212, 175, 55, 0.15); border: 2px solid #D4AF37; padding: 1.5rem; border-radius: 16px; text-align: center; flex: 1;">
                <div style="color: {text_soft}; font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1rem;">✅ Correct</div>
                <div style="color: #ffffff; font-size: 2.2rem; font-weight: 900; margin-top: 0.5rem;">{st.session_state.timed_correct}/{st.session_state.timed_total}</div>
            </div>
            <div style="background: rgba(212, 175, 55, 0.15); border: 2px solid #D4AF37; padding: 1.5rem; border-radius: 16px; text-align: center; flex: 1;">
                <div style="color: {text_soft}; font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1rem;">🎯 Accuracy</div>
                <div style="color: #ffffff; font-size: 2.2rem; font-weight: 900; margin-top: 0.5rem;">{int(acc)}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
            
        st.markdown(f"### You earned **{st.session_state.timed_correct * 15} XP** this round!")
        
        if st.button("🔄 Play Again", type="primary", use_container_width=True):
            st.session_state.timed_results = False
            st.session_state.timer_running = True
            st.session_state.time_left = 60
            st.session_state.timed_score = 0
            st.session_state.timed_correct = 0
            st.session_state.timed_total = 0
            st.session_state.question = None
            st.session_state.timed_feedback = None
            st.rerun()
            
        if st.button("🏠 Back to Learn", use_container_width=True):
            st.session_state.page = "Learn"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    # START SCREEN
    if not st.session_state.timer_running:
        st.markdown('<div class="game-card">', unsafe_allow_html=True)
        st.markdown(f"""
        <h2 style="color: #D4AF37;">Are you ready?</h2>
        <p style="color: {text_soft};">You have 60 seconds to identify as many radicals as possible. Each correct answer is worth 15 XP!</p>
        """, unsafe_allow_html=True)
        if st.button("🚀 Start 60s Challenge", type="primary", use_container_width=True):
            st.session_state.timer_running = True
            st.session_state.time_left = 60
            st.session_state.timed_score = 0
            st.session_state.timed_correct = 0
            st.session_state.timed_total = 0
            st.session_state.question = None
            st.session_state.timed_feedback = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ACTIVE GAME
    if st.session_state.timer_running:
        # Stats Bar
        cols = st.columns([1, 1, 1])
        with cols[0]:
            st.markdown(f"### ⏳ {st.session_state.time_left}s")
        with cols[1]:
            st.markdown(f"<h3 style='text-align: center; color: #D4AF37;'>Score: {st.session_state.timed_score}</h3>", unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"<h3 style='text-align: right;'>✅ {st.session_state.timed_correct}/{st.session_state.timed_total}</h3>", unsafe_allow_html=True)

        if st.session_state.question is None:
            q = RADICALS.sample(1).iloc[0]
            opts = RADICALS.sample(4)["meaning"].tolist()
            if q.meaning not in opts:
                opts[0] = q.meaning
            random.shuffle(opts)
            st.session_state.question = (q, opts)

        q, opts = st.session_state.question

        st.markdown(f"""
        <div class="game-card">
            <div style="color: #fde047; font-size: 1.1rem; letter-spacing: 0.15rem; font-weight: 700; margin-bottom: -0.5rem;">MANDALINK SPEED CHALLENGE</div>
            <div class="radical-big">{q.radical}</div>
        """, unsafe_allow_html=True)

        # Feedback Display
        if st.session_state.timed_feedback:
            st.markdown(st.session_state.timed_feedback, unsafe_allow_html=True)
            st.session_state.timed_feedback = None 

        for opt in opts:
            if st.button(opt, key=f"timed_{opt}", use_container_width=True):
                st.session_state.timed_total += 1
                if opt == q.meaning:
                    st.session_state.timed_correct += 1
                    st.session_state.timed_score += 25
                    st.session_state.timed_feedback = '<div style="color: #16a34a; font-weight: bold; margin-bottom: 1rem;">✅ Correct! +25 XP</div>'
                    update_xp(st.session_state.user, 5)
                else:
                    st.session_state.timed_feedback = '<div style="color: #dc2626; font-weight: bold; margin-bottom: 1rem;">❌ Wrong!</div>'
                
                st.session_state.question = None
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        # Timer logic
        time.sleep(1)
        st.session_state.time_left -= 1

        if st.session_state.time_left <= 0:
            st.session_state.timer_running = False
            st.session_state.timed_results = True
            st.session_state.question = None

        st.rerun()

# --------------------------------------------------
# LEADERBOARD
# --------------------------------------------------
elif st.session_state.page == "Leaderboard":
    st.title("🏆 Leaderboard")
    leaderboard_data = get_leaderboard()
    if leaderboard_data:
        df = pd.DataFrame(leaderboard_data)
        st.dataframe(df, width="stretch")
    else:
        st.info("No users yet!")

# --------------------------------------------------
# STROKE ORDER 
# --------------------------------------------------
elif st.session_state.page == "Stroke Order":
    st.title("✍️ Interactive Stroke Order")
    
    # Search bar
    search_query = st.text_input("🔍 Search radicals by meaning, pinyin, or character...", key="stroke_search")
    
    # Filter radicals based on search
    if search_query:
        filtered = RADICALS[
            RADICALS['radical'].str.contains(search_query, case=False, na=False) |
            RADICALS['meaning'].str.contains(search_query, case=False, na=False) |
            (RADICALS['pinyin'].str.contains(search_query, case=False, na=False) if 'pinyin' in RADICALS.columns else False)
        ]
    else:
        filtered = RADICALS
    
    # Mode selection
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"Showing {len(filtered)} radical(s)")
    with col2:
        mode = st.selectbox("Mode", ["Demo", "Practice"], label_visibility="collapsed")
    
    if len(filtered) == 0:
        st.warning("No radicals found matching your search.")
    else:
        # Display radicals in a grid
        cols_per_row = 3
        for i in range(0, len(filtered), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                if i + j < len(filtered):
                    radical_row = filtered.iloc[i + j]
                    # Extract only the primary character (e.g., '人' from '人 (亻)')
                    radical = radical_row['radical'][0] 
                    meaning = radical_row['meaning']
                    pinyin = radical_row.get('pinyin', '')
                    
                    with col:
                        # Create a card for each radical
                        with st.container():
                            st.markdown(f"""
                            <div style="
                                background: rgba(255, 255, 255, 0.05);
                                padding: 1.5rem;
                                border-radius: 16px;
                                text-align: center;
                                backdrop-filter: blur(8px);
                                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                                border: 1px solid rgba(212, 175, 55, 0.25);
                                margin-bottom: 1rem;
                            ">
                                <h3 style="color: #D4AF37; margin: 0; font-size: 1.2rem; font-weight: 700;">{meaning}</h3>
                                <p style="color: {text_soft}; margin: 0.25rem 0; font-size: 1rem; font-weight: 500; opacity: 0.9;">{pinyin if pinyin else ''}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Add audio button if pinyin exists
                            if pinyin and pd.notna(pinyin):
                                audio_html = create_audio_button_html(pinyin, "🔊")
                                if audio_html:
                                    st.components.v1.html(audio_html, height=50)
                            
                            # Hanzi Writer container
                            writer_id = f"writer_{i}_{j}"
                            practice_id = f"practice_{i}_{j}"
                            
                            if mode == "Demo":
                                # Demo mode - animated stroke order
                                st.components.v1.html(f"""
                                <!DOCTYPE html>
                                <html>
                                <head>
                                    <script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script>
                                    <style>
                                        body {{
                                            margin: 0;
                                            padding: 0;
                                            background: transparent;
                                        }}
                                        .writer-container {{
                                            display: flex;
                                            flex-direction: column;
                                            align-items: center;
                                            padding: 1.2rem;
                                            background: {panel_bg};
                                            border-radius: 16px;
                                            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                                            border: 2px solid #D4AF37;
                                        }}
                                        .controls {{
                                            margin-top: 1rem;
                                            display: flex;
                                            gap: 0.5rem;
                                        }}
                                        button {{
                                            padding: 0.5rem 1rem;
                                            border: none;
                                            border-radius: 8px;
                                            background: #b91c1c;
                                            color: white;
                                            cursor: pointer;
                                            font-size: 0.9rem;
                                            font-weight: 600;
                                            transition: all 0.2s;
                                        }}
                                        button:hover {{
                                            background: #991b1b;
                                            transform: translateY(-2px);
                                            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                                        }}
                                        button:active {{
                                            transform: translateY(0);
                                        }}
                                    </style>
                                </head>
                                <body>
                                    <div class="writer-container">
                                        <svg id="{writer_id}" xmlns="http://www.w3.org/2000/svg" width="200" height="200">
                                            <line x1="0" y1="0" x2="200" y2="200" stroke="#DDD" />
                                            <line x1="200" y1="0" x2="0" y2="200" stroke="#DDD" />
                                            <line x1="100" y1="0" x2="100" y2="200" stroke="#DDD" />
                                            <line x1="0" y1="100" x2="200" y2="100" stroke="#DDD" />
                                        </svg>
                                        <div class="controls">
                                            <button onclick="writer.animateCharacter()">▶ Animate</button>
                                            <button onclick="writer.showCharacter()">👁 Show</button>
                                            <button onclick="writer.hideCharacter()">🚫 Hide</button>
                                        </div>
                                    </div>
                                    <script>
                                        var writer = HanziWriter.create('{writer_id}', '{radical}', {{
                                            width: 200,
                                            height: 200,
                                            padding: 5,
                                            strokeAnimationSpeed: 2,
                                            delayBetweenStrokes: 200,
                                            strokeColor: '#b91c1c',
                                            radicalColor: '#dc2626',
                                            showOutline: true,
                                            showCharacter: false
                                        }});
                                        
                                        // Auto-animate on load
                                        setTimeout(() => writer.animateCharacter(), 500);
                                    </script>
                                </body>
                                </html>
                                """, height=320)
                            else:
                                # Practice mode - interactive drawing
                                st.components.v1.html(f"""
                                <!DOCTYPE html>
                                <html>
                                <head>
                                    <script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script>
                                    <style>
                                        body {{
                                            margin: 0;
                                            padding: 0;
                                            background: transparent;
                                        }}
                                        .practice-container {{
                                            display: flex;
                                            flex-direction: column;
                                            align-items: center;
                                            padding: 1.2rem;
                                            background: {panel_bg};
                                            border-radius: 16px;
                                            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                                            border: 2px solid #D4AF37;
                                        }}
                                        .controls {{
                                            margin-top: 1rem;
                                            display: flex;
                                            gap: 0.5rem;
                                            flex-wrap: wrap;
                                            justify-content: center;
                                        }}
                                        button {{
                                            padding: 0.5rem 1rem;
                                            border: none;
                                            border-radius: 8px;
                                            background: #b91c1c;
                                            color: white;
                                            cursor: pointer;
                                            font-size: 0.85rem;
                                            font-weight: 600;
                                            transition: all 0.2s;
                                        }}
                                        button:hover {{
                                            background: #991b1b;
                                            transform: translateY(-2px);
                                            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                                        }}
                                        button:disabled {{
                                            background: #ccc;
                                            cursor: not-allowed;
                                            transform: none;
                                        }}
                                        .success {{
                                            background: #16a34a;
                                        }}
                                        .success:hover {{
                                            background: #15803d;
                                        }}
                                        #message {{
                                            margin-top: 0.5rem;
                                            font-weight: 600;
                                            min-height: 1.5rem;
                                        }}
                                    </style>
                                </head>
                                <body>
                                    <div class="practice-container">
                                        <svg id="{practice_id}" xmlns="http://www.w3.org/2000/svg" width="200" height="200">
                                            <line x1="0" y1="0" x2="200" y2="200" stroke="#DDD" />
                                            <line x1="200" y1="0" x2="0" y2="200" stroke="#DDD" />
                                            <line x1="100" y1="0" x2="100" y2="200" stroke="#DDD" />
                                            <line x1="0" y1="100" x2="200" y2="100" stroke="#DDD" />
                                        </svg>
                                        <div id="message"></div>
                                        <div class="controls">
                                            <button id="hint-btn" onclick="quiz.showHint()">💡 Hint</button>
                                            <button id="reset-btn" onclick="resetQuiz()">🔄 Reset</button>
                                        </div>
                                    </div>
                                    <script>
                                        var writer = HanziWriter.create('{practice_id}', '{radical}', {{
                                            width: 200,
                                            height: 200,
                                            padding: 5,
                                            showOutline: true,
                                            strokeColor: '#16a34a',
                                            radicalColor: '#dc2626'
                                        }});
                                        
                                        var quiz = writer.quiz({{
                                            onMistake: function(strokeData) {{
                                                document.getElementById('message').innerHTML = '<span style="color: #dc2626;">❌ Try again!</span>';
                                            }},
                                            onCorrectStroke: function(strokeData) {{
                                                document.getElementById('message').innerHTML = '<span style="color: #16a34a;">✓ Good!</span>';
                                            }},
                                            onComplete: function(summaryData) {{
                                                document.getElementById('message').innerHTML = '<span style="color: #16a34a;">🎉 Perfect!</span>';
                                                document.getElementById('hint-btn').disabled = true;
                                                document.getElementById('reset-btn').className = 'success';
                                            }}
                                        }});
                                        
                                        function resetQuiz() {{
                                            quiz.cancel();
                                            quiz = writer.quiz({{
                                                onMistake: function(strokeData) {{
                                                    document.getElementById('message').innerHTML = '<span style="color: #dc2626;">❌ Try again!</span>';
                                                }},
                                                onCorrectStroke: function(strokeData) {{
                                                    document.getElementById('message').innerHTML = '<span style="color: #16a34a;">✓ Good!</span>';
                                                }},
                                                onComplete: function(summaryData) {{
                                                    document.getElementById('message').innerHTML = '<span style="color: #16a34a;">🎉 Perfect!</span>';
                                                    document.getElementById('hint-btn').disabled = true;
                                                    document.getElementById('reset-btn').className = 'success';
                                                }}
                                            }});
                                            document.getElementById('message').innerHTML = '';
                                            document.getElementById('hint-btn').disabled = false;
                                            document.getElementById('reset-btn').className = '';
                                        }}
                                    </script>
                                </body>
                                </html>
                                """, height=340)
    
    # Instructions
    st.markdown("---")
    st.markdown("""
    ### 📚 How to Use
    
    **Demo Mode:**
    - Click **▶ Animate** to see the stroke order animation
    - Click **👁 Show** to reveal the complete character
    - Click **🚫 Hide** to hide the character
    
    **Practice Mode:**
    - Draw the radical stroke by stroke in the correct order
    - Click **💡 Hint** if you get stuck
    - Click **🔄 Reset** to try again
    - Complete all strokes correctly to finish!
    """)

# --------------------------------------------------
# AI HELP
# --------------------------------------------------
elif st.session_state.page == "AI Help":
    st.title("🤖 AI Radical Helper")
    q = st.text_area("Ask about a radical")

    if st.button("Ask"):
        with st.spinner("Thinking..."):
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a specialized assistant for a Chinese Radicals learning app. Your expertise is restricted to Chinese characters (Hanzi), radicals, pinyin, tones, Chinese grammar, culture related to language, and general linguistics. If a user asks a question outside of these topics (e.g., mathematics, coding, politics, general advice), politely explain that your purpose is solely to assist with Chinese language learning and decline to answer."},
                    {"role": "user", "content": q}
                ]
            )
        st.success(res.choices[0].message.content)
