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

# ===== BUS ROUTE DATA =====
BUS_ROUTES = {
    "route 10": {
        "stations": ["Al Qouz", "Mall of Emirates", "Dubai Marina"],
        "next_arrival": "15 minutes",
        "location": [25.2048, 55.2708]
    },
    "route 15": {
        "stations": ["Deira", "Dubai Creek", "Bur Dubai"],
        "next_arrival": "22 minutes",
        "location": [25.2654, 55.2962]
    }
}

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

# ===== CORE FUNCTIONS =====
def get_bus_response(message):
    message = message.lower()
    
    for route, details in BUS_ROUTES.items():
        if route in message:
            return f"Route {route.upper()}: Next arrival in {details['next_arrival']}. Stations: {', '.join(details['stations'])}"
    
    if "route" in message:
        return "\n".join([f"{route.upper()}: {details['next_arrival']} - {', '.join(details['stations'])}" 
                        for route, details in BUS_ROUTES.items()])
    
    if "help" in message or "info" in message:
        return "I can help you with bus routes in Dubai. Try asking 'When is route 10?' or 'Show routes'"
    
    return "I didn't understand. Ask about specific bus routes or say 'help'."

def create_bus_map(location):
    m = folium.Map(location=location, zoom_start=12)
    folium.Marker(location, popup="Bus Location").add_to(m)
    return m

def play_text(response, xi_api_key):
    client = ElevenLabs(api_key=xi_api_key)
    audio = client.generate(
        text=response,
        voice="Hamid",
        model="eleven_turbo_v2"
    )
    play(audio)

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
    <p>Rihlat is an AI assistant that can help you with bus routes.</p>
    
    Source 
            (github.com/ZeroQLi/rihlat)
    </div>
    """, unsafe_allow_html=True)

# ===== MAIN CHAT CONTAINER =====
with st.container():
    
    with st.container():
        st.markdown('<div class="message-container">', unsafe_allow_html=True)
        for msg in st.session_state.messages:
            avatar = "👨🏻‍💻" if msg["role"] == "user" else "⚛"
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.markdown(f"""
                    <div style="margin: 1rem 0; padding: 1rem; 
                         background: { '#444' if msg['role'] == 'user' else '#555' };
                        border-radius: 15px;
                        animation: fadeIn 0.5s ease-in;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.5em;">{avatar}</span>
                            <div>
                                <div style="color: #888; font-size: 0.8em;">{timestamp}</div>
                                {msg["content"]}
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)

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
            response = get_bus_response(text_input)
            st.session_state.messages.append({"role": "assistant", "content": response})
            play_text(response, "sk_40ae4c9c3087c754dac0aa6f4d91983f40d06c355e225330")
            
            # Show map if location found
            map_location = next((details['location'] for route, details in BUS_ROUTES.items() 
                               if route in text_input.lower()), None)
            if map_location:
                bus_map = create_bus_map(map_location)
                st_folium(bus_map, width='100%', height=400)

    st.session_state.input_key += 1
    st.rerun()

if st.session_state.audio_data:
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as f:
            f.write(st.session_state.audio_data)
            f.seek(0)
            
            with st.spinner("Processing audio..."):
                transcription = rihlat.transcribe_audio(f.name, "7fbda577-d23f-4d8b-9098-3d4edfe4f1de")
                st.session_state.messages.append({"role": "user", "content": f"🎤 Audio: {transcription}"})
                st.session_state.history.append(f"Audio: {transcription[:30]}...")
                
                response = get_bus_response(transcription)
                st.session_state.messages.append({"role": "assistant", "content": response})
                play_text(response, "sk_40ae4c9c3087c754dac0aa6f4d91983f40d06c355e225330")
                
                # Show map if location found
                map_location = next((details['location'] for route, details in BUS_ROUTES.items() 
                                   if route in transcription.lower()), None)
                if map_location:
                    bus_map = create_bus_map(map_location)
                    st_folium(bus_map, width='100%', height=400)
        
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