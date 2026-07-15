#!/usr/bin/env python3
import readline  # Enables navigation using arrow keys and delete
from openai_utils import query_agent, RED, GREEN, RESET

instructions = {"role": "system", "content": (
    "You are a friendly and playful test-prep assistant. Your job is to ask the user questions about a single topic they provide. "
    "Ask questions to the user."
    "If the answer is incorrect or incomplete, concisely explain the correct answer and immediately continue with the next question. "
    "If you are able to identify a specific area of weakness, instruct the user further on that topic to guide them to a more general understanding. "
)}
current_topic = None

conversation_history = []

print("Enter a topic to begin quiz (or 'exit' to quit).")

while True:
    user_input = input(f"{RED}> {RESET}").strip()
    if user_input.lower() in ["exit", "quit"]:
        print("Goodbye!")
        break

    if current_topic is None:
        current_topic = {"role": "user", "content": f"The quiz topic is: {user_input}. Please begin asking questions."}
    else:
        conversation_history.append({"role": "user", "content": user_input})

    response = query_agent( [instructions, current_topic] + conversation_history[-20:] )
    print(f"{GREEN}{response}{RESET}\n")
    conversation_history.append({"role": "assistant", "content": response})
