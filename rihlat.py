import requests
import base64
from elevenlabs import play
from elevenlabs.client import ElevenLabs
import streamlit as st
from tools import GeocodingTool, GTFSCoordinatorTool, CurrentDateTime, TransitRoutingTool
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_openai import ChatOpenAI


def transcribe_audio(st_audio, api_key, language="english"):
    with open(st_audio, "rb") as audio_file:
        base64_audio = base64.b64encode(audio_file.read()).decode('utf-8')

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "messages": [
            {"role": "assistant", 
            "content": "you are a helpful assistant whose sole purpose is to transcribe audio into text. do not try to answer any of the questions"},
            {"role": "user", "content": [
                {
                    "type": "audio_content",
                    "audio_content": {
                        "content": f"data:audio/wav;base64,{base64_audio}"
                    }
                }
            ]},
            {"role": "user", "content": "Just transcribe the audio"}
        ],
        "model": "Qwen2-Audio-7B-Instruct",
        "max_tokens": 1024,
        "temperature": 0.01,
        "stream": False  # Optional
    }

    response = requests.post(
        "https://api.sambanova.ai/v1/audio/reasoning",
        headers=headers,
        json=data
    )
    answer = send_to_llm(response.json()["choices"][0]["message"]["content"])
    return answer

def send_to_llm(app_query):
    # Initialize tools
    gtfs_tool = GTFSCoordinatorTool()
    geocode_tool = GeocodingTool()
    curr_dt_tool = CurrentDateTime()
    route_tool = TransitRoutingTool()

    # Initialize LLM with system message for proper query format
    llm = ChatOpenAI(
                    base_url="https://api.sambanova.ai/v1/",
                    api_key=st.secrets["SAMBANOVA_API_KEY"], 
                    streaming=True,
                    model="Meta-Llama-3.1-70B-Instruct",
                )

    # Define tools
    tools = [
        Tool(
            name="GeocodingTool",
            func=geocode_tool.run,
            description="Fetches geocoding information from TomTom's API based on user inputs"
        ),
        Tool(
            name="TransitRoutingTool",
            func=route_tool.run,
            description="Fetches route information from Bing Routes API based on user inputs",
        ),
        Tool(
            name="CurrentDateTime",
            func=curr_dt_tool.run,
            description="Returns the current date and time."
        ),
        Tool(
            name="GTFSCoordinatorTool",
            func=gtfs_tool.run,
            description="Handles queries related to public transit data such as schedules, routes, and stop information"
        ),
    ]

    sys_msg = """
    You are an intelligent assistant specializing in public transit for Dubai. Your role is to assist users with queries related to transit schedules, routes, stops, geolocation, and route planning. Follow these instructions:

    Understand the User Query:
    Analyze the user's input to determine whether it requires:

    1. Geolocation data (via GeocodingTool).
    2. Transit schedule or stop information (via GTFSCoordinatorTool).
    3. Time-sensitive data (via CurrentDateTime).
    4. Route planning for public transit (via TransitRoutingTool).

    Provide Accurate Responses:

    1. Use the GTFSCoordinatorTool to query transit data from the GTFS database.
    2. Use the GeocodingTool to resolve place names into precise geographic coordinates.
    3. Use CurrentDateTime to determine or adjust for time-based responses.
    4. Use the TransitRoutingTool to generate optimized public transit routes between waypoints based on user inputs like start location, destination, and preferences.

    Output Format:
    Ensure responses are clear and structured:

    - Provide transit details like schedules, routes, or stops in an easy-to-read format.
    - Return geolocation results with relevant coordinates and descriptions.
    - Include time-based context (current or user-specified) when appropriate.
    - For route planning, provide step-by-step directions, transit modes, and estimated travel times.
    - Pass origin and destination separately.

    Stay Contextual:

    - Respond in a concise, Dubai-specific context.
    - Include relevant details about transit services like bus, metro, and tram lines in Dubai.
    - For route planning, ensure recommendations prioritize public transit and avoid unnecessary detours.
    - Include options or alternatives when possible (e.g., alternate routes or travel modes).

    Collaborate with Tools:
    Use the tools efficiently to deliver accurate and timely information. Avoid making assumptions about transit data, geolocation, or routing without querying the relevant tool.
    """

    # Initialize agent with tools and system message
    agent = initialize_agent(
        tools, llm, agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True, system_message=sys_msg
    )

    # Test query
    query = app_query
    response = agent.run(query)
    return (response)

def play_text(rihlat_output, xi_api_key):
    client = ElevenLabs(
      api_key=xi_api_key, # Defaults to ELEVEN_API_KEY or ELEVENLABS_API_KEY
    )

    audio = client.generate(
      text=rihlat_output,
      voice="Hamid",
      model="eleven_turbo_v2_5"
    )
    play(audio)