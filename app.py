import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client
from PIL import Image
from pptx import Presentation
from gtts import gTTS
from duckduckgo_search import DDGS
import matplotlib.pyplot as plt
import base64
import asyncio
import edge_tts
import io
import json
import os
import unicodedata
import urllib.parse
import urllib.request
import uuid

# --- PAGE SETUP ---
st.set_page_config(page_title="Spark AI", page_icon="⚡", layout="wide")

# --- API & SUPABASE SETUP ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Missing GEMINI_API_KEY! Please add it in your Streamlit Cloud Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

PREFERRED_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]

def get_available_chat_models():
    return PREFERRED_MODELS

supabase = None
supa_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
supa_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
if supa_url and supa_key:
    try:
        supabase = create_client(supa_url, supa_key)
    except Exception:
        supabase = None

# --- AUTHENTICATION GATE (Stay Signed In) ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if not st.session_state.user_email and supabase and "rt" in st.query_params:
    try:
        refreshed = supabase.auth.refresh_session(st.query_params["rt"])
        if refreshed and refreshed.user:
            st.session_state.user_email = refreshed.user.email
            if refreshed.session:
                st.query_params["rt"] = refreshed.session.refresh_token
    except Exception:
        st.query_params.clear()

# --- PROFILE SYNC (LOADS SAVED THEME & AVATARS BEFORE RENDERING UI) ---
def load_profile_from_supabase():
    if not supabase or not st.session_state.get("user_email") or st.session_state.user_email == "guest@local":
        return "💎", "⚡", "🌌 Dark UI"
    try:
        res = (
            supabase.table("spark_profiles")
            .select("*")
            .eq("user_email", st.session_state.user_email)
            .execute()
        )
        if res.data:
            row = next(iter(res.data))
            return (
                row.get("user_avatar") or "💎",
                row.get("bot_avatar") or "⚡",
                row.get("app_theme") or "🌌 Dark UI",
            )
    except Exception:
        pass
    return "💎", "⚡", "🌌 Dark UI"

def save_profile_to_supabase(u_av, b_av, theme_name):
    if not supabase or not st.session_state.get("user_email") or st.session_state.user_email == "guest@local":
        return
    try:
        supabase.table("spark_profiles").upsert({
            "user_email": st.session_state.user_email,
            "user_avatar": u_av,
            "bot_avatar": b_av,
            "app_theme": theme_name,
        }).execute()
    except Exception as e:
        st.warning(f"Could not save settings to cloud: {e}")

if "app_theme" not in st.session_state:
    st.session_state.app_theme = "🌌 Dark UI"
if "user_avatar" not in st.session_state:
    st.session_state.user_avatar = "💎"
if "bot_avatar" not in st.session_state:
    st.session_state.bot_avatar = "⚡"

if st.session_state.get("user_email") and not st.session_state.get("profile_loaded"):
    u_av, b_av, saved_theme = load_profile_from_supabase()
    st.session_state.user_avatar = u_av
    st.session_state.bot_avatar = b_av
    st.session_state.app_theme = saved_theme
    st.session_state.profile_loaded = True

# --- THEME ENGINE (Dark, Dark UI, Light, Light UI) ---
THEMES = {
    "🌌 Dark UI": {
        "bg": "radial-gradient(circle at top right, #111827, #090d16 75%)",
        "sidebar": "#0d1320",
        "text": "#f8fafc",
        "muted": "#cbd5e1",
        "card": "rgba(30, 41, 59, 0.75)",
        "border": "rgba(56, 189, 248, 0.28)",
        "input_bg": "#1e293b",
        "bottom_bg": "#090d16",
        "title_grad": "linear-gradient(90deg, #38bdf8, #facc15)",
        "btn_grad": "linear-gradient(90deg, #0284c7, #2563eb)",
        "btn_text": "#ffffff",
    },
    "🌑 Dark": {
        "bg": "#121212",
        "sidebar": "#18181b",
        "text": "#f4f4f5",
        "muted": "#d4d4d8",
        "card": "#1f1f23",
        "border": "#3f3f46",
        "input_bg": "#27272a",
        "bottom_bg": "#121212",
        "title_grad": "linear-gradient(90deg, #f4f4f5, #a1a1aa)",
        "btn_grad": "linear-gradient(90deg, #3f3f46, #52525b)",
        "btn_text": "#ffffff",
    },
    "☀️ Light": {
        "bg": "#ffffff",
        "sidebar": "#f8fafc",
        "text": "#0f172a",
        "muted": "#334155",
        "card": "#f1f5f9",
        "border": "#cbd5e1",
        "input_bg": "#ffffff",
        "bottom_bg": "#ffffff",
        "title_grad": "linear-gradient(90deg, #0f172a, #334155)",
        "btn_grad": "linear-gradient(90deg, #0f172a, #1e293b)",
        "btn_text": "#ffffff",
    },
    "✨ Light UI": {
        "bg": "linear-gradient(135deg, #f0f9ff 0%, #e0e7ff 50%, #fdf4ff 100%)",
        "sidebar": "rgba(255, 255, 255, 0.88)",
        "text": "#0f172a",
        "muted": "#334155",
        "card": "rgba(255, 255, 255, 0.85)",
        "border": "rgba(59, 130, 246, 0.3)",
        "input_bg": "#ffffff",
        "bottom_bg": "#eef2ff",
        "title_grad": "linear-gradient(90deg, #0284c7, #7c3aed)",
        "btn_grad": "linear-gradient(90deg, #0284c7, #6366f1)",
        "btn_text": "#ffffff",
    },
}

