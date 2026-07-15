from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
import os
import uuid

load_dotenv()

# Read file at ~/elevenlabskey
api_key_path = os.path.expanduser("~/elevenlabskey")
with open(api_key_path, "r") as f:
    api_key_text = f.read().strip()
elevenlabs = ElevenLabs(
  api_key=api_key_text
)

def get_voice_id_by_language(language):
    if language=="Chinese":
        return "ByhETIclHirOlWnWKhHc"
    if language=="English":
        return "kPzsL2i3teMYv0FxEYQ6"
    if language=="Japanese":
        return "3JDquces8E8bkmvbh6Bc"
    if language=="Indonesian":
        return "RWiGLY9uXI70QL540WNd"
    if language=="Arabic":
        return "JjTirzdD7T3GMLkwdd3a"
    if language=="Spanish":
        return "n4x17EKVqyxfey8QMqvy"
    return None

def generate_tts(text, language, audio_filepath):
    text = '... ' + text + ' ...'
    response = elevenlabs.text_to_speech.convert(
        text=text,
        voice_id=get_voice_id_by_language(language),
        model_id="eleven_v3",
        output_format="mp3_44100_128",
    )

    with open(audio_filepath, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)
    print(f"{audio_filepath} generated successfully.")
