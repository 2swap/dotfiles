#!/usr/bin/env python3
import sys
from openai import OpenAI
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
import tempfile
from pydantic import BaseModel

class Card(BaseModel):
    front: str
    back: str

class CardList(BaseModel):
    cards: list[Card]

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

client = OpenAI(api_key=get_openai_key())

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

def query_agent(messages, tf=None):
    try:
        response = client.responses.parse(
            model="gpt-4.1-mini",
            input=messages,
            **({'text_format': tf} if tf else {})
        )
        return response.output_parsed if tf else response.output_text
    except Exception as e:
        print("Error:", e)

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
        user_input = input(f"What was wrong? {RED}> {RESET}").strip()
        return "Command was not approved by user. Reason: " + user_input, "", False
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

def lang_tts_prompt(lang):
    if lang.lower() == "indonesian":
        return "Bicara dalam bahasa Indonesia."
    if lang.lower() == "spanish":
        return "Habla en español."
    if lang.lower() == "japanese":
        return "日本語で話してください。"
    else:
        return f"Speak in {lang}."

def tts_to_anki_media(text, language):
    audio_filename = re.sub(r'[^a-zA-Z0-9]', '_', text).strip('_')[:30] + short_random_id() + ".mp3"
    audio_filepath = os.path.join(os.path.expanduser("~/anki_media"), audio_filename)
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="nova",
        input=text,
        instructions=lang_tts_prompt(language),
    ) as response:
        response.stream_to_file(audio_filepath)
    return audio_filename

def tts_to_temp_file(text):
    temp_audio_filepath = os.path.join(tempfile.gettempdir(), "temp_tts_" + short_random_id() + ".mp3")
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="nova",
        input=text,
        instructions="Speak clearly and assertively in the appropriate language.",
    ) as response:
        response.stream_to_file(temp_audio_filepath)
    print(f"Temporary audio file created at {temp_audio_filepath}")
    return temp_audio_filepath

def play_audio_file(audio_path):
    subprocess.run(["ffplay", "-nodisp", "-autoexit", audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def translate_items(texts, source_language, target_language):
    messages = [
        {"role": "system", "content": (
            f"You are a {source_language} to {target_language} translator of sentence lists. Provide the original sentences on the front and the translations on the back. ")},
        {"role": "user", "content": json.dumps(texts)}
    ]
    return query_agent(messages, CardList)

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"











def debug():
    instructions = {"role": "system", "content": (
        "You are a debug assistant. "
        "To invoke a command, send a two-line reply. "
        "On the first line, use this syntax: 'SHELL: `ls ~`'. "
        "The command must be packed into one line, and the output will be provided to you for inspection. "
        "On the second line, in one sentence, explain your command. "
        "If no command is needed, simply respond in text. "
    )}
    conversation_history = []

    while True:
        user_input = input(f"{RED}> {RESET}").strip()
        if user_input in ["wipe"]:
            conversation_history = []
            print(f"{GREEN}Wiped chat history.{RESET}\n")
            continue
        if user_input in ["exit", "quit"]:
            break

        conversation_history.append({"role": "user", "content": user_input})

        while True:
            response = query_agent([instructions] + conversation_history[-20:])
            print(f"{GREEN}{response}{RESET}\n")
            conversation_history.append({"role": "assistant", "content": response})
            line_had_shell = False
            line1 = response.splitlines()[0]
            match = re.search(r'^SHELL: `([^`]*)`$', line1.strip())
            if match:
                command = match.group(1)
                stdout, stderr, line_had_shell = run_shell_command(command)
                result_message = f"STDOUT: {stdout}\nSTDERR: {stderr}"
                conversation_history.append({"role": "system", "content": result_message})
            else:
                break

    print("Goodbye!")

def chat(voice):
    instructions = {"role": "system", "content": (
        "You are a helpful chat assistant, specializing in pedagogy. "
    )}
    conversation_history = []

    while True:
        user_input = input(f"{RED}> {RESET}").strip()
        if user_input in ["wipe"]:
            conversation_history = []
            print(f"{GREEN}Wiped chat history.{RESET}\n")
            continue
        if user_input in ["exit", "quit"]:
            break

        conversation_history.append({"role": "user", "content": user_input})

        response = query_agent([instructions] + conversation_history[-20:])
        print(f"{GREEN}{response}{RESET}\n")
        conversation_history.append({"role": "assistant", "content": response})

        if voice:
            try:
                tts_audio_path = tts_to_temp_file(response)
                play_audio_file(tts_audio_path)
            except Exception as e:
                print(f"Error playing TTS audio: {e}")

    print("Goodbye!")

def rw():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    input_path = Path(input_file)
    try:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

    start_indices = [i for i, line in enumerate(lines) if 'RW_'+'START' in line]
    end_indices = [i for i, line in enumerate(lines) if 'RW_'+'END' in line]

    # Validate counts
    if len(start_indices) != len(end_indices):
        print("Error: Number of START lines does not match number of END lines.")
        sys.exit(1)
    if len(start_indices) > 1 or len(end_indices) > 1:
        print("Error: More than one START or END found.")
        sys.exit(1)
    if len(start_indices) == 1 and start_indices[0] > end_indices[0]:
        print("Error: START occurs after END.")
        sys.exit(1)

    if len(start_indices) == 1:
        start = start_indices[0]
        end = end_indices[0]
        section_lines = lines[start+1:end]
        section_text = ''.join(section_lines)
    else:
        section_text = ''.join(lines)  # whole file if no markers

    human_prompt = input(f"{RED}> {RESET}").strip()
    if len(human_prompt) < 7:
        return

    messages=[
        {"role": "system", "content": (
            "You are a helpful code assistant. The user will provide a file of code and a suggested change, "
            "and your job is to make a minimal edit implementing that change. "
            "Pay particular attention to leaving the indentation as it was, so the updated version can be directly copied to the source file. "
            "Avoid commentary and extra formatting, only responding with the updated file or content.")},
        {"role": "user", "content": section_text},
        {"role": "user", "content": human_prompt}
    ]

    response = query_agent(messages)

    # Create temp files for meld and editing
    with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as temp_original:
        temp_original_path = temp_original.name
        temp_original.write(section_text)
        temp_original.flush()
    with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as temp_rewritten:
        temp_rewritten_path = temp_rewritten.name
        temp_rewritten.write(response)
        temp_rewritten.flush()

    subprocess.run(["meld", temp_original_path, temp_rewritten_path])

    if ask_for_confirmation("Do you want to delete the temporary files and copy the changes back to the original file?"):
        try:
            # Read the rewritten content back
            with open(temp_rewritten_path, 'r', encoding='utf-8') as f:
                updated_content = f.read()
            if len(start_indices) == 1:
                # Replace section in original lines
                new_lines = lines[:start+1] + [updated_content if updated_content.endswith('\n') else updated_content+'\n'] + lines[end:]
            else:
                # Replace whole file content
                new_lines = [updated_content if updated_content.endswith('\n') else updated_content+'\n']
            # Write back to original file
            with open(input_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"Updated content copied back to {input_file}.")
        except Exception as e:
            print(f"Error copying back updated content: {e}")

        # Delete temp files
        try:
            os.unlink(temp_original_path)
            os.unlink(temp_rewritten_path)
            print("Temporary files deleted.")
        except Exception as e:
            print(f"Error deleting temporary files: {e}")
    else:
        print(f"Temporary files at {temp_original_path}, {temp_rewritten_path}")

def summarize():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} language <input_file>")
        sys.exit(1)

    language = sys.argv[1]
    check_deck_exists(language)
    input_file = sys.argv[2]
    input_path = Path(input_file)
    try:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)
    content = ''.join(lines)

    messages=[
        {"role": "system", "content": (
            "You are a pedagogical assistant. The user will provide some learning material. "
            "Please make a list of 10 flash cards about the facts presented in the material. The answer field should not have more than 4 words. ")},
        {"role": "user", "content": content}
    ]

    response = query_agent(messages, CardList)
    insert_into_anki(response, language, language)

