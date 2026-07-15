#!/usr/bin/env python3
from pprint import pprint
import argparse
from pydantic import BaseModel
from openai_utils import query_agent
from tts import generate_tts
import os

class MultiLanguageEssays(BaseModel):
    spanish: str
    indonesian: str
    japanese: str
    mandarin: str
    topic_folder_name: str

def generate_essays(topic):
    instructions = (
        "You are an expert author of pedagogical summaries in foreign languages. "
        "The user has requested a summary of the topic '{t}'. "
        "Please write a brief summary of the topic. "
        "Write two paragraphs of context (historical information, related topics, etc.), and two paragraphs describing the concepts themselves. "
        "Write the summary in simple terms that a 10-year-old could understand, while focusing on concrete examples and avoiding abstract/lofty explanations. "
        "This summary will be spoken aloud, so do not include bulleted lists or grammatical structures used in writing. "
        "Write the summary in each language prompted. "
        "Finally, provide a folder name for the topic, which should be a short, lowercase, hyphen-separated version of the topic. "
    )
    prompt = [{"role": "system", "content": instructions.format(t=topic)}]

    print(f"Generating essays for topic: {topic}")
    raw = query_agent(prompt, text_format=MultiLanguageEssays)
    print(f"Generated essays, under folder name: {raw.topic_folder_name}")

    # Put each script into its own text file in the temp folder
    # One text file per language, named {language}.txt
    files = []
    for language in ["spanish", "indonesian", "japanese", "mandarin"]:
        text = getattr(raw, language)
        text_filename = f"/tmp/{language}.txt"
        with open(text_filename, "w") as f:
            f.write(text)
        files.append(text_filename)
        # Use TTS to read the text aloud in the appropriate language
        # One audio file per language, named {language}.mp3
        audio_filepath = f"/tmp/{language}.mp3"
        print(f"Generating TTS for {language}...")
        generate_tts(text, language, audio_filepath)
        files.append(audio_filepath)

    # Rsync each file into root@raspberrypi:/audio/{topic_folder_name}/
    print("Syncing files to Raspberry Pi...")
    for file in files:
        os.system(f"rsync -a {file} root@raspberrypi:~/audio/{raw.topic_folder_name}/")
    print("Done syncing files.")

parser = argparse.ArgumentParser()
parser.add_argument("topic", nargs="+")
args = parser.parse_args()

topic = " ".join(args.topic).strip()
generate_essays(topic)
