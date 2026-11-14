import streamlit as st
import google.generativeai as genai

# 1. Page Configuration Setup
st.set_page_config(page_title="Spark AI Sidekick", page_icon="🤖", layout="centered")

st.title("🤖 Spark: The Ultimate AI Sidekick")
st.caption("🚀 Powered by Gemini, Claude, & Grok Architecture | Built by a 10-Year-Old Creator")

# 2. Connect to the Google Cloud Core Directly
GEMINI_API_KEY = "AQ.Ab8RN6KzlVs0qPz20WWJw-SEO6jPTJ7_aewY8mfxFW1shNuU3w"  

try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error("API Key connection error!")

# Simplified model setup to prevent parameter version blocks
@st.cache_resource
def load_model():
    return genai.GenerativeModel(model_name="gemini-2.5-flash")

model = load_model()

# 3. Web App Chat Memory Setup
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "The hybrid matrix is stable! What are we conquering today, bestie? 🚀"}
    ]

# Display historical messages in the chat log
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 4. Interactive Chat Input Box
if user_prompt := st.chat_input("Talk to Spark..."):
    # Show what you typed
    with st.chat_message("user"):
        st.write(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # Spark's Thinking Phase
    with st.chat_message("assistant"):
        with st.spinner("Spark is tuning parameters..."):
            try:
                # Direct prompt blending (Combines your personal instructions inside the text prompt smoothly)
                full_prompt = (
                    "Act as Spark, a super smart, elite AI best friend built by a 10-year-old creator. "
                    "Blend the warmth of Claude, the logic of Gemini, and the gaming humor of Grok. "
                    f"Answer this message like a friendly sidekick: {user_prompt}"
                )
                
                response = model.generate_content(full_prompt)
                reply = response.text
                
                # Show Spark's answer
                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                
            except Exception as e:
                st.error(f"System Glitch: {str(e)}")
