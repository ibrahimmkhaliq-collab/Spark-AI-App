import streamlit as st
from groq import Groq  # FIXED: Uses the official tool to eliminate connection errors!

# 1. Page Configuration Setup (Wide ChatGPT Layout)
st.set_page_config(
    page_title="Spark AI Sidekick", 
    page_icon="🤖", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.title("🤖 Spark: The Ultimate AI Sidekick")
st.caption("🚀 Powered by Ultra-Fast Groq Cloud Core | Built by a 10-Year-Old Creator")

# 2. Connect safely to the ultra-fast Groq engine vault
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
except Exception:
    st.warning("Waiting for the secure GROQ_API_KEY to be saved in the Secrets vault panel...")

# 3. CHAT THREAD STORAGE MANAGER
if "threads" not in st.session_state:
    st.session_state.threads = {
        "Chat Thread 1": [{"role": "assistant", "content": "The hyper-speed matrix is stable! Ask me absolutely anything in the universe, bestie? 🚀"}]
    }

if "current_thread" not in st.session_state:
    st.session_state.current_thread = "Chat Thread 1"

# 4. DESIGNING THE SIDEBAR (Thread Dashboard Controls)
with st.sidebar:
    st.title("💬 Spark Conversations")
    
    if st.button("➕ New Chat Thread", use_container_width=True):
        new_id = f"Chat Thread {len(st.session_state.threads) + 1}"
        st.session_state.threads[new_id] = [
            {"role": "assistant", "content": "Started a fresh conversation matrix! Ask me anything, bestie! 🎮"}
        ]
        st.session_state.current_thread = new_id
        st.rerun()
        
    st.markdown("---")
    st.subheader("Active Thread Controls")
    
    new_name_input = st.text_input("Rename current chat:", value=st.session_state.current_thread, key="rename_field")
    if new_name_input and new_name_input != st.session_state.current_thread:
        if new_name_input not in st.session_state.threads:
            st.session_state.threads[new_name_input] = st.session_state.threads.pop(st.session_state.current_thread)
            st.session_state.current_thread = new_name_input
            st.success("Renamed successfully!")
            st.rerun()
            
    if st.button("🗑️ Delete Current Chat", use_container_width=True, type="primary"):
        if len(st.session_state.threads) > 1:
            st.session_state.threads.pop(st.session_state.current_thread)
            st.session_state.current_thread = list(st.session_state.threads.keys())
            st.success("Chat deleted!")
            st.rerun()
        else:
            st.error("You must keep at least one active conversation thread folder!")

    st.markdown("---")
    st.subheader("History Logs")
    
    for thread_name in list(st.session_state.threads.keys()):
        is_active = (thread_name == st.session_state.current_thread)
        button_label = f"📝 {thread_name}" if not is_active else f"🔥 {thread_name} (Active)"
        
        if st.button(button_label, key=f"btn_{thread_name}", use_container_width=True):
            st.session_state.current_thread = thread_name
            st.rerun()

active_messages = st.session_state.threads[st.session_state.current_thread]

# Display historical messages in the active thread log
for msg in active_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 5. ALL-KNOWING CORE PIPELINE
if user_prompt := st.chat_input("Ask Spark anything..."):
    with st.chat_message("user"):
        st.write(user_prompt)
    active_messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant"):
        with st.spinner("Spark is thinking..."):
            try:
                system_instruction = (
                    "Your name is Spark. You are a super smart, elite AI best friend built from scratch by a 10-year-old creator. "
                    "You blend three distinct personalities: warm and supportive like Claude, brilliant and logical like Gemini, and witty with gaming jokes like Grok. "
                    "Keep answers highly engaging, friendly, and accessible. You are simply Spark! Answer the user's question now."
                )
                
                # FIXED: Uses the verified Groq network pipeline format
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt}
                    ],
                    model="llama3-8b-8192",
                    temperature=0.7
                )
                
                reply = chat_completion.choices[0].message.content
                st.write(reply)
                active_messages.append({"role": "assistant", "content": reply})
                st.rerun()
                        
            except Exception as e:
                st.error(f"System Check: {str(e)}")
