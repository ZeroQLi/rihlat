import requests
import base64

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
    return response.json()["choices"][0]["message"]["content"]