if st.session_state.app_theme not in THEMES:
    st.session_state.app_theme = "🌌 Dark UI"

t = THEMES[st.session_state.app_theme]

st.markdown(f"""
<style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background: {t['bg']} !important;
        color: {t['text']} !important;
    }}
    section[data-testid="stSidebar"] {{
        background: {t['sidebar']} !important;
        border-right: 1px solid {t['border']} !important;
    }}
    .stApp p, .stApp span, .stApp label, .stApp div,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    [data-testid="stWidgetLabel"] p {{
        color: {t['text']} !important;
    }}
    [data-testid="stCaptionContainer"] p {{
        color: {t['muted']} !important;
    }}
    h1, h2, h3 {{
        background: {t['title_grad']} !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
    }}
    input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div {{
        background-color: {t['input_bg']} !important;
        color: {t['text']} !important;
        border-color: {t['border']} !important;
    }}
    div.stButton > button[kind="primary"],
    div.stButton > button[kind="primary"] p {{
        background: {t['btn_grad']} !important;
        color: {t['btn_text']} !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }}
    div.stButton > button[kind="secondary"] {{
        background-color: {t['card']} !important;
        color: {t['text']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 10px !important;
    }}
    div[data-testid="stChatMessage"], [data-testid="stExpander"] {{
        background-color: {t['card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 14px !important;
    }}
    [data-testid="stBottom"], [data-testid="stBottom"] > div {{
        background: {t['bottom_bg']} !important;
        border-top: 1px solid {t['border']} !important;
    }}
    [data-testid="stChatInput"],
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] > div > div {{
        background-color: {t['input_bg']} !important;
        border-color: {t['border']} !important;
        border-radius: 14px !important;
    }}
    [data-testid="stChatInput"] textarea {{
        color: {t['text']} !important;
        caret-color: {t['text']} !important;
        -webkit-text-fill-color: {t['text']} !important;
        background-color: transparent !important;
    }}
    [data-testid="stChatInput"] textarea::placeholder {{
        color: {t['muted']} !important;
        -webkit-text-fill-color: {t['muted']} !important;
        opacity: 0.75 !important;
    }}
</style>
""", unsafe_allow_html=True)

if not st.session_state.user_email:
    col_l, col_mid, col_r = st.columns([1, 1.4, 1])
    with col_mid:
        theme_choice = st.selectbox(
            "🎨 Theme:",
            list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.app_theme),
        )
        if theme_choice != st.session_state.app_theme:
            st.session_state.app_theme = theme_choice
            st.rerun()

        st.title("⚡ Welcome to Spark AI")
        st.caption("Sign in to access your private AI workspace & synced chat threads.")
        auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔐 Sign In", "✨ Create Account", "🚀 Guest Mode"])
        
        with auth_tab1:
            login_email = st.text_input("Email", key="login_email")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            if st.button("Sign In", type="primary", use_container_width=True):
                if not supabase:
                    st.error("Supabase keys are missing in Secrets.")
                elif login_email and login_pass:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                        st.session_state.user_email = res.user.email
                        st.session_state.pop("profile_loaded", None)
                        if res.session:
                            st.query_params["rt"] = res.session.refresh_token
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")

        with auth_tab2:

            reg_pass = st.text_input("Password (min 6 chars)", type="password", key="reg_pass")
            if st.button("Create Account", type="primary", use_container_width=True):
                if not supabase:
                    st.error("Supabase keys are missing in Secrets.")
                elif reg_email and len(reg_pass) >= 6:
                    try:
                        res = supabase.auth.sign_up({"email": reg_email, "password": reg_pass})
                        if res.user:
                            st.session_state.user_email = res.user.email
                            st.session_state.pop("profile_loaded", None)
                            if res.session:
                                st.query_params["rt"] = res.session.refresh_token
                            st.success("Account created! Loading Spark AI...")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Sign up failed: {e}")
                else:
                    st.warning("Enter a valid email and a password with at least 6 characters.")

        with auth_tab3:
            st.info("Try Spark AI without saving threads to the cloud.")
            if st.button("Continue as Guest", use_container_width=True):
                st.session_state.user_email = "guest@local"
                st.rerun()
    st.stop()

