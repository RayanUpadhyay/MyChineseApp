import streamlit as st
import pandas as pd
import random
import time
import base64
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
_bg_css = "linear-gradient(135deg, #F5EDE3 0%, #EDE0D4 100%)"
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
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;700;900&display=swap');

html, body, [class*="css"] {{
    font-family: 'Noto Serif SC', SimSun, '宋体', serif;
    color: #5C0E0E !important;
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
    color: #6B0000 !important;
    font-family: 'Noto Serif SC', serif;
    font-weight: 700 !important;
}}

/* Form labels */
label {{
    color: #8B1A1A !important;
    font-weight: 600 !important;
}}

/* Placeholders */
input::placeholder, textarea::placeholder {{
    color: #A07070 !important;
    -webkit-text-fill-color: #A07070 !important;
}}

/* Body text */
.stMarkdown p, .stMarkdown li {{
    color: #5C0E0E !important;
    font-size: 1.05rem;
}}

.stCaption {{
    color: #8B1A1A !important;
    opacity: 0.9;
}}

/* Notifications */
[data-testid="stNotification"] {{
    background-color: rgba(255, 255, 255, 0.85) !important;
    border: 1px solid rgba(155, 68, 68, 0.4) !important;
    border-radius: 8px !important;
}}

[data-testid="stNotification"] p {{
    color: #5C0E0E !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
}}

/* Input fields */
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] {{
    background-color: #ffffff !important;
    border: 2px solid #9B4444 !important;
    border-radius: 8px !important;
}}

div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {{
    color: #3C0A0A !important;
    background-color: #ffffff !important;
    -webkit-text-fill-color: #3C0A0A !important;
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
    border-right: 2px solid rgba(155, 68, 68, 0.18);
}}

section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: #6B0000 !important;
}}

section[data-testid="stSidebar"] button {{
    background-color: #A05555 !important;
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
    background-color: #6B0000 !important;
    color: #ffffff !important;
}}

/* ── GAME / FLASHCARD CARD ── */
.game-card {{
    background: #9B4444;
    padding: 2.5rem 2rem;
    border-radius: 16px;
    max-width: 820px;
    margin: 1.2rem auto;
    text-align: center;
    box-shadow: 0 6px 24px rgba(107, 0, 0, 0.14);
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
    color: #6B0000 !important;
    -webkit-text-fill-color: #6B0000 !important;
    background: none;
    -webkit-background-clip: unset !important;
    background-clip: unset !important;
    margin: 0 0 0.3rem 0;
    line-height: 1.1;
    font-family: 'Noto Serif SC', SimSun, serif;
}}

.home-tagline {{
    font-size: 1.2rem;
    color: #8B1A1A;
    letter-spacing: 0.05em;
    margin: 0 0 1.8rem 0;
    font-weight: 600;
}}

.home-divider {{
    width: 60px;
    height: 2px;
    background: #9B4444;
    margin: 0 auto 2rem auto;
    border-radius: 2px;
}}

.home-desc-card {{
    background: rgba(255, 255, 255, 0.22);
    border-radius: 16px;
    padding: 1.8rem 2rem;
    margin-bottom: 2rem;
}}

.home-desc {{
    font-size: 1.1rem;
    color: #5C0E0E;
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
    color: #8B1A1A;
    font-weight: 700;
    margin-bottom: 0.5rem;
}}

.feature-list {{
    color: #5C0E0E;
    font-size: 1rem;
    font-weight: 500;
    margin: 0;
}}

/* ── AUTH PAGE ── */
.auth-container {{
    max-width: 540px;
    margin: 0.5rem auto 1.5rem auto;
    padding: 1.2rem 2.5rem;
    text-align: center;
}}

.auth-title {{
    font-size: 2rem;
    font-weight: 900;
    color: #6B0000;
    margin-bottom: 0.2rem;
    font-family: 'Noto Serif SC', SimSun, serif;
}}

