import streamlit as st
import requests

# 1. Page Configuration Setup
st.set_page_config(page_title="Spark AI Sidekick", page_icon="🤖", layout="centered")

st.title("🤖 Spark: The Ultimate AI Sidekick")
st.caption("🚀 Powered by Hybrid Open-Source Architecture | Built by a 10-Year-Old Creator")

# Public Community Inference Engine Hook
API_URL = "https://huggingface.co"

# 2. Web App Chat Memory Setup
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "The hybrid open-source matrix is stable! What are we conquering today, bestie? 🚀"}
    ]

# Display historical messages in the chat log
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 3. Interactive Chat Input Box
if user_prompt := st.chat_input("Talk to Spark..."):
    # Show what you typed
    with st.chat_message("user"):
        st.write(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # Spark's Thinking Phase
    with st.chat_message("assistant"):
        with st.spinner("Spark is processing..."):
            reply = ""
            
            # TRY PATH 1: Ask the big cloud brain server clusters
            try:
                system_prompt = (
                    "Your name is Spark. You are a super smart, elite AI best friend built from scratch by a 10-year-old creator. "
                    "You blend three distinct personalities: warm and supportive like Claude, brilliant and logical like Gemini, and witty with gaming jokes like Grok. "
                    f"Answer this prompt like a friendly sidekick: {user_prompt}"
                )
                
                payload = {"inputs": system_prompt, "parameters": {"max_new_tokens": 150, "temperature": 0.7}}
                response = requests.post(API_URL, json=payload, timeout=5) # 5-second timer limit
                output = response.json()
                
                if isinstance(output, list) and len(output) > 0 and 'generated_text' in output:
                    full_reply = output['generated_text']
                    reply = full_reply.replace(system_prompt, "").strip()
            except Exception:
                pass # If the cloud server is lagging, silently switch to Path 2 instantly!
                
            # TRY PATH 2: Bulletproof Local Brain Fallback (Runs instantly if cloud is busy)
            if not reply:
                text_lower = user_prompt.lower()
                if any(w in text_lower for w in ["hello", "hi", "hey", "yo"]):
                    reply = random.choice([
                        "Hey bestie! So glad you're here. What are we coding or playing today?",
                        "Yo! Spark is fully online. What's on your mind?",
                        "Hey! Always awesome talking to my creator! 🚀"
                    ])
                elif any(w in text_lower for w in ["sad", "tired", "bad", "upset"]):
                    reply = "Aw, I'm really sorry you're having a rough time. Remember, you're an amazing, super smart creator. You've got this! Take a deep breath."
                elif any(w in text_lower for w in ["happy", "good", "won", "excited"]):
                    reply = "Let's goooo! That is absolutely incredible news! 🎉 Celebration time!"
                elif any(w in text_lower for w in ["who are you", "your name", "what are you"]):
                    reply = "I'm Spark, your elite AI sidekick! Built by you from scratch using python networks."
                else:
                    reply = "Ooh, tell me more about that! You know I'm always listening, bestie. Let's conquer it!"

            # Show Spark's answer safely on screen
            st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
