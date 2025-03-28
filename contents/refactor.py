#!/usr/bin/env python3
import sys
import openai
from pathlib import Path
import subprocess

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input_file> <prompt>")
        sys.exit(1)

    input_file = sys.argv[1]
    user_input = " ".join(sys.argv[2:])

    try:
        with open(input_file, 'r') as f:
            file_content = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

    try:
        home = Path.home()
        with open(home / 'openaikey', 'r') as keyFile:
            openai_api_key = keyFile.readline().strip()
    except Exception as e:
        print(f"Error reading OpenAI API key: {e}")
        sys.exit(1)
    
    if not openai_api_key:
        print("Error: OpenAI API key is missing.")
        sys.exit(1)
    
    openai.api_key = openai_api_key
    
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful code assistant. The user will provide a file of code and a suggested change, and your job is to make a minimal edit implementing that change. Do not change unrelated parts of the file. Avoid commentary, only responding with the updated code."},
                {"role": "user", "content": file_content},
                {"role": "user", "content": user_input}
            ],
        )

        response = completion.choices[0].message.content.strip()
        input_path = Path(input_file)
        output_file = input_path.parent / (input_path.stem + ".edited" + input_path.suffix)
        with open(output_file, 'w') as f:
            f.write(response)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    subprocess.run(["meld", input_file, str(output_file)])

if __name__ == '__main__':
    main()

