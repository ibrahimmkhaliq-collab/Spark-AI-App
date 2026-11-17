import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from pptx import Presentation
from gtts import gTTS
import io
import json
import os

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

# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "audio_cache" not in st.session_state:
    st.session_state.audio_cache = {}
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

# --- HELPER FUNCTIONS ---
def generate_pptx(slides_data):
    prs = Presentation()
    for slide_info in slides_data:
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
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

def text_to_speech(text, msg_index):
    if msg_index not in st.session_state.audio_cache:
        clean_text = text.replace("*", "").replace("#", "").replace("`", "")
        tts = gTTS(text=clean_text[:1500], lang="en")
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.session_state.audio_cache[msg_index] = fp.getvalue()
    return st.session_state.audio_cache[msg_index]

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("⚡ Spark AI Controls")
    
    selected_mood = st.selectbox("Spark's Focus Mode:", list(PERSONALITIES.keys()))
    
    action_mode = st.radio(
        "Action Mode:",
        ["💬 Smart Chat & Vision", "🎨 Generate AI Image", "📊 Build Presentation Slide"]
    )
    
    st.divider()
    auto_read = st.toggle("🔊 Auto-Read Spark's Replies", value=False)
    
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.audio_cache = {}
        st.session_state.last_processed_audio = None
        st.rerun()

# --- MAIN HEADER ---
st.title("⚡ Spark AI")
st.caption(f"Current Mode: **{selected_mood}** | **{action_mode}**")

# --- DISPLAY CHAT HISTORY ---
for idx, msg in enumerate(st.session_state.messages):
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
                key=f"dl_{idx}"
            )
            
        if msg["role"] == "assistant" and msg.get("content"):
            col_audio, _ = st.columns([1, 4])
            with col_audio:
                if st.button("🔊 Read Aloud", key=f"tts_btn_{idx}"):
                    audio_bytes = text_to_speech(msg["content"], idx)
                    st.audio(audio_bytes, format="audio/mp3", autoplay=True)

# --- VOICE CHAT INPUT BAR ---
st.divider()
voice_audio = st.audio_input("🎙️ Voice Chat (Record a message to send automatically)")

# --- TEXT + INLINE '+' FILE/IMAGE ATTACHMENT BAR ---
prompt_data = st.chat_input(
    "Message Spark, or click + to attach images & files...",
    accept_file=True,
    file_type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "csv", "py", "md"]
)

# --- HANDLE INPUT (EITHER TEXT/FILE OR VOICE) ---
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
            gemini_contents.append(
                types.Part.from_bytes(data=file_bytes, mime_type=mime)
            )
            
    if audio_bytes_to_send:
        gemini_contents.append(
            types.Part.from_bytes(data=audio_bytes_to_send, mime_type="audio/wav")
        )
        gemini_contents.append("Listen to the user's voice message and respond directly to what they asked.")
    elif user_text:
        gemini_contents.append(user_text)

    st.session_state.messages.append(user_msg)
    with st.chat_message("user"):
        if user_msg.get("image"):
            st.image(user_msg["image"], width=320)
        if user_msg.get("file_name"):
            st.info(f"📎 Attached file: **{user_msg['file_name']}**")
        st.markdown(user_msg["content"])

    # --- GENERATE SPARK'S RESPONSE ---
    with st.chat_message("assistant"):
        with st.spinner("Spark is thinking..."):
            try:
                system_instruction = PERSONALITIES[selected_mood]
                
                # MODE 1: IMAGE GENERATION
                if action_mode == "🎨 Generate AI Image":
                    result = client.models.generate_images(
                        model="imagen-3.0-generate-002",
                        prompt=user_text or "A futuristic glowing spark",
                        config=types.GenerateImagesConfig(number_of_images=1)
                    )
                    gen_img = Image.open(io.BytesIO(result.generated_images[0].image.image_bytes))
                    st.image(gen_img, caption=user_text)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Here is your generated image for: **{user_text}**",
                        "image": gen_img
                    })

                # MODE 2: PRESENTATION BUILDER
                elif action_mode == "📊 Build Presentation Slide":
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
                    summary = f"I built a **{len(slides_data)}-slide presentation** on **{user_text}**."
                    st.markdown(summary)
                    st.download_button(
                        label="📥 Download PowerPoint (.pptx)",
                        data=pptx_file,
                        file_name="Spark_Presentation.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": summary,
                        "pptx_bytes": pptx_file.getvalue()
                    })

                # MODE 3: SMART CHAT, VISION, FILES & VOICE
                else:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=gemini_contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction
                        )
                    )
                    reply_text = response.text
                    st.markdown(reply_text)
                    
                    new_idx = len(st.session_state.messages)
