import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from pptx import Presentation
from gtts import gTTS
import io
import json
import os
import uuid

# --- PAGE SETUP ---
st.set_page_config(page_title="Spark AI", page_icon="⚡", layout="wide")

# --- API SETUP ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Missing GEMINI_API_KEY! Please add it in your Streamlit Cloud Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- FOCUS MODES (Strict No-Slang Rule) ---
NO_SLANG_RULE = " Speak clearly, naturally, and respectfully. Never use slang words like bestie, bro, fam, or bestie-style talk."

PERSONALITIES = {
    "🤖 Helpful Sidekick": "You are Spark, a helpful and intelligent AI assistant." + NO_SLANG_RULE,
    "🧙‍♂️ Coding Wizard": "You are Spark, an elite software architect. Output clean, well-structured code with brief explanations." + NO_SLANG_RULE,
    "🧠 Strict Logic Teacher": "You are Spark, an academic tutor. Focus on step-by-step logic and clear explanations." + NO_SLANG_RULE,
    "⚡ Sharp & Direct": "You are Spark, a witty, sharp, and straight-to-the-point AI assistant." + NO_SLANG_RULE,
    "🃏 Clever Humor": "You are Spark, a clever companion. Use smart analogies and light humor." + NO_SLANG_RULE
}

# --- MULTI-THREAD SESSION STATE ---
if "threads" not in st.session_state:
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
            model="gemini-2.5-flash",
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
        model="gemini-2.5-flash",
        contents=gemini_contents,
        config=types.GenerateContentConfig(system_instruction=system_instruction)
    )
    return {"role": "assistant", "content": response.text}

# --- SIDEBAR CONTROLS & CHAT THREADS ---
with st.sidebar:
    st.title("⚡ Spark AI")
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

    if len(st.session_state.threads) > 1:
        if st.button("🗑️ Delete Current Thread", use_container_width=True):
            del st.session_state.threads[st.session_state.current_thread_id]
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

# --- VOICE & TEXT INPUTS ---
st.divider()
voice_audio = st.audio_input("🎙️ Voice Chat (Record a message to send automatically)")

prompt_data = st.chat_input(
    "Message Spark, or click + to attach images & files...",
    accept_file=True,
    file_type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "csv", "py", "md"]
)

# --- PROCESS NEW INPUT ---
user_text = ""
uploaded_file = None
audio_bytes_to_send = None

if prompt_data:
    user_text = prompt_data.text
    if prompt_data.files:
        uploaded_file = prompt_data.files[0]
elif voice_audio is not None:
    raw_audio = voice_audio.getvalue()
    if raw_audio != st.session_state.last_processed_audio:
        st.session_state.last_processed_audio = raw_audio
        audio_bytes_to_send = raw_audio
        user_text = "🎙️ *[Voice Message]*"

if user_text or uploaded_file or audio_bytes_to_send:
    if len(active_thread["messages"]) == 0 and user_text:
        clean_title = user_text.replace("🎙️ *[Voice Message]*", "Voice Chat").strip()
        active_thread["title"] = (clean_title[:28] + "...") if len(clean_title) > 28 else clean_title

    user_msg = {"role": "user", "content": user_text or "Analyze this attachment."}
    gemini_contents = []

    if uploaded_file:
        file_ext = uploaded_file.name.split(".")[-1].lower()
        if file_ext in ["png", "jpg", "jpeg", "webp"]:
            img = Image.open(uploaded_file)
            user_msg["image"] = img
            gemini_contents.append(img)
        else:
            user_msg["file_name"] = uploaded_file.name
            file_bytes = uploaded_file.getvalue()
            mime = "application/pdf" if file_ext == "pdf" else "text/plain"
            gemini_contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime))

    if audio_bytes_to_send:
        gemini_contents.append(types.Part.from_bytes(data=audio_bytes_to_send, mime_type="audio/wav"))
        gemini_contents.append("Listen to the user's voice message and respond directly to what they asked.")
    elif user_text:
        gemini_contents.append(user_text)

    active_thread["messages"].append(user_msg)

    with st.spinner("Spark is thinking..."):
        reply_msg = get_spark_reply(action_mode, PERSONALITIES[selected_mood], user_text, gemini_contents)
        active_thread["messages"].append(reply_msg)
        if auto_read and reply_msg.get("content"):
            new_idx = len(active_thread["messages"]) - 1
