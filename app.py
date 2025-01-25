import streamlit as st
import rihlat
import tempfile
import json

if prompt := st.chat_input("Enter your question") or st.audio_input("Record your query"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown("sending audio file")

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
