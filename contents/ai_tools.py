#!/usr/bin/env python3
import sys
import openai
import readline  # Enables navigation using arrow keys and delete
from pathlib import Path
import subprocess
import threading
import os
import json
import requests
import re
import argparse
import string
import random
from pprint import pprint
import shutil
from time import sleep

def anki_connect(action, params={}):
    try:
        if params is None:
            params = []
        request = json.dumps({"action": action, "version": 6, "params": params})
        response = requests.post("http://localhost:8765", data=request)
        resp_json = response.json()
        if 'error' in resp_json and resp_json['error']:
            print("Error: " + str(resp_json['error']))
        return resp_json
    except requests.ConnectionError:
        print("AnkiConnect is not running. Please turn it on.")
        exit(1)

def check_deck_exists(deck_name):
    decks = anki_connect("deckNames")["result"]
    if not (deck_name in decks):
        anki_connect("createDeck", {"deck": deck_name})
        print(f"Deck '{deck_name}' created.")

def read_file(input_file):
    print(f"Reading file {input_file}")
    try:
        with open(input_file, 'r') as f:
            file_content = f.read()
            return file_content
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

def anki_add_note(deck, front, back, front_sound, back_sound):
    notes = [{
        "deckName": deck,
        "modelName": "BasicWithTTS",
        "fields": {
            "Front": front,
            "Back": back,
            "FrontTTS": "[sound:"+front_sound+"]",
            "BackTTS": "[sound:"+back_sound+"]",
        },
        "options": {
            "allowDuplicate": True
        },
        "tags": []
    }]
    resp_json = anki_connect("addNotes", { "notes": notes } )

