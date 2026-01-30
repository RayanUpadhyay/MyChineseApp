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
st.set_page_config(page_title="Chinese Radicals", layout="wide")

# --------------------------------------------------
# BACKGROUND + SIDEBAR
# --------------------------------------------------
if BACKGROUND_FILE.exists():
    import base64
    encoded = base64.b64encode(BACKGROUND_FILE.read_bytes()).decode()
    st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-attachment: fixed;
    }}
    section[data-testid="stSidebar"] {{
        background-color: #b91c1c;
    }}
    </style>
    """, unsafe_allow_html=True)

# --------------------------------------------------
# GAME UI CSS (OG STYLE)
# --------------------------------------------------
st.markdown("""
<style>
.game-card {
    background: rgba(185, 28, 28, 0.92);
    padding: 2.5rem;
    border-radius: 24px;
    max-width: 720px;
    margin: auto;
    text-align: center;
    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
}

.radical-big {
    font-size: 7rem;
    font-weight: 900;
    color: #fde047;
    margin: 1.5rem 0;
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
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# GROQ
# --------------------------------------------------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

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
    "question": None,
    "answered": False,
    "correct": False,
    "attempts": 0,
    "already_earned_xp": False,
    "timer_running": False,
    "time_left": 0,
}.items():
    st.session_state.setdefault(key, val)

# --------------------------------------------------
# LOGIN / SIGNUP
# --------------------------------------------------
if not st.session_state.logged_in:
    st.title("🎓 Chinese Radicals Learning App")
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        login_username = st.text_input("Username", key="login_user")
        login_password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", type="primary"):
            if login_username and login_password:
                success, message = authenticate_user(login_username, login_password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user = login_username
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Please enter both username and password")
    
    with tab2:
        st.subheader("Create New Account")
        signup_username = st.text_input("Username", key="signup_user")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_pass")
        signup_confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
        
        if st.button("Sign Up", type="primary"):
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
                    # Display pinyin with audio button
                    st.markdown(f'<p style="color: #666; font-size: 1.1rem; margin-top: -0.5rem;">{r.pinyin}</p>', unsafe_allow_html=True)
                    audio_html = create_audio_button_html(r.pinyin, "🔊 Listen")
                    if audio_html:
                        st.components.v1.html(audio_html, height=50)
            st.markdown("---")

# --------------------------------------------------
# FLASHCARDS (WITH AUDIO)
# --------------------------------------------------
elif st.session_state.page == "Flashcards":
    st.title("🃏 Flashcards")

    if "card" not in st.session_state:
        st.session_state.card = RADICALS.sample(1).iloc[0]

    st.markdown(f"## {st.session_state.card.radical}")
    
    # Add audio button for pinyin
    if "pinyin" in st.session_state.card and pd.notna(st.session_state.card.pinyin):
        audio_html = create_audio_button_html(st.session_state.card.pinyin, "🔊 Pronunciation")
        if audio_html:
            st.components.v1.html(audio_html, height=50)

    if st.checkbox("Show meaning"):
        st.success(st.session_state.card.meaning)
        if "pinyin" in st.session_state.card and pd.notna(st.session_state.card.pinyin):
            st.info(f"Pinyin: {st.session_state.card.pinyin}")

    if st.button("Next Card"):
        st.session_state.card = RADICALS.sample(1).iloc[0]
        st.rerun()

# --------------------------------------------------
# GAME (OG STYLE WITH UNLIMITED RETRIES)
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

    st.markdown('<div class="game-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="radical-big">{q.radical}</div>', unsafe_allow_html=True)
    
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
# TIMED MODE (OG STYLE)
# --------------------------------------------------
elif st.session_state.page == "Timed Mode":
    st.title("⏱️ Timed Mode")

    if not st.session_state.timer_running:
        if st.button("Start 60s Timer"):
            st.session_state.timer_running = True
            st.session_state.time_left = 60
            st.session_state.question = None
            st.rerun()

    if st.session_state.timer_running:
        st.markdown(f"### ⏳ {st.session_state.time_left}s remaining")

        if st.session_state.question is None:
            q = RADICALS.sample(1).iloc[0]
            opts = RADICALS.sample(4)["meaning"].tolist()
            if q.meaning not in opts:
                opts[0] = q.meaning
            random.shuffle(opts)
            st.session_state.question = (q, opts)

        q, opts = st.session_state.question

        st.markdown('<div class="game-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="radical-big">{q.radical}</div>', unsafe_allow_html=True)

        for opt in opts:
            if st.button(opt, key=f"timed_{opt}"):
                if opt == q.meaning:
                    update_xp(st.session_state.user, 15)
                st.session_state.question = None
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        time.sleep(1)
        st.session_state.time_left -= 1

        if st.session_state.time_left <= 0:
            st.session_state.timer_running = False
            st.success("⏰ Time’s up!")

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
# STROKE ORDER (INTERACTIVE WITH HANZI WRITER)
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
                                background: linear-gradient(135deg, rgba(185, 28, 28, 0.95), rgba(220, 38, 38, 0.95));
                                padding: 1.5rem;
                                border-radius: 16px;
                                text-align: center;
                                box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                                margin-bottom: 1rem;
                            ">
                                <h3 style="color: #fde047; margin: 0; font-size: 1.2rem;">{meaning}</h3>
                                <p style="color: #fef3c7; margin: 0.25rem 0; font-size: 0.9rem;">{pinyin if pinyin else ''}</p>
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
                                            padding: 1rem;
                                            background: rgba(255, 255, 255, 0.95);
                                            border-radius: 12px;
                                            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
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
                                            padding: 1rem;
                                            background: rgba(255, 255, 255, 0.95);
                                            border-radius: 12px;
                                            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
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
