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
from gtts import gTTS

def read_file(input_file):
    print(f"Reading file {input_file}")
    try:
        with open(input_file, 'r') as f:
            file_content = f.read()
            return file_content
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

def send_to_anki(notes):
    payload = {
        "action": "addNotes",
        "version": 6,
        "params": {
            "notes": notes
        }
    }

    print("Sending to anki...")
    # Send the flashcards to AnkiConnect.
    anki_url = "http://localhost:8765"
    try:
        anki_resp = requests.post(anki_url, json=payload)
        result = anki_resp.json()
        print("AnkiConnect response:")
        print(json.dumps(result, indent=2))
        print("AnkiConnect error: " + str(result["error"]))
    except Exception as e:
        print("Error sending request to AnkiConnect:", e)
        sys.exit(1)

def parse_json(raw):
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        flashcards_json = json_match.group(0)
        try:
            sentences_dict = json.loads(flashcards_json)
        except json.JSONDecodeError as e:
            print("Failed to decode JSON. Raw string was:")
            print(flashcards_json)
            sys.exit(1)
    else:
        print("No valid JSON found. Raw string was:")
        print(raw)
        sys.exit(1)
    return sentences_dict

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

openai.api_key = get_openai_key()

def openai_tts(sentence, audio_filepath):
    try:
        tts_resp = openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=sentence,
        )
        tts_resp.stream_to_file(audio_filepath)
    except Exception as e:
        print("Error generating TTS audio for sentence with OpenAI:", e)
        sys.exit(1)

def gtts_tts(sentence, audio_filepath, lang):
    try:
        tts = gTTS(text=sentence, lang=lang)
        tts.save(audio_filepath)
    except Exception as e:
        print("Error generating TTS audio for sentence with gTTS:", e)
        sys.exit(1)

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
        accepted = input(f"{RED}{query} {RED}[y/n]: ").strip().lower()
        if accepted in ['y', 'yes']:
            return True
        elif accepted in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'.")

def run_shell_command(command):
    if not ask_for_confirmation(f"Do you want to run the following command? {GREEN}{command}"):
        print("Command execution cancelled.")
        return "Command was not approved by user.", ""

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
    return "".join(stdout_lines), "".join(stderr_lines)

def get_gtts_lang(language):
    mapping = {
        "english": "en",
        "french": "fr",
        "spanish": "es",
        "german": "de",
        "italian": "it",
        "japanese": "ja",
        "chinese": "zh-CN",
        "russian": "ru",
        "korean": "ko",
        "portuguese": "pt",
        "arabic": "ar",
        "Indonesian": "id",
        "Turkish": "tr"
    }

    return mapping.get(language.lower(), "en")

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"











def chat():
    conversation_history = [{"role": "system", "content": (
                "You are a helpful assistant involved in a continuous conversation. You can also execute shell commands on "
                "the host machine. When you decide to execute a shell command, output a line starting with 'SHELL:' followed "
                "by the command to execute. The command will be executed and its stdout and stderr will be provided back to you "
                "in the conversation context.")}]

    while True:
        user_input = input(f"{RED}> {RESET}").strip()
        if len(user_input) < 5:
            conversation_history = []
            print(f"{GREEN}Wiped chat history.{RESET}\n")
            continue

        conversation_history.append({"role": "user", "content": user_input})

        while True:
            response = query_agent("gpt-4o-mini", conversation_history[-10:])
            print(f"{GREEN}{response}{RESET}\n")
            conversation_history.append({"role": "assistant", "content": response})
            line_had_shell = False
            for line in response.splitlines():
                if line.startswith("SHELL:"):
                    command = line[len("SHELL:"):].strip()
                    stdout, stderr = run_shell_command(command)
                    result_message = f"STDOUT: {stdout}\nSTDERR: {stderr}"
                    conversation_history.append({"role": "system", "content": result_message})
                    line_had_shell = True
                    break
            if not line_had_shell:
                break

