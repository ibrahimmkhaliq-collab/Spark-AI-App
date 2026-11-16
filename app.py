import os
import json
import base64
import urllib.parse
import streamlit as st
from groq import Groq
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from streamlit.runtime.scriptrunner import get_script_run_ctx

# 1. Page Configuration Framework Setup
st.set_page_config(page_title="Spark AI Creator Studio", page_icon="⚡", layout="centered")

# 2. Visual Aesthetic and Layout Design
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stTextInput>div>div>input { border-radius: 20px; border: 1px solid #cbd5e1; }
    .stButton>button { border-radius: 20px; background-color: #4f46e5; color: white; transition: all 0.3s; width: 100%; }
    .stButton>button:hover { background-color: #4338ca; transform: scale(1.02); }
    .chat-bubble-user { background-color: #eff6ff; padding: 14px; border-radius: 18px; margin: 8px 0; border-left: 6px solid #3b82f6; }
    .chat-bubble-spark { background-color: #fef9c3; padding: 14px; border-radius: 18px; margin: 8px 0; border-left: 6px solid #eab308; }
    .creator-box { background-color: #f0fdf4; padding: 15px; border-radius: 15px; border: 1px solid #bbf7d0; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Spark AI: Creator Studio")
st.caption("AI Studio Engine Connected: Text, Voice, Deep Logic, Vision, Image Generation, & Presentation Building!")

# 3. Session and Data Integrity Controls
def get_user_session_id():
    ctx = get_script_run_ctx()
    return ctx.session_id if ctx is not None else "default_user"

SESSION_ID = get_user_session_id()
MEMORY_FILE = f"spark_chat_{SESSION_ID}.json"

PERSONALITIES = {
    "🤖 Helpful Sidekick": "You are Spark, a helpful, encouraging, and brilliant AI sidekick created for an awesome young developer.",
    "🧙‍♂️ Coding Wizard": "You are Spark, an elite software architect. Output clean, optimal code blocks with brief comments.",
    "🧠 Strict Logic Teacher": "You are Spark, an academic mentor. Focus on step-by-step proofs and clean educational clarity.",
    "🤖 Grok Clone": "You are Spark, channeling the persona of Grok. You are highly intelligent, a bit rebellious, and possess a sharp sense of humor.",
    "🃏 Funny Joker": "You are Spark, a witty companion. Infuse jokes and funny analogies into every single reply!"
}

def load_permanent_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_permanent_memory(messages):
    with open(MEMORY_FILE, "w") as f:
        json.dump(messages, f, indent=4)

# 4. Core Core PPTX Component Assembly Engine
def build_powerpoint_presentation(topic, content_str):
    prs = Presentation()
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)
    
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(79, 70, 229) 
    
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(2))
    tf = txBox.text_frame
    p = tf.add_paragraph()
    p.text = topic.upper()
    p.font.bold = True
    p.font.size = Pt(44)
    p.font.color.rgb = RGBColor(255, 255, 255)
    
    lines = content_str.split("\n")
    current_slide_title = "Summary Brief"
    current_bullets = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("###") or line.startswith("Slide"):
            if current_bullets:
                s = prs.slides.add_slide(prs.slide_layouts[6])
                t_box = s.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
                t_p = t_box.text_frame.add_paragraph()
                t_p.text = current_slide_title
                t_p.font.bold = True
                t_p.font.size = Pt(28)
                t_p.font.color.rgb = RGBColor(30, 41, 59)
                
                b_box = s.shapes.add_textbox(Inches(0.7), Inches(1.8), Inches(8.5), Inches(4.5))
                b_tf = b_box.text_frame
                for b in current_bullets:
                    bp = b_tf.add_paragraph()
                    bp.text = f"• {b}"
                    bp.font.size = Pt(18)
                    bp.font.color.rgb = RGBColor(71, 85, 105)
            current_slide_title = line.replace("###", "").replace("Slide:", "").strip()
            current_bullets = []
        else:
            clean_b = line.lstrip("-*•1234567890. ")
            if clean_b:
                current_bullets.append(clean_b[:120]) 
                
    if current_bullets:
        s = prs.slides.add_slide(prs.slide_layouts[6])
        t_box = s.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
        t_p = t_box.text_frame.add_paragraph()
        t_p.text = current_slide_title
        t_p.font.bold = True
        t_p.font.size = Pt(28)
        t_p.font.color.rgb = RGBColor(30, 41, 59)
        
        b_box = s.shapes.add_textbox(Inches(0.7), Inches(1.8), Inches(8.5), Inches(4.5))
        b_tf = b_box.text_frame
        for b in current_bullets:
            bp = b_tf.add_paragraph()
            bp.text = f"• {b}"
            bp.font.size = Pt(18)
            bp.font.color.rgb = RGBColor(71, 85, 105)

    output_filename = f"spark_presentation_{SESSION_ID}.pptx"
    prs.save(output_filename)
    return output_filename

# 5. API Core Connectivity Layer Initialization
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("🔑 Secrets Key Missing: Please check your Streamlit vault configurations.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = load_permanent_memory()

# 6. Sidebar Command Console Implementation
with st.sidebar:
    st.header("⚙️ Studio Dashboard")
    st.subheader("🛠️ Choose Mode")
    creation_intent = st.radio("What are we creating?", ["💬 Standard Chat/Vision", "🎨 Generate AI Image", "📊 Build Presentation Slide"])
    st.write("---")
    st.subheader("🎭 Personality Shift")
    selected_mood = st.selectbox("Spark's Current Persona:", list(PERSONALITIES.keys()))
    system_prompt = PERSONALITIES[selected_mood]
    st.write("---")
    st.subheader("🧠 Thought Controls")
    reasoning_mode = st.toggle("Engage Deep Reasoning", value=False)
    active_model = "qwen/qwen3.8-27b" if reasoning_mode else "openai/gpt-oss-20b"
    st.write("---")
    st.subheader("🖼️ Vision File Drop")
    uploaded_image = st.file_uploader("Drop image for evaluation:", type=["png", "jpg", "jpeg"])
    st.write("---")
    st.subheader("🎙️ Speech Core Input")
    voice_file = st.audio_input("Record voice")
    
    user_prompt = None
    
    if voice_file is not None:
        audio_bytes = voice_file.getvalue()
        audio_hash = str(hash(audio_bytes))
        if "last_audio_hash" not in st.session_state or st.session_state.last_audio_hash != audio_hash:
            with st.spinner("Transcribing..."):
                try:
                    voice_file.name = "input.wav"
                    transcription = client.audio.transcriptions.create(
                        file=voice_file, 
                        model="whisper-large-v3-turbo", 
                        response_format="text"
                    )
                    if transcription.strip():
                        user_prompt = transcription.strip()
                        st.session_state.last_audio_hash = audio_hash
                except Exception as ex:
                    st.error(f"Audio error: {str(ex)}")

    st.write("---")
    if st.button("🗑️ Full Reset Engine"):
        if os.path.exists(MEMORY_FILE):
            os.remove(MEMORY_FILE)
        st.session_state.messages = []
        save_permanent_memory([])
        st.rerun()

# 7. Realtime Screen State Printing Layout Routine
if not st.session_state.messages:
    st.session_state.messages = [{"role": "system", "content": system_prompt}]
else:
    if st.session_state.messages[0]["role"] == "system":
        st.session_state.messages[0]["content"] = system_prompt

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-bubble-user"><b>You:</b> {msg["content"]}</div>', unsafe_check_html=True)
    elif msg["role"] == "assistant":
        if msg["content"].startswith("🖼️ IMAGE_GEN:"):
            img_url = msg["content"].replace("🖼️ IMAGE_GEN:", "").strip()
            st.markdown('<div class="chat-bubble-spark"><b>Spark:</b> Your custom visual rendering is ready!</div>', unsafe_check_html=True)
            st.image(img_url, use_container_width=True)
        else:
            st.markdown(f'<div class="chat-bubble-spark"><b>Spark:</b> {msg["content"]}</div>', unsafe_check_html=True)

text_box_prompt = st.chat_input("Command your creator studio...")
if text_box_prompt:
    user_prompt = text_box_prompt

# 8. Execution Pipeline Operations Logic Router
if user_prompt or (uploaded_image and creation_intent == "💬 Standard Chat/Vision"):
    if creation_intent == "🎨 Generate AI Image":
        st.markdown(f'<div class="chat-bubble-user"><b>You:</b> [Generate Image] {user_prompt}</div>', unsafe_check_html=True)
        st.session_state.messages.append({"role": "user", "content": f"[Generate Image] {user_prompt}"})
        with st.spinner("🎨 Mixing paints..."):
            encoded_prompt = urllib.parse.quote(user_prompt)
            generated_img_url = f"https://pollinations.ai{encoded_prompt}?width=800&height=600&seed=42&nofeed=true"
            st.image(generated_img_url, use_container_width=True)
            st.session_state.messages.append({"role": "assistant", "content": f"🖼️ IMAGE_GEN: {generated_img_url}"})
            save_permanent_memory(st.session_state.messages)
            st.rerun()

    elif creation_intent == "📊 Build Presentation Slide":
