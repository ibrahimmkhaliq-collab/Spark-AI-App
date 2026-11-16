import streamlit as st
from groq import Groq
import json
import os
from streamlit.runtime.scriptrunner import get_script_run_ctx

# Set up the webpage title, icon, and layout
st.set_page_config(page_title="Spark AI Sidekick", page_icon="⚡", layout="centered")

# Custom CSS styling to make the app look awesome
st.markdown("""
    <style>
    .main { background-color: #f5f7fa; }
    .stTextInput>div>div>input { border-radius: 20px; }
    .stButton>button { border-radius: 20px; background-color: #4A90E2; color: white; }
    .chat-bubble-user { background-color: #E3F2FD; padding: 12px; border-radius: 15px; margin: 6px 0; border-left: 5px solid #2196F3; }
    .chat-bubble-spark { background-color: #FFF9C4; padding: 12px; border-radius: 15px; margin: 6px 0; border-left: 5px solid #FFEB3B; }
    </style>
    """, unsafe_check_html=True)

st.title("⚡ Spark AI Sidekick")
st.caption("Upgraded: Isolated Private Memories, Backups, and Live Audio Transcription!")

# Find the unique browser session ID for the user
def get_user_session_id():
    ctx = get_script_run_ctx()
    return ctx.session_id if ctx is not None else "default_user"

# Initialize file paths
SESSION_ID = get_user_session_id()
MEMORY_FILE = f"spark_chat_{SESSION_ID}.json"

def load_permanent_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return [{"role": "system", "content": "You are Spark, a helpful and brilliant AI sidekick created for an awesome developer."}]

def save_permanent_memory(messages):
    with open(MEMORY_FILE, "w") as f:
        json.dump(messages, f, indent=4)

# 1. Connect to Groq cloud engine securely
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("🔑 Secrets Key Missing: Please check your Streamlit vault configurations.")
    st.stop()

# 2. Synchronize existing history data
if "messages" not in st.session_state:
    st.session_state.messages = load_permanent_memory()

# 3. Print out conversation logs neatly
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-bubble-user"><b>You:</b> {msg["content"]}</div>', unsafe_check_html=True)
    elif msg["role"] == "assistant":
        st.markdown(f'<div class="chat-bubble-spark"><b>Spark:</b> {msg["content"]}</div>', unsafe_check_html=True)

# 4. Input Configuration Strategy (Voice + Text Input Hub)
user_prompt = None

# Keyboard text bar input at the bottom
text_input = st.chat_input("Type a message to Spark...")
if text_input:
    user_prompt = text_input

# Sidebar layout configurations
with st.sidebar:
    st.header("⚙️ Sidekick Settings")
    st.write("Memory Mode: **Isolated Private Space 🔒**")
    
    st.write("---")
    st.subheader("🎙️ Voice Mode Input")
    st.caption("Record your voice to automatically transcribe and send text:")
    
    # Direct system browser recording widget
    voice_file = st.audio_input("Record a message")
    
    # Check if a voice audio clip was recorded and hasn't been processed yet
    if voice_file is not None:
        # Create a unique key tracking if this audio file has already been sent
        audio_bytes = voice_file.getvalue()
        audio_hash = str(hash(audio_bytes))
        
        if "last_audio_hash" not in st.session_state or st.session_state.last_audio_hash != audio_hash:
            with st.spinner("🎙️ Transcribing voice audio..."):
                try:
                    # Provide an explicit file layout name so the tool reads the audio content properly
                    voice_file.name = "input_audio.wav"
                    
                    # Call Groq's high-speed Whisper audio transcription platform
                    transcription = client.audio.transcriptions.create(
                        file=voice_file,
                        model="whisper-large-v3-turbo",  # Ultra-fast transcription model
                        response_format="text"
                    )
                    
                    # Save the transcribed string as our prompt
                    if transcription.strip():
                        user_prompt = transcription.strip()
                        st.session_state.last_audio_hash = audio_hash
                except Exception as audio_err:
                    st.error(f"❌ Audio transcription failed: {str(audio_err)}")

    st.write("---")
    st.subheader("💾 Export Chat Log")
    
    chat_text = ""
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            chat_text += f"You: {msg['content']}\n"
        elif msg["role"] == "assistant":
            chat_text += f"Spark: {msg['content']}\n"
            
    st.download_button(
        label="📥 Download My Chat Log",
        data=chat_text,
        file_name="spark_chat_history.txt",
        mime="text/plain"
    )
    
    st.write("---")
    if st.button("🗑️ Reset My Chat Only"):
        if os.path.exists(MEMORY_FILE):
            os.remove(MEMORY_FILE)
        if "last_audio_hash" in st.session_state:
            del st.session_state.last_audio_hash
        st.session_state.messages = [
            {"role": "system", "content": "You are Spark, a helpful and brilliant AI sidekick created for an awesome developer."}
        ]
        save_permanent_memory(st.session_state.messages)
        st.rerun()

# 5. Process any active communication input discovered (Text or Transcribed Voice)
if user_prompt:
    st.markdown(f'<div class="chat-bubble-user"><b>You:</b> {user_prompt}</div>', unsafe_check_html=True)
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    save_permanent_memory(st.session_state.messages)
    
    with st.spinner("Spark is thinking..."):
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=st.session_state.messages,
                temperature=0.7,
                max_tokens=1024
            )
            
            spark_response = completion.choices.message.content
            st.markdown(f'<div class="chat-bubble-spark"><b>Spark:</b> {spark_response}</div>', unsafe_check_html=True)
            st.session_state.messages.append({"role": "assistant", "content": spark_response})
            save_permanent_memory(st.session_state.messages)
            
            # Instantly refresh to clear the audio file state so it doesn't double-trigger
            st.rerun()
            
        except Exception as e:
            st.error(f"⚠️ Error connection broken: {str(e)}")
