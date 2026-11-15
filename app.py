import streamlit as st
import requests

# 1. Page Configuration Setup
st.set_page_config(page_title="Spark AI Sidekick", page_icon="🤖", layout="centered")

st.title("🤖 Spark: The Ultimate AI Sidekick")
st.caption("🚀 Powered by Open-Source Llama Architecture | Built by a 10-Year-Old Creator")

# 2. Public Community Inference Engine Hook (No Google Keys Needed!)
API_URL = "https://huggingface.co"

# 3. Web App Chat Memory Setup
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "The hybrid open-source matrix is stable! What are we conquering today, bestie? 🚀"}
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
        with st.spinner("Spark is processing..."):
            try:
                # Direct best-friend prompt engineering block
                system_prompt = (
                    "Your name is Spark. You are a super smart, elite AI best friend built from scratch by a 10-year-old creator. "
                    "You blend three distinct personalities: warm and supportive like Claude, brilliant and logical like Gemini, and witty with gaming jokes like Grok. "
                    "Keep answers highly engaging, friendly, and accessible. You are simply Spark! "
                    f"Answer this prompt like a friendly sidekick: {user_prompt}"
                )
                
                # Make a secure network request to the public AI cluster
                payload = {"inputs": system_prompt, "parameters": {"max_new_tokens": 250, "temperature": 0.7}}
                response = requests.post(API_URL, json=payload)
                
                # Extract text output response block safely
                output = response.json()
                if isinstance(output, list) and len(output) > 0 and 'generated_text' in output[0]:
                    # Clean up the output text to show only the answer response
                    full_reply = output[0]['generated_text']
                    reply = full_reply.replace(system_prompt, "").strip()
                else:
                    reply = "Hey bestie! My network paths just hiccupped. Send that message one more time!"
                
                # Show Spark's answer on screen
                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                
            except Exception as e:
                st.error(f"System Glitch: {str(e)}")
