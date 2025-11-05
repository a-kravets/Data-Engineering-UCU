import streamlit as st
import requests
import os
from deep_translator import GoogleTranslator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="Python-based LLM Chatbot", layout="centered")

st.title("Python-based LLM Chatbot")


LLM_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434/api/chat")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "gemma:2b")

CONTEXT_FILE = "context.txt"
if os.path.exists(CONTEXT_FILE):
    with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
        context_text = f.read()
else:
    context_text = "No context file found."


#Split context into paragraphs

paragraphs = [p.strip() for p in context_text.split("\n\n") if p.strip()]

#Simple TF-IDF retriever

def get_relevant_context(query, k=3):
    if not paragraphs:
        return ""
    docs = paragraphs + [query]
    vectorizer = TfidfVectorizer().fit_transform(docs)
    sims = cosine_similarity(vectorizer[-1], vectorizer[:-1]).flatten()
    top_indices = sims.argsort()[-k:][::-1]
    relevant = "\n\n".join(paragraphs[i] for i in top_indices)
    return relevant




if "history" not in st.session_state:
    st.session_state.history = []

translator_to_en = GoogleTranslator(source="auto", target="en")
translator_to_uk = GoogleTranslator(source="auto", target="uk")

with st.form(key="chat_form"):
    user_input = st.text_input("You:", placeholder="Ask me anything...")
    send_button = st.form_submit_button("Send")

if send_button and user_input.strip():
    user_input_en = translator_to_en.translate(user_input)
    st.session_state.history.append({"role": "user", "content": user_input})

    # Get relevant context snippets
    relevant = get_relevant_context(user_input_en)

    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Use the following context to answer accurately:\n\n{context_text}"},
                {"role": "user", "content": user_input_en}
            ],
            "stream": False
        }
        response = requests.post(LLM_API_URL, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        llm_reply_en = data["message"]["content"]
        llm_reply_uk = translator_to_uk.translate(llm_reply_en)
        llm_reply = llm_reply_uk + context_text
    except Exception as e:
        llm_reply = f"Error contacting LLM: {e}"
    st.session_state.history.append({"role": "assistant", "content": llm_reply})

for msg in st.session_state.history:
    prefix = "You" if msg["role"] == "user" else "Bot"
    st.markdown(f"**{prefix}:** {msg['content']}")