# --- FOCUS MODES ---
NO_SLANG_RULE = " You were created by Ibrahim Muneeb Khaliq. If anyone asks who created, built, or made you, always answer that you are Spark AI, created by Ibrahim Muneeb Khaliq. Speak clearly, naturally, and respectfully. Never use slang words like bestie, bro, fam, or bestie-style talk."

PERSONALITIES = {
    "🤖 Helpful Sidekick": "You are Spark, a helpful and intelligent AI assistant." + NO_SLANG_RULE,
    "🧙‍♂️ Coding Wizard": "You are Spark, an elite software architect. Output clean, well-structured code with brief explanations." + NO_SLANG_RULE,
    "🧠 Strict Logic Teacher": "You are Spark, an academic tutor. Focus on step-by-step logic and clear explanations." + NO_SLANG_RULE,
    "⚡ Sharp & Direct": "You are Spark, a witty, sharp, and straight-to-the-point AI assistant." + NO_SLANG_RULE,
    "🃏 Clever Humor": "You are Spark, a clever companion. Use smart analogies and light humor." + NO_SLANG_RULE
}

# --- FULL UNICODE EMOJI DATABASE ---
@st.cache_data
def get_all_unicode_emojis():
    ranges = [
        (0x1F300, 0x1F5FF),
        (0x1F600, 0x1F64F),
        (0x1F680, 0x1F6FF),
        (0x1F900, 0x1F9FF),
        (0x1FA70, 0x1FAFF),
        (0x2600, 0x26FF),
        (0x2700, 0x27BF),
    ]
    emojis = []
    for start, end in ranges:
        for cp in range(start, end + 1):
            ch = chr(cp)
            try:
                name = unicodedata.name(ch).title()
                if unicodedata.category(ch) == "So":
                    emojis.append(f"{ch}  {name}")
            except ValueError:
                continue
    return emojis

ALL_EMOJIS = get_all_unicode_emojis()

def encode_avatar_image(uploaded_img):
    img = Image.open(uploaded_img).convert("RGBA")
    img.thumbnail((96, 96))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def get_valid_avatar(av_value, fallback):
    if not av_value or not isinstance(av_value, str):
        return fallback
    val = av_value.strip()
    if val.startswith("data:image/") and ";base64," in val:
        try:
            _, b64_part = val.split(";base64,", 1)
            return Image.open(io.BytesIO(base64.b64decode(b64_part)))
        except Exception:
            return fallback
    if len(val) <= 8:
        return val
    return fallback

def load_threads_from_supabase():
    if not supabase or st.session_state.user_email == "guest@local":
        return None
    try:
        res = (
            supabase.table("spark_threads")
            .select("*")
            .eq("user_email", st.session_state.user_email)
            .order("updated_at")
            .execute()
        )
        if res.data:
            loaded = {}
            for row in res.data:
                loaded[row["thread_id"]] = {
                    "title": row["title"],
                    "messages": json.loads(row["messages_json"])
                }
            return loaded
    except Exception:
        return None
    return None

def save_thread_to_supabase(thread_id, thread_data):
    if not supabase or st.session_state.user_email == "guest@local":
        return
    try:
        serializable_msgs = []
        for m in thread_data["messages"]:
            clean_m = {"role": m["role"], "content": m.get("content", "")}
            if m.get("file_name"):
                clean_m["file_name"] = m["file_name"]
            serializable_msgs.append(clean_m)

        supabase.table("spark_threads").upsert({
            "thread_id": thread_id,
            "user_email": st.session_state.user_email,
            "title": thread_data["title"],
            "messages_json": json.dumps(serializable_msgs)
        }).execute()
    except Exception:
        pass

