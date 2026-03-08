#!/usr/bin/env python3
import argparse
import tempfile
import subprocess
import sys
from openai_utils import RED, RESET, query_agent
from ask_for_confirmation import ask_for_confirmation
from pathlib import Path
from read_file import read_file
import os

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
    print("Goodbye!")
    sys.exit(0)

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
