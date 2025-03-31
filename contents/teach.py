#!/usr/bin/env python3
import sys
import os
import json
import requests
import openai
import re

def main():
    # Check that a subject argument was provided.
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <subject>")
        sys.exit(1)
    
    # Join all arguments to support subjects with spaces.
    subject = " ".join(sys.argv[1:]).strip()

    # Ensure the OpenAI API key is set.
    keyFile = open('/home/2swap/openaikey', 'r')
    openai_api_key = keyFile.readline().rstrip()
    keyFile.close()
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)
    openai.api_key = openai_api_key

    # Query the OpenAI API to generate flashcards about the subject.
    prompt = (
        f"Generate a few flashcards about: {subject}."
    )
    
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a helpful assistant that generates flashcards. "
                                               "Provide a JSON object where each key is a question and each value is the answer, without any additional text or formatting. "
                                               "Stick to the core technical details of a subject, and avoid non-technical trivia. "
                                               "There should be one unambiguously correct answer- avoid open-ended questions such as 'What are some examples of Carnivora'."
                                               "Ask questions redundantly or bidirectionally- two cards such as 'What occurs during prometaphase?' and 'What stage involves spindle attachment?' are helpful. "
                                               "For foreign names, places, or concepts, always include foreign language text as well as romanized text. "},
                {"role": "user", "content": prompt}
            ],
        )
    except Exception as e:
        print("Error querying OpenAI API:", e)
        sys.exit(1)
    
    # Extract JSON from the OpenAI response
    raw_response = completion.choices[0].message.content.strip()
    # Find the first '{' and the last '}'
    json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)

    if json_match:
        flashcards_json = json_match.group(0)  # Extract the matched JSON string
        try:
            flashcards = json.loads(flashcards_json)  # Parse JSON
        except json.JSONDecodeError as e:
            print("Failed to decode JSON from OpenAI response. Response was:")
            print(flashcards_json)
            sys.exit(1)
    else:
        print("No valid JSON found in OpenAI response. Full response was:")
        print(raw_response)
        sys.exit(1)
    
    # Build the list of note payloads for AnkiConnect.
    notes = []
    for question, answer in flashcards.items():
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
    
    payload = {
        "action": "addNotes",
        "version": 6,
        "params": {
            "notes": notes
        }
    }
    
    # Send the flashcards to AnkiConnect.
    anki_url = "http://localhost:8765"
    try:
        anki_response = requests.post(anki_url, json=payload)
        result = anki_response.json()
        print("AnkiConnect response:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print("Error sending request to AnkiConnect:", e)
        sys.exit(1)

if __name__ == '__main__':
    main()