def delete_thread_from_supabase(thread_id):
    if not supabase or st.session_state.user_email == "guest@local":
        return
    try:
        supabase.table("spark_threads").delete().eq("thread_id", thread_id).execute()
    except Exception:
        pass

# --- MULTI-THREAD SESSION STATE ---
if "threads" not in st.session_state:
    saved_threads = load_threads_from_supabase()
    if saved_threads:
        st.session_state.threads = saved_threads
        st.session_state.current_thread_id = next(iter(saved_threads))
    else:
        first_id = str(uuid.uuid4())
        st.session_state.threads = {first_id: {"title": "New Chat 1", "messages": []}}
        st.session_state.current_thread_id = first_id

if "audio_cache" not in st.session_state:
    st.session_state.audio_cache = {}
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None
if "search_results" not in st.session_state:
    st.session_state.search_results = []

if st.session_state.current_thread_id not in st.session_state.threads:
    st.session_state.current_thread_id = next(iter(st.session_state.threads))

active_thread = st.session_state.threads[st.session_state.current_thread_id]

# --- HELPER FUNCTIONS ---
def create_new_thread():
    new_id = str(uuid.uuid4())
    chat_num = len(st.session_state.threads) + 1
    st.session_state.threads[new_id] = {"title": f"New Chat {chat_num}", "messages": []}
    st.session_state.current_thread_id = new_id
    save_thread_to_supabase(new_id, st.session_state.threads[new_id])

def web_search_ddg(query, max_results=6):
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []

def generate_pptx(slides_data):
    prs = Presentation()
    for slide_info in slides_data:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = slide_info.get("title", "Slide")
        body = slide.placeholders[1].text_frame
        body.clear()
        for idx, point in enumerate(slide_info.get("bullets", [])):
            p = body.paragraphs[0] if idx == 0 else body.add_paragraph()
            p.text = str(point)
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf
def generate_chart_image(chart_spec):
    chart_type = chart_spec.get("chart_type", "bar").lower()
    title = chart_spec.get("title", "Data Chart")
    labels = [str(x) for x in chart_spec.get("labels", [])]
    values = [float(y) for y in chart_spec.get("values", [])]
    x_label = chart_spec.get("x_label", "")
    y_label = chart_spec.get("y_label", "")

    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")
    colors = ["#38bdf8", "#facc15", "#a855f7", "#34d399", "#fb7185", "#f97316"]

    if chart_type == "pie":
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            colors=colors[:len(values)],
            textprops={"color": "#f8fafc", "fontsize": 9},
        )
        for at in autotexts:
            at.set_color("#0f172a")
            at.set_fontweight("bold")
    elif chart_type == "line":
        ax.plot(labels, values, marker="o", linewidth=2.5, color="#38bdf8")
        ax.fill_between(labels, values, color="#38bdf8", alpha=0.18)
    else:
        bars = ax.bar(labels, values, color=colors[:len(values)], width=0.55)
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f"{h:g}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                color="#f8fafc",
                fontsize=9,
            )

    ax.set_title(title, color="#f8fafc", fontsize=12, fontweight="bold", pad=12)
    if chart_type != "pie":
        ax.set_xlabel(x_label, color="#cbd5e1", fontsize=9)
        ax.set_ylabel(y_label, color="#cbd5e1", fontsize=9)
        ax.tick_params(colors="#cbd5e1", labelsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.2, color="#94a3b8")
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["bottom", "left"]:
            ax.spines[spine].set_color("#475569")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)

SPARK_VOICES = {
    "👩 Female": {
        "🌸 Jenny — Warm & Friendly (US)": "en-US-JennyNeural",
        "✨ Aria — Bright & Expressive (US)": "en-US-AriaNeural",
        "👑 Sonia — Calm & Polished (UK)": "en-GB-SoniaNeural",
    },
    "👨 Male": {
        "🦁 Christopher — Deep & Authoritative (US)": "en-US-ChristopherNeural",
        "🎧 Guy — Natural & Conversational (US)": "en-US-GuyNeural",
        "⚡ Ryan — Crisp & Energetic (UK)": "en-GB-RyanNeural",
    },
}