.auth-sub {{
    color: #8B1A1A;
    font-size: 1rem;
    margin-bottom: 0.8rem;
    font-weight: 500;
}}

/* ── TABS ── */
button[data-baseweb="tab"] {{
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    padding: 0.65rem 2.5rem !important;
    color: #ffffff !important;
    background-color: #A05555 !important;
    border-radius: 4px 4px 0 0 !important;
    border: none !important;
}}

button[data-baseweb="tab"][aria-selected="true"] {{
    background-color: #6B0000 !important;
    color: #ffffff !important;
    border-bottom: 3px solid #6B0000 !important;
}}

button[data-baseweb="tab"]:hover {{
    background-color: #8B2222 !important;
    color: #ffffff !important;
}}

/* ── PRIMARY BUTTONS ── */
.stButton > button[kind="primary"],
[data-testid="baseButton-primary"] {{
    background-color: #6B0000 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 0.65rem 1.5rem !important;
}}

.stButton > button[kind="primary"]:hover,
[data-testid="baseButton-primary"]:hover {{
    background-color: #5C0000 !important;
}}

/* ── DEFAULT BUTTONS ── */
.stButton > button {{
    background-color: #A05555 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}}

.stButton > button:hover {{
    background-color: #8B3333 !important;
    color: #ffffff !important;
}}

/* ── GAME ANSWER BUTTONS (outlined style via wrapper) ── */
.answer-opt .stButton > button {{
    background-color: #ffffff !important;
    color: #5C0E0E !important;
    border: 1.5px solid #9B4444 !important;
    border-radius: 8px !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    text-align: left !important;
}}

.answer-opt .stButton > button:hover {{
    background-color: #F5EDE3 !important;
    border-color: #6B0000 !important;
    color: #5C0E0E !important;
}}

.answer-opt .stButton > button:disabled {{
    opacity: 0.6 !important;
}}

/* Checkbox */
.stCheckbox label {{
    color: #5C0E0E !important;
}}

/* Text area */
textarea {{
    color: #3C0A0A !important;
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
    LOGO_FILE = BASE_DIR / "Mandalink (1).jpg.jpeg"
    logo_html = ""
    if LOGO_FILE.exists():
        logo_b64 = base64.b64encode(LOGO_FILE.read_bytes()).decode()
        logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" class="home-logo" alt="Mandalink Logo" />'

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
    LOGO_FILE = BASE_DIR / "Mandalink (1).jpg.jpeg"
    logo_html = ""
    if LOGO_FILE.exists():
        logo_b64 = base64.b64encode(LOGO_FILE.read_bytes()).decode()
        logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" style="width:110px;height:110px;object-fit:contain;margin-bottom:0.6rem;" alt="Logo" />'

    # Back button (top-left)
    if st.button("← Back", key="auth_back_btn"):
        st.session_state.app_page = "home"
        st.rerun()

    st.markdown(f"""
    <div class="auth-container">
        <div style="text-align:center;">{logo_html}</div>
        <div class="auth-title">Mandalink</div>
        <div class="auth-sub">Chinese Radicals Simplified</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Register"])

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

        if st.button("Register", type="primary", use_container_width=True, key="auth_signup_btn"):
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
_LOGO_FILE = BASE_DIR / "Mandalink (1).jpg.jpeg"
if _LOGO_FILE.exists():
    _sidebar_logo_b64 = base64.b64encode(_LOGO_FILE.read_bytes()).decode()
    st.sidebar.markdown(
        f'<div style="text-align:center;padding:1.2rem 0 0.3rem 0;">'
        f'<img src="data:image/jpeg;base64,{_sidebar_logo_b64}" '
        f'style="width:90px;height:90px;object-fit:contain;" alt="Mandalink" /></div>',
        unsafe_allow_html=True
    )

st.sidebar.markdown(
    '<h2 style="text-align:center;color:#6B0000;margin:0.2rem 0 0 0;font-size:1.35rem;font-weight:900;">Mandalink</h2>',
    unsafe_allow_html=True
)
st.sidebar.markdown(
    '<p style="text-align:center;color:#8B1A1A;font-size:0.8rem;margin:0 0 1rem 0;">Chinese Radicals Simplified</p>',
    unsafe_allow_html=True
)

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
    st.session_state.app_page = "home"
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
    st.title("Radical Meanings")

    # Search bar
    search_query = st.text_input("Search radicals by meaning, pinyin, or character...", key="learn_search")

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
                st.markdown(
                    f'<p style="font-size:2.4rem;font-weight:700;color:#5C0E0E;margin:0.2rem 0;">{r.radical}</p>',
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown(
                    f'<h3 style="color:#8B1A1A;margin:0.2rem 0 0.1rem 0;">{r.meaning}</h3>',
                    unsafe_allow_html=True
                )
                if "pinyin" in r and pd.notna(r.pinyin):
                    st.markdown(
                        f'<p style="color:#5C0E0E;font-size:1.05rem;margin:0 0 0.3rem 0;font-weight:500;">{r.pinyin}</p>',
                        unsafe_allow_html=True
                    )
                    audio_html = create_audio_button_html(r.pinyin, "Listen")
                    if audio_html:
                        st.components.v1.html(audio_html, height=50)
            st.markdown(
                '<div style="border-bottom:1px solid rgba(155,68,68,0.22);margin:0.8rem 0;"></div>',
                unsafe_allow_html=True
            )

# --------------------------------------------------
# FLASHCARDS (WITH AUDIO)
# --------------------------------------------------
elif st.session_state.page == "Flashcards":
    st.title("Flashcards")
    st.markdown(
        "Flash cards are a fantastic way to enhance your learning! To use them effectively, "
        "start by writing a question or term on one side and the answer or definition on the other. "
        "Shuffle the cards and go through them regularly, testing yourself. You can also group them "
        "by topic for focused study sessions. Happy learning!"
    )

    if "card" not in st.session_state:
        st.session_state.card = RADICALS.sample(1).iloc[0]

    st.markdown(f"""
    <div class="game-card">
        <div style="color:#ffffff;font-size:1rem;letter-spacing:0.15rem;font-weight:700;margin-bottom:0.2rem;text-transform:uppercase;">Mandalink Radical Study</div>
        <div class="radical-big">{st.session_state.card.radical}</div>
    """, unsafe_allow_html=True)

    show = st.checkbox("Show Meaning", key="flash_show")

    if show:
        st.markdown(f"""
        <div style="
            background:rgba(255,255,255,0.18);
            border:1px solid rgba(255,255,255,0.4);
            padding:1.2rem;
            border-radius:10px;
            margin:1rem 0;
        ">
            <h2 style="color:#ffffff;margin:0;font-size:1.8rem;">{st.session_state.card.meaning}</h2>
            {f'<p style="color:#fef3c7;font-size:1.1rem;margin-top:0.4rem;">Pinyin: {st.session_state.card.pinyin}</p>' if "pinyin" in st.session_state.card and pd.notna(st.session_state.card.pinyin) else ''}
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Pronunciation and Next buttons below the card
    col_a, col_b = st.columns([3, 1])
    with col_a:
        if "pinyin" in st.session_state.card and pd.notna(st.session_state.card.pinyin):
            audio_html = create_audio_button_html(st.session_state.card.pinyin, "Pronunciation")
            if audio_html:
                st.components.v1.html(audio_html, height=55)
    with col_b:
        if st.button("Next >", key="flash_next"):
            st.session_state.card = RADICALS.sample(1).iloc[0]
            st.rerun()

# --------------------------------------------------
# GAME
# --------------------------------------------------
elif st.session_state.page == "Game":
    st.title("Guess the Meaning")
    st.markdown(
        "Flash cards are a fantastic way to enhance your learning! To use them effectively, "
        "start by writing a question or term on one side and the answer or definition on the other. "
        "Shuffle the cards and go through them regularly, testing yourself. You can also group them "
        "by topic for focused study sessions. Happy learning!"
    )

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
        <div style="color:#ffffff;font-size:1rem;letter-spacing:0.15rem;font-weight:700;margin-bottom:0.2rem;text-transform:uppercase;">Mandalink Quiz Challenge</div>
        <div class="radical-big">{q.radical}</div>
    </div>
    """, unsafe_allow_html=True)

    # Show attempt counter if user has tried
    if st.session_state.attempts > 0:
        st.caption(f"Attempt #{st.session_state.attempts + 1}")

    st.markdown(
        '<p style="color:#5C0E0E;font-weight:600;margin:0.8rem 0 0.3rem 0;">Select one of the options below</p>',
        unsafe_allow_html=True
    )

    for opt in opts:
        st.markdown('<div class="answer-opt">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.correct:
        _, col_next = st.columns([3, 1])
        with col_next:
            if st.button("Next >", key="game_next"):
                st.session_state.question = None
                st.rerun()

# --------------------------------------------------
# TIMED MODE
# --------------------------------------------------
elif st.session_state.page == "Timed Mode":
    st.title("Timed Mode")

    # RESULTS SCREEN
    if st.session_state.timed_results:
        st.markdown('<div class="game-card">', unsafe_allow_html=True)
        st.markdown('<h1 style="color:#ffffff;">🎮 Challenge Complete!</h1>', unsafe_allow_html=True)

        acc = (st.session_state.timed_correct / st.session_state.timed_total * 100) if st.session_state.timed_total > 0 else 0

        st.markdown(f"""
        <div style="display:flex;justify-content:space-around;gap:1rem;margin:2rem 0;">
            <div style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.35);padding:1.5rem;border-radius:12px;text-align:center;flex:1;">
                <div style="color:#ffffff;font-size:0.85rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1rem;">⭐ Final Score</div>
                <div style="color:#ffffff;font-size:2.2rem;font-weight:900;margin-top:0.5rem;">{st.session_state.timed_score}</div>
            </div>
            <div style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.35);padding:1.5rem;border-radius:12px;text-align:center;flex:1;">
                <div style="color:#ffffff;font-size:0.85rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1rem;">✅ Correct</div>
                <div style="color:#ffffff;font-size:2.2rem;font-weight:900;margin-top:0.5rem;">{st.session_state.timed_correct}/{st.session_state.timed_total}</div>
            </div>
            <div style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.35);padding:1.5rem;border-radius:12px;text-align:center;flex:1;">
                <div style="color:#ffffff;font-size:0.85rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1rem;">🎯 Accuracy</div>
                <div style="color:#ffffff;font-size:2.2rem;font-weight:900;margin-top:0.5rem;">{int(acc)}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            f'<p style="color:#ffffff;font-size:1.1rem;">You earned <strong>{st.session_state.timed_correct * 15} XP</strong> this round!</p>',
            unsafe_allow_html=True
        )

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
        st.markdown("""
        <h2 style="color:#ffffff;">Are you ready?</h2>
        <p style="color:#fef3c7;">You have 60 seconds to identify as many radicals as possible. Each correct answer is worth 15 XP!</p>
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
            st.markdown(f'<h3 style="color:#6B0000;">⏳ {st.session_state.time_left}s</h3>', unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f'<h3 style="text-align:center;color:#6B0000;">Score: {st.session_state.timed_score}</h3>', unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f'<h3 style="text-align:right;color:#6B0000;">✅ {st.session_state.timed_correct}/{st.session_state.timed_total}</h3>', unsafe_allow_html=True)

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
            <div style="color:#ffffff;font-size:1rem;letter-spacing:0.15rem;font-weight:700;margin-bottom:0.2rem;text-transform:uppercase;">Mandalink Speed Challenge</div>
            <div class="radical-big">{q.radical}</div>
        """, unsafe_allow_html=True)

        # Feedback Display
        if st.session_state.timed_feedback:
            st.markdown(st.session_state.timed_feedback, unsafe_allow_html=True)
            st.session_state.timed_feedback = None

        for opt in opts:
            st.markdown('<div class="answer-opt">', unsafe_allow_html=True)
            if st.button(opt, key=f"timed_{opt}", use_container_width=True):
                st.session_state.timed_total += 1
                if opt == q.meaning:
                    st.session_state.timed_correct += 1
                    st.session_state.timed_score += 25
                    st.session_state.timed_feedback = '<div style="color:#16a34a;font-weight:bold;margin-bottom:0.5rem;">✅ Correct! +25 XP</div>'
                    update_xp(st.session_state.user, 5)
                else:
                    st.session_state.timed_feedback = '<div style="color:#dc2626;font-weight:bold;margin-bottom:0.5rem;">❌ Wrong!</div>'

                st.session_state.question = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

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
    st.title("Leaderboard")
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
    st.title("Interactive Stroke Order")

    # Search bar
    search_query = st.text_input("Search radicals by meaning, pinyin, or character...", key="stroke_search")

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
                                background:rgba(255,255,255,0.42);
                                padding:1.2rem;
                                border-radius:12px;
                                text-align:center;
                                border:1px solid rgba(155,68,68,0.22);
                                margin-bottom:1rem;
                            ">
                                <h3 style="color:#8B1A1A;margin:0;font-size:1.1rem;font-weight:700;">{meaning}</h3>
                                <p style="color:#5C0E0E;margin:0.2rem 0;font-size:0.95rem;font-weight:500;">{pinyin if pinyin else ''}</p>
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
                                            background: #ffffff;
                                            border-radius: 12px;
                                            box-shadow: 0 4px 16px rgba(107,0,0,0.1);
                                            border: 1.5px solid #C8A0A0;
                                        }}
                                        .controls {{
                                            margin-top: 1rem;
                                            display: flex;
                                            gap: 0.5rem;
                                        }}
                                        button {{
                                            padding: 0.5rem 1rem;
                                            border: none;
                                            border-radius: 6px;
                                            background: #9B4444;
                                            color: white;
                                            cursor: pointer;
                                            font-size: 0.9rem;
                                            font-weight: 600;
                                            transition: all 0.2s;
                                        }}
                                        button:hover {{
                                            background: #6B0000;
                                            transform: translateY(-2px);
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
                                            strokeColor: '#9B4444',
                                            radicalColor: '#6B0000',
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
                                            background: #ffffff;
                                            border-radius: 12px;
                                            box-shadow: 0 4px 16px rgba(107,0,0,0.1);
                                            border: 1.5px solid #C8A0A0;
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
                                            border-radius: 6px;
                                            background: #9B4444;
                                            color: white;
                                            cursor: pointer;
                                            font-size: 0.85rem;
                                            font-weight: 600;
                                            transition: all 0.2s;
                                        }}
                                        button:hover {{
                                            background: #6B0000;
                                            transform: translateY(-2px);
                                            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
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
                                            radicalColor: '#9B4444'
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
    st.title("AI Radical Helper")
    q = st.text_area("Ask about a radical")

    if st.button("Ask", type="primary"):
        with st.spinner("Thinking..."):
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a specialized assistant for a Chinese Radicals learning app. Your expertise is restricted to Chinese characters (Hanzi), radicals, pinyin, tones, Chinese grammar, culture related to language, and general linguistics. If a user asks a question outside of these topics (e.g., mathematics, coding, politics, general advice), politely explain that your purpose is solely to assist with Chinese language learning and decline to answer."},
                    {"role": "user", "content": q}
                ]
            )
        st.success(res.choices[0].message.content)
