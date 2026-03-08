#!/usr/bin/env python3
import readline  # Enables navigation using arrow keys and delete
import threading
from pprint import pprint
import argparse
import subprocess
from openai_utils import query_agent, RED, GREEN, RESET
from anki_utils import check_deck_exists, insert_into_anki, CardList
import re
from ask_for_confirmation import ask_for_confirmation

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

instructions = {"role": "system", "content": (
    "You are a helpful chat assistant, specializing in pedagogy. "
    "Respond concisely in one or two paragraphs, but be sure to fully answer the user's question. "
)}
conversation_history = []

while True:
    user_input = input(f"{RED}> {RESET}").strip()
    if user_input in ["exit", "quit"]:
        break

    # enable debug mode
    if "[d]" in user_input:
        debug_instr = {"role": "system", "content": (
            "The user has requested debug assistance on their linux machine. "
            "From now on, to invoke a command, use this sample syntax on the first line of your response: 'SHELL: `ls ~`'. "
            "The command must be packed into the first line, and the output will be provided to you for inspection. "
            "On subsequent lines, briefly explain the motivation behind the command. "
            "If no command is needed, simply continue to respond in text. "
        )}
        conversation_history.append(debug_instr)

    # Add a file to the conversation
    if "[f=" in user_input:
        # Match substring like "[f=path/to/file]"
        regex = r'\[f=([^\]]+)\]'
        path = re.search(regex, user_input).group(1).strip()
        if not os.path.isfile(path):
            print(f"File '{path}' does not exist.")
            continue
        print(f"Adding file '{path}'...")
        file_content = read_file(path)
        conversation_history.append({"role": "system", "content": f"The user has provided the following file content from '{path}':\n```\n{file_content}\n```"})
        continue

    # Anki cards
    if "[a=" in user_input:
        anki_instr = (
            "The user has requested 8 anki cards covering this information. "
            "Focus the cards not on trivia such as dates, but instead the most critical contextual information about the topic. "
            "The front of the card should provide all relevant context for a final question. "
            "The question itself should ask for a single word, place, fact, name, or datapoint so that the user's answer can easily be judged as right or wrong. "
            "An example of a good card is as follows: "
            "Front: 'Conway studied the endgame of Go, resulting in the development of Combinatorial Game Theory. What is the Japanese name for the endgame of Go?' "
            "Back: 'Yose' "
            "Please make the cards in the user's native language ({fl}). "
        )
        # Match substring like "[a=Spanish]"
        regex = r'\[a=([^\]]+)\]'
        language = re.search(regex, user_input).group(1)
        language = language.strip().capitalize()
        anki_history = conversation_history.copy()
        anki_history.append({"role": "system", "content": anki_instr.format(fl=language)})
        if not check_deck_exists(language):
            continue
        raw = query_agent(anki_history, text_format=CardList)
        pprint(raw)
        if not ask_for_confirmation("Continue?"):
            exit(1)
        insert_into_anki(raw, language, language)
        continue

    conversation_history.append({"role": "user", "content": user_input})
    while True:
        response = query_agent([instructions] + conversation_history[-20:])
        print(f"{GREEN}{response}{RESET}\n")
        conversation_history.append({"role": "assistant", "content": response})
        line_had_shell = False
        line1 = response.splitlines()[0]
        # Check if the first line of the response matches the pattern "SHELL: `command`"
        match = re.search(r'^SHELL: `([^`]+)`', line1)
        if match:
            command = match.group(1)
            stdout, stderr, line_had_shell = run_shell_command(command)
            result_message = f"STDOUT: {stdout}\nSTDERR: {stderr}"
            conversation_history.append({"role": "system", "content": result_message})
        else:
            break

        print("Goodbye!")