def text_to_speech(text, cache_key, voice_id="en-US-JennyNeural"):
    full_cache_key = f"{cache_key}_{voice_id}"
    if full_cache_key not in st.session_state.audio_cache:
        clean_text = text.replace("*", "").replace("#", "").replace("`", "")[:1500]

        async def _synthesize():
            communicate = edge_tts.Communicate(clean_text, voice_id)
            audio_chunks = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.extend(chunk["data"])
            return bytes(audio_chunks)

        loop = asyncio.new_event_loop()
        try:
            st.session_state.audio_cache[full_cache_key] = loop.run_until_complete(_synthesize())
        finally:
            loop.close()
    return st.session_state.audio_cache[full_cache_key]



def generate_with_fallback(contents, config):
    models_to_try = get_available_chat_models()
    if st.session_state.get("working_model") in models_to_try:
        wm = st.session_state["working_model"]
        models_to_try = [wm] + [m for m in models_to_try if m != wm]

    last_error = None
    for model_name in models_to_try:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            st.session_state["working_model"] = model_name
            return res
        except Exception as e:
            last_error = e
            err_str = str(e)
            if any(code in err_str for code in ["503", "429", "404", "400", "UNAVAILABLE", "NOT_FOUND"]):
                continue
            raise e
    raise last_error

def get_spark_reply(action_mode, system_instruction, user_text, gemini_contents):
    if action_mode == "🌐 Live Web Search":
        results = web_search_ddg(user_text, max_results=5)
        context_lines = [f"- {r.get('title')}: {r.get('body')} ({r.get('href')})" for r in results]
        search_prompt = (
            f"User question: {user_text}\n\n"
            f"Live Web Search Results:\n" + "\n".join(context_lines) +
            "\n\nAnswer clearly using the web search results and include clickable markdown links to sources."
        )
        response = generate_with_fallback(
            contents=search_prompt,
            config=types.GenerateContentConfig(system_instruction=system_instruction)
        )
        return {"role": "assistant", "content": response.text}

    if action_mode == "🎨 Generate AI Image":
        prompt_clean = (user_text or "A futuristic glowing spark").strip()
        image_models = [
            "gemini-3.1-flash-image-preview",
            "gemini-2.5-flash-image",
            "gemini-3-pro-image-preview",
        ]
        last_img_err = ""
        for img_model in image_models:
            try:
                res = client.models.generate_content(
                    model=img_model,
                    contents=prompt_clean,
                    config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
                )
                if res.candidates and res.candidates[0].content.parts:
                    for part in res.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.data:
                            gen_img = Image.open(io.BytesIO(part.inline_data.data))
                            return {
                                "role": "assistant",
                                "content": f"Here is your generated image for: **{prompt_clean}**",
                                "image": gen_img,
                            }
            except Exception as e:
                last_img_err = str(e)
                continue

        try:
            encoded_prompt = urllib.parse.quote(prompt_clean)
            fallback_url = f"https://pollinations.ai{encoded_prompt}?width=1024&height=1024&nologo=true"
            req = urllib.request.Request(fallback_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                gen_img = Image.open(io.BytesIO(resp.read()))
                return {
                    "role": "assistant",
                    "content": f"Here is your generated image for: **{prompt_clean}**",
                    "image": gen_img,
                }
        except Exception as fallback_err:
            raise RuntimeError(f"Image generation failed ({last_img_err or fallback_err}).")

    if action_mode == "📊 Build Presentation Slide":
        ppt_prompt = (
            f"Create a 5-slide presentation about: {user_text}. "
            "Return ONLY valid JSON as a list of objects with keys 'title' (string) and 'bullets' (list of 3-4 short strings)."
        )
        response = generate_with_fallback(
            contents=ppt_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json"
            )
        )
        raw_json = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        slides_data = json.loads(raw_json)
        if isinstance(slides_data, dict) and "slides" in slides_data:
            slides_data = slides_data["slides"]
        pptx_file = generate_pptx(slides_data)
        return {
            "role": "assistant",
            "content": f"I built a **{len(slides_data)}-slide presentation** on **{user_text}**. Click below to download it:",
            "pptx_bytes": pptx_file.getvalue()
        }

    if action_mode == "📈 Create Data Chart":
        chart_prompt = (
            f"Generate structured chart data for: {user_text}. "
            "Return ONLY a JSON object with keys: "
            "'chart_type' ('bar', 'line', or 'pie'), 'title' (string), "
            "'labels' (list of strings), 'values' (list of numbers), "
            "'x_label' (string), 'y_label' (string), and 'summary' (1-2 sentence insight)."
        )
        response = generate_with_fallback(
            contents=chart_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json"
            )
        )
        raw_json = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        chart_spec = json.loads(raw_json)
        chart_img = generate_chart_image(chart_spec)
        return {
            "role": "assistant",
            "content": f"**{chart_spec.get('title', 'Chart')}**\n\n{chart_spec.get('summary', '')}",
            "image": chart_img,
        }

    response = generate_with_fallback(
        contents=gemini_contents,
        config=types.GenerateContentConfig(system_instruction=system_instruction)
    )
    return {"role": "assistant", "content": response.text}