def rw():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    messages=[
        {"role": "system", "content": "You are a helpful code assistant. The user will provide a file of code and a suggested change, and your job is to make a minimal edit implementing that change. Avoid commentary, only responding with the updated file or part of the file."},
        {"role": "user", "content": read_file(input_file)},
        {"role": "user", "content": input(f"{RED}> {RESET}").strip()}
    ]

    response = query_agent("o3-mini", messages)
    input_path = Path(input_file)
    backup_file = input_path.with_name(input_path.name + ".old")
    input_path.rename(backup_file)
    with open(input_file, 'w') as f:
        f.write(response)

    subprocess.run(["meld", str(backup_file), input_file])

    if ask_for_confirmation("Do you want to delete the backup file?"):
        backup_file.unlink()
        print("Backup file deleted.")
    else:
        print("Backup file retained.")

def teach():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <subject>")
        sys.exit(1)
    subject = " ".join(sys.argv[1:]).strip()

    messages=[
        {"role": "system", "content": f"You are a helpful assistant that generates flashcards. "
                                       "Provide a JSON object where each key is a question and each value is the answer, without any additional text or formatting. "
                                       "Stick to the core technical details of a subject, and avoid non-technical trivia. " 
                                       "Ask questions redundantly or bidirectionally- two cards such as 'What occurs during prometaphase?' and 'What stage involves spindle attachment?' are helpful. "
                                       "Include lots of examples. "
                                       "Feature brevity over complete sentences in the answer field. "
                                       "For foreign names, places, or concepts, always include foreign language text as well as romanized text. "},
        {"role": "user", "content": f"Generate a few flashcards about: {subject}."}
    ]
    flashcards = parse_json(query_agent("gpt-4o-mini", messages))
    
    # Build the list of note payloads for AnkiConnect.
    notes = []
    for question, answer in flashcards.items():
        print(question+" "+answer)
        note = {
            "deckName": "Understanding",
            "modelName": "Basic",
            "fields": {
                "Front": question,
                "Back": answer
            },
            "options": {
                "allowDuplicate": True
            },
            "tags": []
        }
        notes.append(note)
    
    send_to_anki(notes)

def vocab():
    parser = argparse.ArgumentParser(description="Generate flashcards with TTS audio.")
    parser.add_argument("language", help="The language of the flashcards.")
    parser.add_argument("foreign_word", nargs="+", help="The foreign word(s) for which to generate sentences.")
    parser.add_argument("--tts", choices=["openai", "gtts"], default="gtts",
                        help="Specify whether to use 'openai' or 'gtts' for text-to-speech output.")
    args = parser.parse_args()

    language = args.language.strip()
    foreign_word = " ".join(args.foreign_word).strip()

    messages=[
        {"role": "system", "content": (
            "You are a helpful assistant that generates flashcards. Provide the flashcards as a JSON object "
            "where each key is a 4-8 word sentence (in the foreign language) and each value is the corresponding English translation. "
            "Ensure the sentences are natural and diverse. "
            "Even if the user types a romanized word, produce the target-language sentence in the native writing system. "
            "Do not include any extra commentary or formatting. "
        )},
        {"role": "user", "content": f"Here is a list of {language} words: '{foreign_word}'. Generate 3 sentences for each word in the list."}
    ]

    raw_response = query_agent("gpt-4o-mini", messages)

    sentences_dict = parse_json(raw_response)

    notes = []

    # Process each sentence and its translation.
    for sentence, translation in sentences_dict.items():
        print(sentence+"\t"+translation)
        # Create a file name for the audio snippet.
        # Remove non-word characters and replace spaces with underscores.
        audio_filename = re.sub(r'\W+', '_', sentence).strip('_') + ".mp3"
        # Construct the full file path in the media directory.
        audio_filepath = os.path.join(os.path.expanduser("~/anki_media"), audio_filename)
        if args.tts == "gtts":
            gtts_tts(sentence, audio_filepath, get_gtts_lang(language))
        else:
            openai_tts(sentence, audio_filepath)

        note = {
            "deckName": language.capitalize(),
            "modelName": "SentenceWithAudio",
            "fields": {
                "Text": sentence,
                "Translation": translation,
                "Audio": "[sound:"+audio_filename+"]",
            },
            "options": {
                "allowDuplicate": True
            },
            "tags": []
        }
        notes.append(note)

    send_to_anki(notes)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Choose an entry point: rw, teach, chat, vocab")
    parser.add_argument("cmd", choices=["rw", "teach", "chat", "vocab"], help="Command to execute")
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="Additional arguments for the selected command")
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
