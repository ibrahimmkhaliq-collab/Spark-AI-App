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

# --- FOCUS MODES ---
NO_SLANG_RULE = " Speak clearly, naturally, and respectfully. Never use slang words like bestie, bro, fam, or bestie-style talk."

PERSONALITIES = {
    "🤖 Helpful Sidekick": "You are Spark, a helpful and intelligent AI assistant." + NO_SLANG_RULE,
    "🧙‍♂️ Coding Wizard": "You are Spark, an elite software architect. Output clean, well-structured code with brief explanations." + NO_SLANG_RULE,
    "🧠 Strict Logic Teacher": "You are Spark, an academic tutor. Focus on step-by-step logic and clear explanations." + NO_SLANG_RULE,
    "⚡ Sharp & Direct": "You are Spark, a witty, sharp, and straight-to-the-point AI assistant." + NO_SLANG_RULE,
    "🃏 Clever Humor": "You are Spark, a clever companion. Use smart analogies and light humor." + NO_SLANG_RULE
}

# --- SUPABASE SYNC HELPERS ---
def load_threads_from_supabase():
    if not supabase:
        return None
    try:
        res = supabase.table("spark_threads").select("*").order("updated_at").execute()
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
    if not supabase:
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
            "title": thread_data["title"],
            "messages_json": json.dumps(serializable_msgs)
        }).execute()
    except Exception:
        pass

def delete_thread_from_supabase(thread_id):
    if not supabase:
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
    if supabase:
        st.caption("☁️ Supabase Cloud Sync: **Connected**")

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
    active_thread["messages"].append(user_msg_record)
    if active_thread["title"].startswith("New Chat ") and user_text:
        active_thread["title"] = user_text[:30] + ("..." if len(user_text) > 30 else "")

    with st.spinner("⚡ Spark is thinking..."):
        try:
            reply_msg = get_spark_reply(
                action_mode=action_mode,
                system_instruction=PERSONALITIES[selected_mood],
                user_text=user_text,
                gemini_contents=gemini_contents
            )
            active_thread["messages"].append(reply_msg)
            save_thread_to_supabase(st.session_state.current_thread_id, active_thread)

            if auto_read and reply_msg.get("content"):
                new_idx = len(active_thread["messages"]) - 1
                cache_key = f"{st.session_state.current_thread_id}_{new_idx}"
                audio_out = text_to_speech(reply_msg["content"], cache_key)
                st.audio(audio_out, format="audio/mp3", autoplay=True)

            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
            