def parse_json(raw):
    json_match = re.search(r'(\{.*\}|\[.*\])', raw, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print("Failed to decode JSON. Raw string was:")
            print(json_str)
            sys.exit(1)
    else:
        print("No valid JSON found. Raw string was:")
        print(raw)
        sys.exit(1)
    return data

def get_openai_key():
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
    return openai_api_key

def get_azure_key():
    try:
        home = Path.home()
        with open(home/'azurekey', 'r') as keyFile:
            azure_api_key = keyFile.readline().strip()
    except Exception as e:
        print(f"Error reading OpenAI API key: {e}")
        sys.exit(1)

    if not azure_api_key:
        print("Error: OpenAI API key is missing.")
        sys.exit(1)
    return azure_api_key

openai.api_key = get_openai_key()

azure_token = 0 # Cache the token
def get_azure_token():
    global azure_token
    if azure_token == 0:
        fetch_token_url = 'https://eastus.api.cognitive.microsoft.com/sts/v1.0/issueToken'
        headers = {
            'Ocp-Apim-Subscription-Key': get_azure_key()
        }
        response = requests.post(fetch_token_url, headers=headers)
        azure_token = str(response.text)
    return azure_token

def get_lang(language):
    mapping = {
        "english": "en", "french": "fr", "spanish": "es", "german": "de", "italian": "it",
        "japanese": "ja", "chinese": "zh", "mandarin": "zh", "russian": "ru", "korean": "ko",
        "portuguese": "pt", "hindi": "hi", "arabic": "ar", "indonesian": "id", "tagalog": "fil",
        "filipino": "fil", "turkish": "tr"
    }
    return mapping.get(language.lower(), "en")

# https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts
def azure_tts(text, path, language):
    voice_dict = {
        "de": ["de-DE-GiselaNeural"],
        "hi": ["hi-IN-AnanyaNeural", "hi-IN-AartiNeural", "hi-IN-KavyaNeural", "hi-IN-SwaraNeural"],
        "es": ["es-MX-DaliaNeural", "es-MX-BeatrizNeural", "es-MX-CandelaNeural", "es-MX-CarlotaNeural", "es-MX-LarissaNeural", "es-MX-MarinaNeural", "es-MX-NuriaNeural", "es-MX-RenataNeural"],
        "id": ["id-ID-GadisNeural", "id-ID-ArdiNeural"],
        "tr": ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"],
        "ja": ["ja-JP-NanamiNeural", "ja-JP-AoiNeural", "ja-JP-MayuNeural", "ja-JP-ShioriNeural"],
        #"zh": ["zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural", "zh-CN-XiaochenNeural", "zh-CN-XiaochenMultilingualNeural4", "zh-CN-XiaohanNeural", "zh-CN-XiaomengNeural", "zh-CN-XiaomoNeural", "zh-CN-XiaoqiuNeural", "zh-CN-XiaorouNeural", "zh-CN-XiaoruiNeural", "zh-CN-XiaoshuangNeural", "zh-CN-XiaoxiaoDialectsNeural", "zh-CN-XiaoxiaoMultilingualNeural4", "zh-CN-XiaoyanNeural", "zh-CN-XiaoyouNeural", "zh-CN-XiaoyuMultilingualNeural4", "zh-CN-XiaozhenNeural"],
        #"zh": ["zh-CN-Xiaochen:DragonHDFlashLatestNeural", "zh-CN-Xiaoxiao:DragonHDFlashLatestNeural", "zh-CN-Xiaoxiao2:DragonHDFlashLatestNeural"],
        "zh": ["zh-CN-Xiaochen:DragonHDLatestNeural"],
        "fil": ["fil-PH-BlessicaNeural", "fil-PH-AngeloNeural"],
        "fr": ["fr-FR-DeniseNeural", "fr-FR-VivienneMultilingualNeural4", "fr-FR-BrigitteNeural", "fr-FR-CelesteNeural", "fr-FR-CoralieNeural", "fr-FR-EloiseNeural", "fr-FR-JacquelineNeural", "fr-FR-JosephineNeural", "fr-FR-YvetteNeural"]
    }
    key = get_lang(language)
    if key in voice_dict:
        voice = random.choice(voice_dict[key])
    else:
        print("Azure language not supported!")
        exit(1)
    if "HD" in voice:
        sleep(7)
    sanitized_text = re.sub(r'[&<>"\']', ' ', re.sub(r'\s+', ' ', text))
    ssml = f"""<speak version='1.0' xml:lang='en-US'>
  <voice name='{voice}'>
    {sanitized_text}
  </voice>
</speak>"""
    tts_url = "https://eastus.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Authorization": "Bearer " + get_azure_token(),
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-48khz-192kbitrate-mono-mp3",
        "User-Agent": "azureTTS"
    }
    response = requests.post(tts_url, headers=headers, data=ssml.encode('utf-8'))
    if response.status_code == 200:
        with open(path, "wb") as audio:
            audio.write(response.content)
    else:
        try:
            error_json = response.json()
            error_message = error_json.get('error', response.text)
        except Exception:
            error_message = response.text
            print(f"TTS request failed with status code {response.status_code}: {error_message}")

def query_agent(model, messages):
    try:
        completion = openai.chat.completions.create(
            model=model,
            messages=messages
        )
    except Exception as e:
        print("Error:", e)
    return completion.choices[0].message.content.strip()

def ask_for_confirmation(query):
    while True:
        accepted = input(f"{RED}{query} {RESET}[y/n]: ").strip().lower()
        if accepted in ['y', 'yes']:
            return True
        elif accepted in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'.")

def run_shell_command(command):
    if not ask_for_confirmation(f"Do you want to run the following command? {GREEN}{command}"):
        print("Command execution cancelled.")
        return "Command was not approved by user.", "", False
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True, bufsize=1)
    stdout_lines = []
    stderr_lines = []
    def read_stream(stream, lines):
        for line in iter(stream.readline, ''):
            print(line, end='')
            lines.append(line)
        stream.close()
    t1 = threading.Thread(target=read_stream, args=(process.stdout, stdout_lines))
    t2 = threading.Thread(target=read_stream, args=(process.stderr, stderr_lines))
    t1.start()
    t2.start()
    process.wait()
    t1.join()
    t2.join()
    return "".join(stdout_lines), "".join(stderr_lines), True

