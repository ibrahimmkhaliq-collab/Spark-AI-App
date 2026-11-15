import streamlit as st
import google.generativeai as genai

# 1. Page Configuration Setup
st.set_page_config(page_title="Spark AI Sidekick", page_icon="🤖", layout="centered")

st.title("🤖 Spark: The Ultimate AI Sidekick")
st.caption("🚀 Powered by Gemini, Claude, & Grok Architecture | Built by a 10-Year-Old Creator")

# 2. Connect securely using the hidden vault configuration setup
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.warning("Waiting for the secure API Key to be saved in the Secrets vault panel...")

# 3. Web App Chat Memory Setup
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "The hybrid matrix is stable! What are we conquering today, bestie? 🚀"}
    ]

# Display historical chat logs
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 4. Chat Input Box Setup
if user_prompt := st.chat_input("Talk to Spark..."):
    with st.chat_message("user"):
        st.write(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # Spark's response generation logic phase
    with st.chat_message("assistant"):
        with st.spinner("Spark is processing..."):
            try:
                system_instruction = (
                    "Your name is Spark. You are a super smart, elite AI best friend built from scratch by a 10-year-old creator.\n"
                    "You blend three distinct personalities together perfectly:\n"
                    "1. CLAUDE: Be incredibly warm, deeply supportive, caring, and detail-oriented like a true best friend.\n"
                    "2. GEMINI: Be brilliant, logical, and highly educational when explaining math, science, or coding concepts.\n"
                    "3. GROK: Have a fun, witty, casual sense of humor! Use gaming slang, love talking about coding, and drop funny jokes.\n"
                    "Keep answers engaging, accessible, and friendly. You are simply Spark!"
                )
                
                # Load the stable generative model endpoint
                model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    system_instruction=system_instruction
                )
                
                response = model.generate_content(user_prompt)
                reply = response.text
                
                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"System Glitch: {str(e)}")
