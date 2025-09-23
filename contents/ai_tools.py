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
    try:
        with open(input_file, 'r') as f:
            file_content = f.read()
            return file_content
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

def anki_add_note(deck, front, back, front_sound, back_sound, model_name="BasicWithTTS"):
    notes = [{
        "deckName": deck,
        "modelName": model_name,
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
    return read_file(Path.home() / 'openaikey').strip()

client = OpenAI(api_key=get_openai_key())

def query_agent(messages, tf=None):
    try:
        response = client.responses.parse(
            model="gpt-5-mini",
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

def generate_tts(text, instructions, audio_filepath):
    try:
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="nova",
            input=text,
            instructions=instructions
        ) as response:
            response.stream_to_file(audio_filepath)
    except Exception as e:
        print(f"Error generating TTS: {e}")

def tts_to_anki_media(text, language):
    audio_filename = re.sub(r'[^a-zA-Z0-9]', '_', text).strip('_')[:30] + short_random_id() + ".mp3"
    audio_filepath = os.path.join(os.path.expanduser("~/anki_media"), audio_filename)
    instructions = lang_tts_prompt(language)
    generate_tts(text, instructions, audio_filepath)
    return audio_filename

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











def chat():
    instructions = {"role": "system", "content": (
        "You are a helpful chat assistant, specializing in pedagogy. "
    )}
    debug_instr = {"role": "system", "content": (
        "The user has requested debug assistance on their linux machine. "
        "From now on, to invoke a command, use this sample syntax on the first line of your response: 'SHELL: `ls ~`'. "
        "The command must be packed into the first line, and the output will be provided to you for inspection. "
        "On subsequent lines, briefly explain the motivation behind the command. "
        "If no command is needed, simply continue to respond in text. "
    )}
    anki_instr = (
        "The user has requested anki cards covering this information. "
        "The front of the card should provide all relevant context for a final question. "
        "The question itself shouldask for a single fact, name, date, or datapoint so that the user's answer can easily be judged as right or wrong. "
        "An example of a good card is as follows: "
        "Front: 'Conway studied the endgame of Go, resulting in the development of Combinatorial Game Theory. What is the Japanese name for the endgame of Go?' "
        "Back: 'Yose' "
        "Please make the cards in the user's native language ({fl}). "
    )
    conversation_history = []

    while True:
        user_input = input(f"{RED}> {RESET}").strip()
        if user_input in ["exit", "quit"]:
            break

        if "[d]" in user_input:
            conversation_history.append(debug_instr)
        if "[a=" in user_input:
            # Match substring like "[a=Spanish]"
            regex = 
            language = 
            language = language.strip().capitalize()
            conversation_history.append({"role": "system", "content": anki_instr.format(fl=language)})
            create_flashcards(conversation_history, language, language)

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

def rw():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    lines = read_file(Path(input_file))

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

    # If the first or last line of the response conatains ` characters to represent code
    if response.splitlines()[0].startswith('```') or response.splitlines()[-1].startswith('```'):
        response = '\n'.join(response.splitlines()[1:-1]).strip()


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

def insert_into_anki(cards, front_language, back_language):
    for card in cards.cards:
        front = card.front
        back = card.back
        print(front+"\t"+back)
        front_audio_filename = tts_to_anki_media(front, front_language)
        back_audio_filename = tts_to_anki_media(back, back_language)
        anki_add_note(front_language, front, back, front_audio_filename, back_audio_filename)

def create_flashcards(chat_history, front_language, back_language):
    check_deck_exists(front_language)

    raw = query_agent(chat_history)
    print(raw)
    if not ask_for_confirmation("Continue?"):
        exit(1)
    translations = translate_items(raw, front_language, back_language)
    pprint(translations)
    insert_into_anki(translations, front_language, back_language)

def vocab(front_language, back_language):
    parser = argparse.ArgumentParser()
    parser.add_argument("topic", nargs="+")
    args = parser.parse_args()
    topic = " ".join(args.topic).strip()
    instructions = (
        "You are an assistant that generates short trivia facts (5-10 words) in {fl}. "
        "Make a diverse JSON list of strings, and be sure to use the following vocab words 2 times each: {t}. "
        "You may change the conjugation or tense of the vocab words as needed to ensure the sentences are grammatical. "
        "For example, if the vocab word were 'Oil', you might say 'The largest oil field is in Saudi Arabia.' "
        "The strings should be factual, kid-friendly/simple to understand, and refer to specific historical events or scientific knowledge. "
    )

    prompt = [{"role": "system", "content": instructions.format(t=topic, fl=front_language)}]

    create_flashcards(prompt, front_language, back_language)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Choose an entry point")
    parser.add_argument("cmd", choices=["rw", "chat", "vocab"], help="The command to run")
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    sys.argv = [sys.argv[0]] + args.rest
    if args.cmd == "rw":
        rw()
    elif args.cmd == "chat":
        chat()
    elif args.cmd == "vocab":
        parser = argparse.ArgumentParser()
        parser.add_argument("-f", "--front-language", required=True, help="The language for the front of the flashcards.")
        parser.add_argument("-b", "--back-language", required=True, help="The language for the back of the flashcards.")
        args = parser.parse_args()
        front_language = args.front_language.strip().capitalize()
        back_language = args.back_language.strip().capitalize()
        vocab(front_language, back_language)