# --- SIDEBAR CONTROLS & CHAT THREADS ---
with st.sidebar:
    st.title("⚡ Spark AI")
    st.caption(f"👤 Signed in: **{st.session_state.user_email}**")
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.user_email = None
        st.session_state.pop("threads", None)
        st.session_state.pop("profile_loaded", None)
        st.session_state.user_avatar = "💎"
        st.session_state.bot_avatar = "⚡"
        st.query_params.clear()
        st.rerun()

    st.divider()
    selected_theme = st.selectbox(
        "🎨 App Theme:",
        list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.app_theme),
    )
    if selected_theme != st.session_state.app_theme:
        st.session_state.app_theme = selected_theme
        save_profile_to_supabase(
            st.session_state.user_avatar,
            st.session_state.bot_avatar,
            selected_theme,
        )
        st.rerun()

    with st.expander("🎭 Customize Avatars (You & Spark)", expanded=False):
        av_tab1, av_tab2 = st.tabs(["👤 Your Icon", "⚡ Spark Icon"])

        with av_tab1:
            u_choice = st.selectbox(f"Browse All {len(ALL_EMOJIS)} Emojis (type to search):", ALL_EMOJIS, key="u_all_emojis")
            u_custom = st.text_input("Or paste any emoji:", key="u_custom_emoji")
            u_photo = st.file_uploader("Or upload your image:", type=["png", "jpg", "jpeg", "webp"], key="u_photo")
            if st.button("Save Your Avatar", use_container_width=True):
                if u_photo is not None:
                    st.session_state.user_avatar = encode_avatar_image(u_photo)
                elif u_custom.strip():
                    st.session_state.user_avatar = u_custom.strip()
                else:
                    st.session_state.user_avatar = next(iter(u_choice.split("  ")))
                save_profile_to_supabase(
                    st.session_state.user_avatar,
                    st.session_state.bot_avatar,
                    st.session_state.app_theme,
                )
                st.rerun()

        with av_tab2:
            b_choice = st.selectbox(f"Browse All {len(ALL_EMOJIS)} Emojis for Spark:", ALL_EMOJIS, key="b_all_emojis")
            b_custom = st.text_input("Or paste any emoji for Spark:", key="b_custom_emoji")
            b_photo = st.file_uploader("Or upload Spark image:", type=["png", "jpg", "jpeg", "webp"], key="b_photo")
            if st.button("Save Spark Avatar", use_container_width=True):
                if b_photo is not None:
                    st.session_state.bot_avatar = encode_avatar_image(b_photo)
                elif b_custom.strip():
                    st.session_state.bot_avatar = b_custom.strip()
                else:
                    st.session_state.bot_avatar = next(iter(b_choice.split("  ")))
                save_profile_to_supabase(
                    st.session_state.user_avatar,
                    st.session_state.bot_avatar,
                    st.session_state.app_theme,
                )
                st.rerun()

    st.divider()
    if st.button("➕ New Chat Thread", use_container_width=True, type="primary"):
        create_new_thread()
        st.rerun()

    st.subheader("💬 Your Chat Threads")
    thread_ids = list(st.session_state.threads.keys())
    selected_thread_id = st.radio(
        "Select a conversation:",
        options=thread_ids,
        index=thread_ids.index(st.session_state.current_thread_id),
        format_func=lambda tid: st.session_state.threads[tid]["title"],
        label_visibility="collapsed"
    )
    if selected_thread_id != st.session_state.current_thread_id:
        st.session_state.current_thread_id = selected_thread_id
        st.rerun()

    new_title = st.text_input(
        "✏️ Rename current chat:",
        value=active_thread["title"],
        key=f"rename_{st.session_state.current_thread_id}"
    )
    if new_title and new_title != active_thread["title"]:
        active_thread["title"] = new_title
        save_thread_to_supabase(st.session_state.current_thread_id, active_thread)
        st.rerun()

    if len(st.session_state.threads) > 1:
        if st.button("🗑️ Delete Current Thread", use_container_width=True):
            del_id = st.session_state.current_thread_id
            del st.session_state.threads[del_id]
            delete_thread_from_supabase(del_id)
            st.session_state.current_thread_id = next(iter(st.session_state.threads))
            st.rerun()

    st.divider()
    selected_mood = st.selectbox("Spark's Focus Mode:", list(PERSONALITIES.keys()))
    action_mode = st.radio(
        "Action Mode:",
        [
            "💬 Smart Chat & Vision",
            "🌐 Live Web Search",
            "🎨 Generate AI Image",
            "📊 Build Presentation Slide",
            "📈 Create Data Chart",
        ]
    )
    st.divider()
    selected_gender = st.radio("🎙️ Voice Gender:", list(SPARK_VOICES.keys()), horizontal=True)
    selected_voice_label = st.selectbox("🗣️ Voice & Vibe:", list(SPARK_VOICES[selected_gender].keys()))
    voice_gender = SPARK_VOICES[selected_gender][selected_voice_label]
    auto_read = st.toggle("🔊 Auto-Read Spark's Replies", value=False)
