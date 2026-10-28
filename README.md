Mandalink (v1)

This is the original version of Mandalink and is no longer maintained. Mandalink was rebuilt from the ground up as Mandalink2, which is what now runs at mandalink.org. Head there for the current code.

Mandalink is a web app for learning Mandarin through its 214 Kangxi radicals, the small building blocks that keep turning up inside Chinese characters. Spot the radical and you get a hint about the meaning of characters you've never seen. This repository holds the first version, written in Python with Streamlit.

Pardon the mess: this was my first GitHub repository, so it still contains a lot of old copies of the app (myprogram (13).py, myprogram_july.py, database_old2.py and friends). The current v1 code is myprogram.py, database.py and tts_helper.py.

Why it was rebuilt

Version 1 did its job as a first build, but it ran into the limits of how it was made, so instead of patching it I rewrote Mandalink from scratch.

Streamlit reruns the whole script on every click. The entire app is one ~1,400-line file, and each button press re-executes it from the top. That made it slow and made every new feature harder to add without breaking another.
No real pages or URLs. Navigation was a set of sidebar buttons that flipped a value in st.session_state, so you couldn't link to a page, use the back button, or bookmark anything.
Fighting the framework for design. The look was produced by injecting large blocks of custom CSS and raw HTML through st.markdown(..., unsafe_allow_html=True), and images had to be base64-embedded into the page.
No API. The UI, the logic and the database calls lived in the same process, so nothing else (like my personal site) could talk to Mandalink.

Mandalink2 splits the app into a React (Vite) frontend and a Java Spring Boot REST API on PostgreSQL, with proper routes, JWT auth, and room to grow. It has since gained profiles, achievements and badges, an announcement board, printable worksheets, moderation tools and an IB Chinese course section, none of which would have been practical here.

What v1 could do
Learn: browse all 214 radicals with pinyin and meaning.
Flashcards: flip through radicals one at a time.
Guess the Meaning: a multiple-choice game.
Timed Mode: answer as many as you can against the clock.
Interactive Stroke Order: guided stroke-order practice.
AI Radical Helper: ask questions about radicals, answered by Llama 3.3 70B through the Groq API.
Pronunciation: Mandarin audio generated with Microsoft Edge TTS (zh-CN-XiaoxiaoNeural) and cached in audio_cache/.
Accounts, XP and levels: register, log in and reset your password (passwords hashed with bcrypt), earn XP, and compete on a leaderboard.
Tech stack
Part	Tool
UI and app logic	Streamlit
Data	pandas, radicals.csv
Database	PostgreSQL via psycopg2 (earlier versions used CSV, then SQLite)
Auth	bcrypt
AI help	Groq (llama-3.3-70b-versatile)
Text-to-speech	edge-tts
Hosting	Render
Running it locally

Requires Python 3.11+.

bash
pip install -r requirements.txt
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
streamlit run myprogram.py

The Groq key is set directly in myprogram.py (Groq(api_key="your_api_key_here")); replace the placeholder with your own key to use AI Help. On Render the app started with start.sh, which binds Streamlit to $PORT.

Files that matter
File	What it is
myprogram.py	The app
database.py	PostgreSQL connection, users, XP and leaderboard
tts_helper.py	Edge TTS audio generation and caching
radicals.csv	The 214 radicals with pinyin and meanings
config.toml	Streamlit theme
start.sh	Start command for Render

Everything else is an older draft kept for history.

Author

Rayan Upadhyay · rayanupadhyay.com · rayanupadhyay@gmail.com
