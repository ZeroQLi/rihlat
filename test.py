import getpass
import os
import streamlit as st
from langchain_community.chat_models.sambanova import ChatSambaNovaCloud

if not os.getenv("SAMBANOVA_API_KEY"):
    os.environ["SAMBANOVA_API_KEY"] = getpass.getpass(
        "Enter your SambaNova Cloud API key: "
    )

llm = ChatSambaNovaCloud(
    model="Meta-Llama-3.1-70B-Instruct",
    max_tokens=1024,
    temperature=0.7,
    top_k=1,
    top_p=0.01,
    streaming=False
)

def send_message(text):
    messages = [
    (
        "system",
        """You are a machine who's sole purpose is to transcribe any audio input and send the output as text.
        If the given input is already text. just return the exact same text as output""",
    ),
    (text),
    ]
    ai_msg = llm.invoke(messages)
    st.info(ai_msg)
    return (ai_msg)

#streamlit data from here

st.write("rihlat test prompter")

with st.form("my_form"):
    text = st.text_area(
        "Enter text:",
        "It will transcribe exactly what you say",
    )
    submitted = st.form_submit_button("Submit")
    if submitted:
        send_message(text)

st.audio_input
