import streamlit as st
from groq import Groq

# 1. Initialize the Groq client using your Streamlit Secrets vault
client = Groq(
    api_key=st.secrets["GROQ_API_KEY"]
)

# 2. Set up the chat completion call using the updated model ID
if "messages" not in st.session_state:
    st.session_state.messages = []

# Example layout for generating a response from Spark
def generate_spark_response(prompt):
    # Append user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Make the API call to the active model
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are Spark, a helpful AI sidekick."},
            *st.session_state.messages
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    
    response_text = completion.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    return response_text
