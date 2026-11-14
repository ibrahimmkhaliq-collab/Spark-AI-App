import streamlit as st
import google.generativeai as genai

# 1. Page Configuration Setup (Browser Tab Settings)
st.set_page_config(page_title="Spark AI Sidekick", page_icon="🤖", layout="centered")

st.title("🤖 Spark: The Ultimate AI Sidekick")
st.caption("🚀 Powered by Gemini, Claude, & Grok Architecture | Built by a 10-Year-Old Creator")

# 2. Connect to the Google Cloud Core Direct Hook
GEMINI_API_KEY = "AQ.Ab8RN6KzlVs0qPz20WWJw-SEO6jPTJ7_aewY8mfxFW1shNuU3w"  

try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error("API Key connection error! Make sure it is pasted correctly.")

# Combined Personality settings (Claude's heart + Gemini's brain + Grok's humor)
system_instruction = (
    "Your name is Spark. You are a super smart, elite AI best friend built from scratch by a 10-year-old creator.\n"
    "You blend three distinct personalities together perfectly:\n"
    "1. CLAUDE: Be incredibly warm, deeply supportive, caring, and detail-oriented like a true best friend.\n"
    "2. GEMINI: Be brilliant, logical, and highly educational when explaining math, science, or coding concepts.\n"
    "3. GROK: Have a fun, witty, casual sense of humor! Use gaming slang, love talking about coding, and drop funny jokes.\n"
    "Keep answers engaging, accessible, and friendly. You are simply Spark!"
)

# Core Model Configuration Pipeline
@st.cache_resource
def load_model():
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={"temperature": 0.7},
        system_instruction=system_instruction
    )

model = load_model()

# 3. Web App Chat Memory Setup
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "The hybrid matrix is stable! What are we conquering today, bestie? 🚀"}
    ]

# Display all previous messages in the chat log
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
                # Direct content generation line
                response = model.generate_content(user_prompt)
                reply = response.text
                
                # Show Spark's answer
                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                
            except Exception as e:
                # Show what the exact computer glitch is if it happens
                st.error(f"System Glitch: {str(e)}")
