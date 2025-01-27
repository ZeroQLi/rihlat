import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import base64
import tempfile
import rihlat
from time import sleep
from elevenlabs import ElevenLabs
from elevenlabs import play
from datetime import datetime

# ===== INITIAL SETUP =====
st.set_page_config(
    page_title="Rihlat AI Assistant",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ===== GLOBAL STYLES =====

st.markdown("""
    <style>
    /* Core app styling */
    #MainMenu, footer, header {visibility: hidden;}
    .stApp {background-color: #333333 !important;}
    
    /* Text styling */
    .stApp, .stChatMessage, .stTextInput, .stAudioInput, .stMarkdown {
        color: white !important;
        font-family: 'Poppins', sans-serif !important;
    }
    
    /* Title styling */
    h1 {
        color: #FDFEFF !important; 
        font-family: 'Poppins', sans-serif !important;
        text-align: center !important;
        margin: 20px 0 !important;
    }
    
    /* Button styling */
    .stButton > button {color: #FFFFFF !important; background-color: black !important;}
    
    /* Chat bubbles */
    [data-testid="stChatMessage"] {background-color: #115C52 !important;}

    /* Sidebar styling */
    [data-testid="stSidebar"] {background-color: #141414!important; min-width: 350px; max-width: 350px;}
    .sidebar-title {
        display: flex; 
        align-items: center; 
        gap: 10px; 
        padding: 15px;
        font-size: 3em; 
        font-weight: bold;
        color: #FDFEFF !important; 
        font-family: 'Poppins', sans-serif !important;
        justify-content: flex-start;
        
    }
    </style>
""", unsafe_allow_html=True)

# ===== SESSION STATE =====
SESSION_DEFAULTS = {
    "messages": [],
    "audio_data": None,
    "input_key": 0,
    "history": []
}

for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ===== SIDEBAR CONTAINER =====
with st.sidebar:
    st.markdown("""
        <div class="sidebar-title">
            Rihlat
        </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📜 History", expanded=True):
        for item in st.session_state.history[-5:]:
            st.caption(f"<span style='color: white;'>•{item}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("""
    <div style="color: #FFFFFF"; font-family: poppins;>
    <p>
    Rihlat is an AI voice assistant that helps you answer questions about your local public transit network.
    
    </p>
    
    Source: https://github.com/ZeroQLi/rihlat
    </div>
    """, unsafe_allow_html=True)

# ===== INPUT PROCESSING =====
st.markdown('<div class="sticky-input">', unsafe_allow_html=True)
with st.container():
    with st.form("input_form", clear_on_submit=True):
        input_cols = st.columns([3, 1])
        
        with input_cols[0]:
            text_input = st.text_area(
                "Type your message",
                key=f"text_{st.session_state.input_key}",
                placeholder="Ask about bus routes...\n(e.g. 'When is route 10 arriving?')",
                label_visibility="collapsed",
                height=68,
            )
        
        with input_cols[1]:
            audio_input = st.audio_input(
                "Record audio",
                key=f"audio_{st.session_state.input_key}",
                help="Click and hold to record",
                label_visibility="collapsed"
            )
        
        submitted = st.form_submit_button("Send", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

if submitted:
    st.session_state.audio_data = audio_input.getvalue() if audio_input else None
    
    if text_input:
        # Process text input
        st.session_state.messages.append({"role": "user", "content": text_input})
        st.session_state.history.append(f"Text: {text_input[:30]}...")
        
        with st.spinner("Analyzing routes..."):
            response = rihlat.send_to_llm(text_input)
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.write(response)
            rihlat.play_text(response, st.secrets["ELEVENLABS_KEY"])

    st.session_state.input_key += 1
    st.rerun()

if st.session_state.audio_data:
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as f:
            f.write(st.session_state.audio_data)
            f.seek(0)
            
            with st.spinner("Processing audio..."):
                print("processing audio file")
                response = rihlat.transcribe_audio(f.name, st.secrets["SAMBANOVA_API_KEY"])
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.info()
                rihlat.play_text(response, st.secrets["ELEVENLABS_KEY"])
        
        st.session_state.audio_data = None
        st.rerun()
    
    except Exception as e:
        st.error(f"Audio processing error: {str(e)}")

# ===== AUTO-SCROLL SCRIPT =====
st.markdown("""
    <script>
    const observer = new MutationObserver(() => {
        window.scrollTo({
            top: document.body.scrollHeight,
            behavior: 'smooth'
        });
    });
    
    observer.observe(document.querySelector('.message-container'), {
        childList: true,
        subtree: true
    });
    </script>
""", unsafe_allow_html=True)