# --- MAIN HEADER ---
st.title(f"⚡ {active_thread['title']}")
st.caption(f"Current Mode: **{selected_mood}** | **{action_mode}**")

# --- CUSTOM WEB SEARCH BROWSER ---
with st.expander("🔍 Spark Custom Web Search Browser", expanded=False):
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        browser_query = st.text_input("Search the web directly inside Spark AI:", placeholder="Search news, sites, facts, tutorials...", label_visibility="collapsed")
    with s_col2:
        run_search = st.button("🔎 Search", type="primary", use_container_width=True)

    if run_search and browser_query.strip():
        with st.spinner("Searching the web..."):
            st.session_state.search_results = web_search_ddg(browser_query.strip(), max_results=6)

    if st.session_state.search_results:
        for r_idx, item in enumerate(st.session_state.search_results):
            st.markdown(f"**[{item.get('title', 'Result')}]({item.get('href', '#')})**")
            st.caption(item.get("body", ""))
            if st.button("💬 Ask Spark to Summarize This Page", key=f"sum_web_{r_idx}"):
                summary_prompt = f"Summarize and explain this web result:\nTitle: {item.get('title')}\nURL: {item.get('href')}\nSnippet: {item.get('body')}"
                active_thread["messages"].append({"role": "user", "content": f"🌐 Summarize: **{item.get('title')}**"})
                reply = get_spark_reply("💬 Smart Chat & Vision", PERSONALITIES[selected_mood], summary_prompt, [summary_prompt])
                active_thread["messages"].append(reply)
                save_thread_to_supabase(st.session_state.current_thread_id, active_thread)
                st.rerun()
            st.divider()

# --- DISPLAY ACTIVE THREAD HISTORY ---
for idx, msg in enumerate(active_thread["messages"]):
    raw_av = st.session_state.bot_avatar if msg["role"] == "assistant" else st.session_state.user_avatar
    av = get_valid_avatar(raw_av, "⚡" if msg["role"] == "assistant" else "💎")
    with st.chat_message(msg["role"], avatar=av):
        if msg.get("image"):
            st.image(msg["image"], width=420)
        if msg.get("file_name"):
            st.info(f"📎 Attached file: **{msg['file_name']}**")
        st.markdown(msg["content"])
        if msg.get("pptx_bytes"):
            st.download_button(
                label="📥 Download PowerPoint (.pptx)",
                data=msg["pptx_bytes"],
                file_name="Spark_Presentation.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                key=f"dl_{st.session_state.current_thread_id}_{idx}"
            )
        if msg["role"] == "assistant" and msg.get("content"):
            cache_key = f"{st.session_state.current_thread_id}_{idx}"
            if st.button("🔊 Read Aloud", key=f"tts_{cache_key}"):
                audio_bytes = text_to_speech(msg["content"], cache_key, voice_gender)
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)

# --- ATTACHMENTS & VOICE EXPANDER ---
with st.expander("📎 Attach Image / File or 🎙️ Record Voice", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader(
            "Upload Image or Document",
            type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "csv", "py", "md"]
        )
    with col2:
        voice_audio = st.audio_input("Record Voice Message") if hasattr(st, "audio_input") else None

