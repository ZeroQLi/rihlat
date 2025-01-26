import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import base64
import tempfile
import rihlat
from time import sleep
from elevenlabs import ElevenLabs  # Assuming this is the correct import for the ElevenLabs client
from elevenlabs import play

st.set_page_config(page_title="Rihlat", page_icon="🚌", layout="wide")

st.markdown("""
<style>
body { font-family: 'Roboto', sans-serif; }
.sidebar .title { 
    font-size: 40px; 
    text-align: center; 
    margin-bottom: 20px; 
    font-family: 'Montserrat', sans-serif;
    font-weight: bold;
    color: #4CAF50;
}
.stTextInput, .stAudioInput {
    width: 100%;
}
.stColumn > .stTextInput, .stColumn > .stAudioInput {
    display: inline-block;
    width: 48%;
    margin-right: 2%;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.stMarkdown .title {
    font-family: 'Inter', sans-serif;
    font-size: 100px;
    text-align: center;
    color: blue;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown('<div class="title">Rihlat</div>', unsafe_allow_html=True)

if 'messages' not in st.session_state:
    st.session_state.messages = []

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

def get_bus_response(message):
    message = message.lower()

    for route, details in BUS_ROUTES.items():
        if route in message:
            return f"Route {route.upper()}: Next arrival in {details['next_arrival']}. Stations: {', '.join(details['stations'])}"

    if "route" in message:
        return "\n".join([f"{route.upper()}: {details['next_arrival']} - {', '.join(details['stations'])}" for route, details in BUS_ROUTES.items()])
    
    if "help" in message or "info" in message:
        return "I can help you with bus routes in Dubai. Try asking 'When is route 10?' or 'Show routes'"
    
    return "I didn't understand. Ask about specific bus routes or say 'help'."

def create_bus_map(location):
    m = folium.Map(location=location, zoom_start=12)
    folium.Marker(location, popup="Bus Location").add_to(m)
    return m

def play_text(rihlat_output, xi_api_key):
    client = ElevenLabs(
        api_key=xi_api_key,  # Defaults to ELEVEN_API_KEY or ELEVENLABS_API_KEY
    )

    audio = client.generate(
        text=rihlat_output,
        voice="Hamid",
        model="eleven_turbo_v2_5"
    )
    play(audio)

audio = st.audio_input("Speak now")
if audio:
    with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as temp_audio:
        temp_audio.write(audio.getvalue())
        transcript = rihlat.transcribe_audio(temp_audio.name, "7fbda577-d23f-4d8b-9098-3d4edfe4f1de")
        st.write(f"Transcription: {transcript}")
        response = get_bus_response(transcript)
        st.markdown(response)
        play_text(response, "sk_40ae4c9c3087c754dac0aa6f4d91983f40d06c355e225330")  # Replace with your actual ElevenLabs API key

# Text input
query = st.text_input("Ask about bus routes")

if query:
    with st.chat_message("user"):
        st.markdown("Processing your query...")

    response = get_bus_response(query)

    with st.chat_message("assistant"):
        st.markdown(response)
        play_text(response, "sk_40ae4c9c3087c754dac0aa6f4d91983f40d06c355e225330")  # Replace with your actual ElevenLabs API key

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if query:
    map_location = None
    for route, details in BUS_ROUTES.items():
        if route in query.lower():
            map_location = details['location']
            break
    if map_location:
        st.map_folium = create_bus_map(map_location)
        st_folium(st.map_folium, width='100%', height=400)