def short_random_id():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))

def tts_to_anki_media(text, language):
    audio_filename = re.sub(r'[^a-zA-Z0-9]', '_', text).strip('_')[:30] + short_random_id() + ".mp3"
    audio_filepath = os.path.join(os.path.expanduser("~/anki_media"), audio_filename)
    azure_tts(text, audio_filepath, language)
    return audio_filename

def translate_items(texts, source_language, target_language):
    messages = [
        {"role": "system", "content": (
            f"You are a helpful assistant that translates {source_language} sentences to {target_language}. "
            "Provide a JSON object mapping each sentence to its translation, without additional text. The original sentence should be the key and the translated sentence should be the value.")},
        {"role": "user", "content": json.dumps(texts)}
    ]
    raw = query_agent("gpt-4.1-mini", messages)
    return parse_json(raw)

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"











def chat():
    instructions = {"role": "system", "content": (
        "You are a helpful assistant. If needed, you can execute shell commands on the host machine. "
        "You may output a line such as 'SHELL: `ls ~`' and the output will be provided.")}
    conversation_history = []

    while True:
        user_input = input(f"{RED}> {RESET}").strip()
        if user_input in ["wipe"]:
            conversation_history = []
            print(f"{GREEN}Wiped chat history.{RESET}\n")
            continue

        conversation_history.append({"role": "user", "content": user_input})

        while True:
            response = query_agent("gpt-4.1-mini", [instructions] + conversation_history[-20:])
            print(f"{GREEN}{response}{RESET}\n")
            conversation_history.append({"role": "assistant", "content": response})
            line_had_shell = False
            for line in response.splitlines():
                match = re.search(r'^SHELL: `([^`]*)`$', line)
                if match:
                    command = match.group(1)
                    stdout, stderr, line_had_shell = run_shell_command(command)
                    result_message = f"STDOUT: {stdout}\nSTDERR: {stderr}"
                    conversation_history.append({"role": "system", "content": result_message})
                    break
            if not line_had_shell:
                break

def rw():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    messages=[
        {"role": "system", "content": (
            "You are a helpful code assistant. The user will provide a file of code and a suggested change, "
            "and your job is to make a minimal edit implementing that change. Avoid commentary and extra formatting, only responding with the updated file.")},
        {"role": "user", "content": read_file(input_file)},
        {"role": "user", "content": input(f"{RED}> {RESET}").strip()}
    ]

    response = query_agent("gpt-4.1-mini", messages)
    input_path = Path(input_file)
    backup_file = input_path.with_name(input_path.name + ".old")
    shutil.copy2(input_file, backup_file)
    with open(input_file, 'w') as f:
        f.write(response)

    subprocess.run(["meld", str(backup_file), input_file])

    if ask_for_confirmation("Do you want to delete the backup file?"):
        backup_file.unlink()
        print("Backup file deleted.")
    else:
        print("Backup file retained.")

def insert_into_anki(translations, front_language, back_language):
    for front, back in translations.items():
        print(front+"\t"+back)
        front_audio_filename = tts_to_anki_media(front, front_language)
        back_audio_filename = tts_to_anki_media(back, back_language)
        anki_add_note(front_language, front, back, front_audio_filename, back_audio_filename)

def create_flashcards(sentences_prompt):
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--front-language", required=True, help="The language for the front of the flashcards.")
    parser.add_argument("-b", "--back-language", required=True, help="The language for the back of the flashcards.")
    parser.add_argument("topic", nargs="+")
    args = parser.parse_args()
    front_language = args.front_language.strip().capitalize()
    back_language = args.back_language.strip().capitalize()
    topic = " ".join(args.topic).strip()

    check_deck_exists(front_language)

    raw = query_agent("gpt-4.1-mini", [{"role": "system", "content": sentences_prompt.format(t=topic, fl=front_language)}])
    sentences = parse_json(raw)
    pprint(sentences)
    if not ask_for_confirmation("Continue?"):
        exit(1)
    translations = translate_items(sentences, front_language, back_language)
    pprint(translations)
    insert_into_anki(translations, front_language, back_language)