# --- MAIN CHATBOX ---
user_prompt = st.chat_input("Message Spark AI...")

def build_chat_history_contents(messages, current_turn_parts):
    history_contents = []
    for m in messages[-20:]:
        role = "model" if m["role"] == "assistant" else "user"
        text = m.get("content", "")
        if text:
            history_contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
            )
    clean_parts = []
    for p in current_turn_parts:
        if isinstance(p, str):
            if p.strip():
                clean_parts.append(types.Part.from_text(text=p))
        elif isinstance(p, types.Part):
            clean_parts.append(p)
        elif p is not None:
            buf = io.BytesIO()
            p.save(buf, format="PNG")
            clean_parts.append(types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"))
    if clean_parts:
        history_contents.append(
            types.Content(role="user", parts=clean_parts)
        )
    return history_contents

# --- PROCESS VOICE OR TEXT/FILE INPUT ---
user_text = ""
gemini_contents = []
user_msg_record = {"role": "user", "content": ""}
triggered = False

if voice_audio is not None:
    audio_bytes = voice_audio.getvalue()
    if audio_bytes != st.session_state.last_processed_audio:
        st.session_state.last_processed_audio = audio_bytes
        triggered = True
        user_text = "Voice message"
        user_msg_record["content"] = "🎙️ *(Voice Message)*"
        gemini_contents.append(
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
        )

elif user_prompt:
    triggered = True
    user_text = user_prompt
    user_msg_record["content"] = user_text

    if uploaded_file is not None:
        user_msg_record["file_name"] = uploaded_file.name
        file_bytes = uploaded_file.getvalue()

        if uploaded_file.type.startswith("image/"):
            img = Image.open(io.BytesIO(file_bytes))
            user_msg_record["image"] = img
            gemini_contents.append(img)
        else:
            gemini_contents.append(
                types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=uploaded_file.type or "application/pdf"
                )
            )

    gemini_contents.append(user_text)

# --- EXECUTE GEMINI CALL & SAVE ---
if triggered:
    full_contents = build_chat_history_contents(active_thread["messages"], gemini_contents)
    active_thread["messages"].append(user_msg_record)
    if active_thread["title"].startswith("New Chat ") and user_text:
        active_thread["title"] = user_text[:30] + ("..." if len(user_text) > 30 else "")

    raw_bot_av = st.session_state.bot_avatar
    bot_av = get_valid_avatar(raw_bot_av, "⚡")
    try:
        if action_mode == "💬 Smart Chat & Vision":
            if "live_flash_models" not in st.session_state:
                blocked = ("image", "tts", "live", "embed", "aqa", "vision", "pro", "research", "computer", "robotics", "thinking")
                try:
                    found = [
                        m.name.removeprefix("models/")
                        for m in client.models.list()
                        if "flash" in m.name.lower() and not any(b in m.name.lower() for b in blocked)
                    ]
                except Exception:
                    found = []
                st.session_state["live_flash_models"] = found or PREFERRED_MODELS

            with st.chat_message("assistant", avatar=bot_av):
                def stream_gemini():
                    models_to_try = st.session_state["live_flash_models"]
                    if st.session_state.get("fast_model") in models_to_try:
                        fm = st.session_state["fast_model"]
                        models_to_try = [fm] + [m for m in models_to_try if m != fm]

                    last_err = None
                    for m_name in models_to_try:
                        try:
                            got_text = False
                            for chunk in client.models.generate_content_stream(
                                model=m_name,
                                contents=full_contents,
                                config=types.GenerateContentConfig(
                                    system_instruction=PERSONALITIES[selected_mood]
                                ),
                            ):
                                if chunk.text:
                                    got_text = True
                                    yield chunk.text
                            if got_text:
                                st.session_state["fast_model"] = m_name
                                return
                        except Exception as e:
                            last_err = e
                            continue
                    raise RuntimeError(f"Could not generate reply: {last_err}")

                full_reply = st.write_stream(stream_gemini())
                reply_msg = {"role": "assistant", "content": str(full_reply)}
        else:
            with st.spinner("⚡ Spark is working..."):
                reply_msg = get_spark_reply(
                    action_mode=action_mode,
                    system_instruction=PERSONALITIES[selected_mood],
                    user_text=user_text,
                    gemini_contents=full_contents,
                )
        active_thread["messages"].append(reply_msg)
        save_thread_to_supabase(st.session_state.current_thread_id, active_thread)
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")
