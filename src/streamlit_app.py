"""
streamlit_app.py — Phase 5: multimodal Streamlit chat (text + image).

Text turns go through the dialogue engine; image turns run the vision model (vision.py) and
continue in the SAME conversation — region-aware and grounded. An uploaded photo simply fills
the 'disease' slot the way a text description would; the region slot and grounding are shared.

Run:  streamlit run src/streamlit_app.py
Prereqs: Ollama running; pip install streamlit
"""
import streamlit as st
from PIL import Image
from conversational_doctor import Conversation
import vision

st.set_page_config(page_title="Regulation-Aware Plant Doctor", page_icon="🌱")

# --- state (persists across re-runs) ---
if "convo" not in st.session_state:
    st.session_state.convo = Conversation()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_image_id" not in st.session_state:
    st.session_state.last_image_id = None

# --- sidebar: state, image upload, reset ---
with st.sidebar:
    st.title("🌱 Plant Doctor")
    st.caption("Regulation-aware, region-correct plant-disease advice for Germany and Norway.")
    region = st.session_state.convo.region
    label = {"DE": "Germany 🇩🇪", "NO": "Norway 🇳🇴"}.get(region, "not set yet")
    st.markdown(f"**Detected region:** {label}")
    st.markdown("---")
    st.markdown("**📷 Upload a leaf photo** — or just describe symptoms in the chat.")
    uploaded = st.file_uploader("leaf photo", type=["png", "jpg", "jpeg"],
                                label_visibility="collapsed")
    st.markdown("---")
    if st.button("🔄 Reset conversation"):
        st.session_state.convo = Conversation()
        st.session_state.messages = []
        st.session_state.last_image_id = None
        st.rerun()

# --- main ---
st.title("Regulation-Aware Plant Doctor")
if not st.session_state.messages:
    st.info("Describe your crop and its symptoms, or upload a leaf photo from the sidebar. "
            "I'll ask which country you're in — advice differs between Germany and Norway.")

# render conversation so far
for role, content in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(content)

# --- image turn (fires when a new photo is uploaded) ---
if uploaded is not None and uploaded.file_id != st.session_state.last_image_id:
    st.session_state.last_image_id = uploaded.file_id
    img = Image.open(uploaded)
    with st.chat_message("user"):
        st.image(img, width=220)
        st.markdown("*(uploaded a leaf photo)*")
    with st.chat_message("assistant"):
        with st.spinner("Looking at the photo…"):
            vr = vision.identify(img)
            reply = st.session_state.convo.image_turn(vr)
        st.markdown(reply)
    st.session_state.messages.append(("user", "📷 *(uploaded a leaf photo)*"))
    st.session_state.messages.append(("assistant", reply))
    # no rerun: keep the image visible in this turn; sidebar region is unchanged by an image turn

# --- text turn ---
if prompt := st.chat_input("Describe the crop and the problem…"):
    st.session_state.messages.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            reply = st.session_state.convo.turn(prompt)
        st.markdown(reply)
    st.session_state.messages.append(("assistant", reply))
    st.rerun()   # refresh so the sidebar region label updates