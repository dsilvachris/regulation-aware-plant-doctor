"""
streamlit_app.py — Phase 4: Streamlit chat UI for the conversational plant doctor.

Wraps the Conversation engine (region gate + region-aware RAG + dialogue state) in a chat UI.
State lives in st.session_state, so the region slot, pending question, and history persist
across Streamlit's re-runs. The heavy model load happens once (Python caches the region_gate
import), so re-runs are fast.

Run:  streamlit run src/streamlit_app.py
Prereqs: Ollama running; pip install streamlit
"""
import streamlit as st
from conversational_doctor import Conversation

st.set_page_config(page_title="Regulation-Aware Plant Doctor", page_icon="🌱")

# --- conversation state (persists across re-runs) ---
if "convo" not in st.session_state:
    st.session_state.convo = Conversation()
if "messages" not in st.session_state:
    st.session_state.messages = []          # [(role, content), ...] for display

# --- sidebar: state + controls ---
with st.sidebar:
    st.title("🌱 Plant Doctor")
    st.caption("Regulation-aware, region-correct plant-disease advice for Germany and Norway.")
    region = st.session_state.convo.region
    label = {"DE": "Germany 🇩🇪", "NO": "Norway 🇳🇴"}.get(region, "not set yet")
    st.markdown(f"**Detected region:** {label}")
    st.markdown("---")
    st.markdown(
        "Ask about a crop disease. If you haven't said which country you're in, I'll ask — "
        "authorised plant-protection products differ between Germany and Norway."
    )
    if st.button("🔄 Reset conversation"):
        st.session_state.convo = Conversation()
        st.session_state.messages = []
        st.rerun()

# --- main: title + intro ---
st.title("Regulation-Aware Plant Doctor")
if not st.session_state.messages:
    st.info("Describe your crop and its symptoms — e.g. *“My potatoes have late blight, what should I spray?”*")

# --- render conversation so far ---
for role, content in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(content)

# --- handle new input ---
if prompt := st.chat_input("Describe the crop and the problem…"):
    st.session_state.messages.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            reply = st.session_state.convo.turn(prompt)
        st.markdown(reply)
    st.session_state.messages.append(("assistant", reply))
    st.rerun()   # refresh so the sidebar region label updates immediately