def teach():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--language", required=True, help="The language for the flashcards.")
    parser.add_argument("topic", nargs="+")
    args = parser.parse_args()
    lang = args.lang.strip().capitalize()
    topic = " ".join(args.topic).strip()
    sentences_prompt=[
        {"role": "system", "content": f"You are a helpful assistant that generates flashcards in {lang}. "
                                       "Provide a JSON object where each key is a question and each value is the answer, without any additional text or formatting. "
                                       "Aim for brevity in the answer field. "},
        {"role": "user", "content": f"Generate flashcards in {lang} about: {topic}."}
    ]

    check_deck_exists(front_language)

    raw = query_agent("gpt-4.1-mini", sentences_prompt)
    sentences = parse_json(raw)
    pprint(sentences)
    if not ask_for_confirmation("Continue?"):
        exit(1)
    insert_into_anki(translations, front_language, front_language)

def lecture():
    parser = argparse.ArgumentParser()
    parser.add_argument("level", choices=['easy', 'hard'], help="Learning level")
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    level = args.level
    sys.argv = [sys.argv[0]] + args.rest

    level_descriptions = {
        "easy": "children, aiming for ease of understanding",
        "hard": "graduate students"
    }
    level_desc = level_descriptions.get(level)

    sentences_prompt = (
        "You are an expert teacher of {t} in the {fl} language. "
        "Provide a JSON list of strings, containing sentences about {t} in {fl}, suitable for " + level_desc + ". Focus on technical specifics instead of trivia, and avoid extra commentary or text."
    )
    create_flashcards(sentences_prompt)

def vocab():
    sentences_prompt = (
        "You are a helpful assistant that generates sentences in {fl}. Provide a JSON list of sentences (each 3 to 7 words). "
        "The vocab in question is: {t}. Make 3 sentences for each vocab word. Avoid extra commentary or text."
    )
    create_flashcards(sentences_prompt)

def create_flashcards_from_vocab_list():
    parser = argparse.ArgumentParser(description="Choose an entry point")
    parser.add_argument("filepath", help="File containing vocab entries")
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    vocab_file_path = Path(args.filepath)
    sys.argv = [sys.argv[0]] + args.rest + ["EmptyTopic"]

    if not vocab_file_path.exists():
        print(f"Vocab file {vocab_file_path} does not exist.")
        sys.exit(1)

    with open(vocab_file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    words_to_use = lines[:2]
    if not words_to_use:
        print("No words found in vocab file.")
        sys.exit(1)

    # Prepare vocab string by joining words with commas or spaces
    vocab_str = ", ".join(words_to_use)

    sentences_prompt = (
        "You are a helpful assistant that generates sentences for {fl} learners. Provide a JSON list of sentences (each 3 to 7 words). "
        "The vocab in question is: " + vocab_str + ". Please create about 3 sentences, using these words a few times each. Avoid extra commentary or text."
    )
    create_flashcards(sentences_prompt)

    # Remove the top word from the file
    lines.pop(0)
    with open(vocab_file_path, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Choose an entry point")
    parser.add_argument("cmd", choices=["rw", "teach", "chat", "vocab", "vocabfile", "lecture"], help="Command to execute")
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    sys.argv = [sys.argv[0]] + args.rest
    if args.cmd == "rw":
        rw()
    elif args.cmd == "teach":
        teach()
    elif args.cmd == "chat":
        chat()
    elif args.cmd == "vocab":
        vocab()
    elif args.cmd == "vocabfile":
        create_flashcards_from_vocab_list()
    elif args.cmd == "lecture":
        lecture()
