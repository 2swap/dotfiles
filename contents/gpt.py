#!/usr/bin/env python3
import sys
import openai
import readline  # Enables navigation using arrow keys and delete
from pathlib import Path

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

def main():
    # Ensure the OpenAI API key is set.
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
    
    # Start interactive chat
    conversation_history = []
    
    while True:
        try:
            user_input = input(f"{RED}> {RESET}").strip()
            
            # Append user input to conversation history
            conversation_history.append({"role": "user", "content": user_input})
            
            # Query OpenAI API
            completion = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant involved in a continuous conversation."}
                ] + conversation_history,
            )
            
            # Extract and print response
            response = completion.choices[0].message.content.strip()
            print(f"{GREEN}{response}{RESET}\n")
            
            # Append response to conversation history
            conversation_history.append({"role": "assistant", "content": response})

            conversation_history = conversation_history[-2:]
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()

