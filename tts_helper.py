import asyncio
import edge_tts
import base64
from pathlib import Path
import hashlib

# Audio cache directory
AUDIO_DIR = Path(__file__).resolve().parent / "audio_cache"
AUDIO_DIR.mkdir(exist_ok=True)

# Chinese voice (female, natural sounding)
VOICE = "zh-CN-XiaoxiaoNeural"


async def _generate_audio(text, output_file):
    """Generate audio file using Edge TTS (async)."""
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)


def generate_audio_sync(text):
    """
    Generate audio for Chinese text (pinyin with tones).
    Returns: path to audio file
    """
    text_hash = hashlib.md5(text.encode()).hexdigest()
    audio_file = AUDIO_DIR / f"{text_hash}.mp3"

    if audio_file.exists():
        return audio_file

    try:
        asyncio.run(_generate_audio(text, str(audio_file)))
        return audio_file
    except Exception as e:
        print(f"Error generating audio for '{text}': {e}")
        return None


def get_audio_base64(text):
    """
    Generate audio and return as base64 for embedding in HTML.
    This is Streamlit Cloud compatible.
    """
    audio_file = generate_audio_sync(text)

    if audio_file and audio_file.exists():
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode()
            return audio_base64

    return None


def create_audio_button_html(text, button_text="🔊"):
    """
    Create HTML for an audio playback button.
    Returns: Complete HTML document for st.components.v1.html()
    """
    audio_base64 = get_audio_base64(text)

    if not audio_base64:
        return ""

    audio_id = hashlib.md5(text.encode()).hexdigest()[:8]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: transparent;
            }}
            .audio-btn {{
                background: #9B4444;
                border: none;
                color: white;
                padding: 0.45rem 1.2rem;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.95rem;
                font-weight: 600;
                letter-spacing: 0.02em;
                transition: all 0.2s;
                display: inline-block;
            }}
            .audio-btn:hover {{
                background: #6B0000;
                transform: translateY(-1px);
                box-shadow: 0 3px 8px rgba(107,0,0,0.2);
            }}
            .audio-btn:active {{
                transform: translateY(0);
                box-shadow: none;
            }}
        </style>
    </head>
    <body>
        <audio id="audio-{audio_id}">
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
        </audio>
        <button class="audio-btn" onclick="document.getElementById('audio-{audio_id}').play()">
            {button_text}
        </button>
    </body>
    </html>
    """

    return html
