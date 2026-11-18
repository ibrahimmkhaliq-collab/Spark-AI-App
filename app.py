import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client
from PIL import Image
from pptx import Presentation
from gtts import gTTS
import io
import json
import os
import uuid

# --- PAGE SETUP ---
st.set_page_config(page_title="Spark AI", page_icon="⚡", layout="wide")

# --- THEME ENGINE (Dark, Dark UI, Light, Light UI) ---
if "app_theme" not in st.session_state:
    st.session_state.app_theme = "🌌 Dark UI"

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
    /* Fix ALL text, labels, radio options, and captions */
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
    /* Inputs, Textboxes, Selectboxes */
    input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div {{
        background-color: {t['input_bg']} !important;
        color: {t['text']} !important;
        border-color: {t['border']} !important;
    }}
    /* Buttons */
    div.stButton > button[kind="primary"] {{
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
    /* Chat Messages & Expander */
    div[data-testid="stChatMessage"], [data-testid="stExpander"] {{
        background-color: {t['card']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 14px !important;
    }}
    /* Fix Bottom Chatbox Container & Input */
    [data-testid="stBottom"], [data-testid="stBottom"] > div {{
        background: {t['bottom_bg']} !important;
        border-top: 1px solid {t['border']} !important;
    }}
    [data-testid="stChatInput"] {{
        background-color: {t['input_bg']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 14px !important;
    }}
    [data-testid="stChatInput"] textarea {{
        color: {t['text']} !important;
        background-color: transparent !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- API & SUPABASE SETUP ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Missing GEMINI_API_KEY! Please add it in your Streamlit Cloud Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)
MODEL_ID = "gemini-2.5-flash"

supabase = None
supa_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
supa_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
if supa_url and supa_key:
    try:
        supabase = create_client(supa_url, supa_key)
    except Exception:
        supabase = None

# --- AUTHENTICATION GATE ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None

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
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")

        with auth_tab2:
            reg_email = st.text_input("Email", key="reg_email")
            reg_pass = st.text_input("Password (min 6 chars)", type="password", key="reg_pass")
            if st.button("Create Account", type="primary", use_container_width=True):
                if not supabase:
                    st.error("Supabase keys are missing in Secrets.")
                elif reg_email and len(reg_pass) >= 6:
                    try:
                        res = supabase.auth.sign_up({"email": reg_email, "password": reg_pass})
                        if res.user:
                            st.session_state.user_email = res.user.email
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
NO_SLANG_RULE = " Speak clearly, naturally, and respectfully. Never use slang words like bestie, bro, fam, or bestie-style talk."

PERSONALITIES = {
    "🤖 Helpful Sidekick": "You are Spark, a helpful and intelligent AI assistant." + NO_SLANG_RULE,
    "🧙‍♂️ Coding Wizard": "You are Spark, an elite software architect. Output clean, well-structured code with brief explanations." + NO_SLANG_RULE,
    "🧠 Strict Logic Teacher": "You are Spark, an academic tutor. Focus on step-by-step logic and clear explanations." + NO_SLANG_RULE,
    "⚡ Sharp & Direct": "You are Spark, a witty, sharp, and straight-to-the-point AI assistant." + NO_SLANG_RULE,
    "🃏 Clever Humor": "You are Spark, a clever companion. Use smart analogies and light humor." + NO_SLANG_RULE
}

# --- USER-SCOPED SUPABASE SYNC HELPERS ---
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

def generate_pptx(slides_data):
    prs = Presentation()
    for slide_info in slides_data:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = slide_info.get("title", "Slide")
        body = slide.placeholders[1].text_frame
        body.clear()
        for idx, point in enumerate(slide_info.get("bullets", [])):
            p = body.paragraphs[0] if idx == 0 else body.add_paragraph()
            p.text = point
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf

def text_to_speech(text, cache_key):
    if cache_key not in st.session_state.audio_cache:
        clean_text = text.replace("*", "").replace("#", "").replace("`", "")
        tts = gTTS(text=clean_text[:1500], lang="en")
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.session_state.audio_cache[cache_key] = fp.getvalue()
    return st.session_state.audio_cache[cache_key]

def get_spark_reply(action_mode, system_instruction, user_text, gemini_contents):
    if action_mode == "🎨 Generate AI Image":
        result = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=user_text or "A futuristic glowing spark",
            config=types.GenerateImagesConfig(number_of_images=1)
        )
        gen_img = Image.open(io.BytesIO(result.generated_images[0].image.image_bytes))
        return {"role": "assistant", "content": f"Here is your generated image for: **{user_text}**", "image": gen_img}

    if action_mode == "📊 Build Presentation Slide":
        ppt_prompt = (
            f"Create a 5-slide presentation about: {user_text}. "
            "Return ONLY valid JSON as a list of objects with keys 'title' and 'bullets' (list of strings)."
        )
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=ppt_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json"
            )
        )
        slides_data = json.loads(response.text)
        pptx_file = generate_pptx(slides_data)
        return {
            "role": "assistant",
            "content": f"I built a **{len(slides_data)}-slide presentation** on **{user_text}**.",
            "pptx_bytes": pptx_file.getvalue()
        }

    response = client.models.generate_content(
        model=MODEL_ID,
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
        st.rerun()

    st.divider()
    selected_theme = st.selectbox(
        "🎨 App Theme:",
        list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.app_theme),
    )
    if selected_theme != st.session_state.app_theme:
        st.session_state.app_theme = selected_theme
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
        ["💬 Smart Chat & Vision", "🎨 Generate AI Image", "📊 Build Presentation Slide"]
    )
    st.divider()
    auto_read = st.toggle("🔊 Auto-Read Spark's Replies", value=False)

# --- MAIN HEADER ---
st.title(f"⚡ {active_thread['title']}")
st.caption(f"Current Mode: **{selected_mood}** | **{action_mode}**")

# --- DISPLAY ACTIVE THREAD HISTORY ---
for idx, msg in enumerate(active_thread["messages"]):
    with st.chat_message(msg["role"]):
        if msg.get("image"):
            st.image(msg["image"], width=320)
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
                audio_bytes = text_to_speech(msg["content"], cache_key)
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)

# --- ATTACHMENTS & VOICE EXPANDER ---
