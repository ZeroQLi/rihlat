import streamlit as st
import rihlat
import tempfile
import json

#streamlit data from here
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Enter your question") or st.audio_input("Record your query"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown("sending audio file")
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

if prompt:
    with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as f:
        # The translation API requires a file, 
        # so we write the audio data to a temporary file
        f.write(prompt.getvalue())
        # open and translate the file
        response = rihlat.transcribe_audio(f.name, "7fbda577-d23f-4d8b-9098-3d4edfe4f1de")
        f.close()

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
