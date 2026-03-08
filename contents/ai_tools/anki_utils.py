import requests
import os
import re
import random
import string
from pydantic import BaseModel
import json
from openai_utils import query_agent, generate_tts

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
        exit(0)

def check_deck_exists(deck_name):
    decks = anki_connect("deckNames")["result"]
    if not (deck_name in decks):
        anki_connect("createDeck", {"deck": deck_name})
        print(f"Deck '{deck_name}' created.")
    return True

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

def insert_into_anki(cards, front_language, back_language):
    for card in cards.cards:
        front = card.front
        back = card.back
        print(front+"\t"+back)
        front_audio_filename = tts_to_anki_media(front, front_language)
        back_audio_filename = tts_to_anki_media(back, back_language)
        anki_add_note(front_language, front, back, front_audio_filename, back_audio_filename)

def translate_items(texts, source_language, target_language):
    messages = [
        {"role": "system", "content": (
            f"You are a {source_language} to {target_language} translator of sentence lists. Provide the original sentences on the front and the translations on the back. ")},
        {"role": "user", "content": json.dumps(texts)}
    ]
    return query_agent(messages, text_format=CardList)

def short_random_id():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))

def tts_to_anki_media(text, language):
    audio_filename = re.sub(r'[^a-zA-Z0-9]', '_', text).strip('_')[:30] + short_random_id() + ".mp3"
    audio_filepath = os.path.join(os.path.expanduser("~/anki_media"), audio_filename)
    generate_tts(text, language, audio_filepath)
    return audio_filename
