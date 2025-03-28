import sys
import openai
from pathlib import Path

try:
    home = Path.home()
    with open(home/'openaikey', 'r') as keyFile:
        openai_api_key = keyFile.readline().strip()
except Exception as e:
    print(f"Error reading OpenAI API key: {e}")
    sys.exit(1)

if not openai_api_key:
    print("Error: OpenAI API key is missing.")
    sys.exit(1)

openai.api_key = openai_api_key

voices = [
"alloy",
"ash",
"ballad",
"coral",
"echo",
"fable",
"onyx",
"nova",
"sage",
"shimmer",
]
response = openai.audio.speech.create(
    model="gpt-4o-mini-tts",
    voice="nova",
    input="Mereka bekerja keras serta penuh dedikasi",
)
response.stream_to_file("/home/2swap/test.mp3")
