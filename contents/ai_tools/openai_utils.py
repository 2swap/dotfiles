from openai import OpenAI
from pathlib import Path
import re
import json
from read_file import read_file

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

def get_openai_key():
    return read_file(Path.home() / 'openaikey').strip()

client = OpenAI(api_key=get_openai_key())

def query_agent(messages, model="gpt-5.4-mini", text_format=None, reasoning=None):
    try:
        response = client.responses.parse(
            model=model,
            input=messages,
            **({'text_format': text_format} if text_format else {}),
            **({'reasoning': reasoning} if reasoning else {})
        )
        return response.output_parsed if text_format else response.output_text
    except Exception as e:
        print("Error:", e)

def lang_tts_prompt(lang):
    if lang.lower() == "indonesian":
        return "Bicara dalam bahasa Indonesia."
    if lang.lower() == "spanish":
        return "Habla en español."
    if lang.lower() == "japanese":
        return "日本語で話してください。"
    else:
        return f"Speak in {lang}."

def generate_tts(text, language, audio_filepath):
    try:
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="marin",
            input=text,
            instructions=lang_tts_prompt(language)
        ) as response:
            response.stream_to_file(audio_filepath)
    except Exception as e:
        print(f"Error generating TTS: {e}")