def insert_into_anki(cards, front_language, back_language):
    for card in cards.cards:
        front = card.front
        back = card.back
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

    raw = query_agent([{"role": "system", "content": sentences_prompt.format(t=topic, fl=front_language)}])
    print(raw)
    if not ask_for_confirmation("Continue?"):
        exit(1)
    translations = translate_items(raw, front_language, back_language)
    pprint(translations)
    insert_into_anki(translations, front_language, back_language)

def teach():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--language", required=True, help="The language for the flashcards.")
    parser.add_argument("topic", nargs="+")
    args = parser.parse_args()
    lang = args.language.strip().capitalize()
    topic = " ".join(args.topic).strip()
    sentences_prompt=[
        {"role": "system", "content": f"You are a helpful assistant that generates flashcards in {lang}. "
                                       "Provide a list of cards where the front is a question and the back is the answer. "
                                       "The answer field should be brief- no longer than 5 words. "
                                       "Questions should have a single correct answer. "
                                       "'Give an example of a Coelomate' is a bad question since there is not a unique answer. "
                                       "A better question would be: 'Are flatworms Coelomates, Pseudocoelomates, or Acoelomates? "
                                       "Use the question field to give background or provide inspiration. Instead of 'What does GNU stand for?', "
                                       "opt for 'GNU is an example of a recursive acronym. What does it stand for?' "},
        {"role": "user", "content": f"Generate flashcards in {lang} about: {topic}."}
    ]

    check_deck_exists(lang)

    sentences = query_agent(sentences_prompt, CardList)
    pprint(sentences)
    if not ask_for_confirmation("Continue?"):
        exit(1)
    insert_into_anki(sentences, lang, lang)

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
        "You are an assistant that generates very short (5-11 word) trivia facts in {fl}. "
        "Make a diverse JSON list of strings, and be sure to use the following vocab words 3 times each: {t}. "
        "You may change the form of the vocab words as needed to ensure the sentences are grammatical. "
        "For example, if the vocab word were 'brain', you might say 'Romans used mouse brains as toothpaste.' "
        "Do not add any extra formatting or text. "
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
    parser.add_argument("cmd", choices=["summarize", "rw", "teach", "chat", "debug", "vocab", "vocabfile", "lecture", "vchat"], help="Command to execute")
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    sys.argv = [sys.argv[0]] + args.rest
    if args.cmd == "rw":
        rw()
    elif args.cmd == "teach":
        teach()
    elif args.cmd == "debug":
        debug()
    elif args.cmd == "chat":
        chat(False)
    elif args.cmd == "vchat":
        chat(True)
    elif args.cmd == "vocab":
        vocab()
    elif args.cmd == "vocabfile":
        create_flashcards_from_vocab_list()
    elif args.cmd == "lecture":
        lecture()
    elif args.cmd == "summarize":
        summarize()
