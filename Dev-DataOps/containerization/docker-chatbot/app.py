import streamlit as st
import requests

st.set_page_config(page_title="Python-based LLM Chatbot", layout="centered")

st.title("Python-based LLM Chatbot")

# Backend LLM endpoint
# we use host.docker.internal instead of localhost
LLM_API_URL = "http://host.docker.internal:12434/engines/llama.cpp/v1/chat/completions"

if "history" not in st.session_state:
    st.session_state.history = []

user_input = st.text_input("You:", placeholder="Ask me anything...")
send_button = st.button("Send")

if send_button and user_input.strip():
    # Add user message
    st.session_state.history.append({"role": "user", "content": user_input})
    
    # Send request to LLM container
    try:
 #       payload = {
 #           "model": "ai/smollm2:135M-Q4_K_M",
 #           "messages": st.session_state.history,
 #           "max_tokens": 200
 #       }
        payload = {
            "model": "ai/smollm2:135M-Q4_K_M",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."}
            ] + st.session_state.history
        }
        response = requests.post(LLM_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        llm_reply = data["choices"][0]["message"]["content"]

    except Exception as e:
        llm_reply = f"Error contacting LLM: {e}"

    st.session_state.history.append({"role": "assistant", "content": llm_reply})

# Display chat history
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**Bot:** {msg['content']}")
