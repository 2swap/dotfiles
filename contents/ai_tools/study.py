#!/usr/bin/env python3
from pprint import pprint
import argparse
from openai_utils import query_agent
from anki_utils import check_deck_exists, insert_into_anki, CardList
from ask_for_confirmation import ask_for_confirmation

def generate_tech_cards(topic, language):
    instructions = (
        "You are a flash-card study assistant. "
        "The user has requested cards about {t} written in {lang}. "
        "Both the question on the front and question on the back should be as concise as possible. "
    )
    prompt = [{"role": "system", "content": instructions.format(t=topic, lang=language)}]

    check_deck_exists(language)

    raw = query_agent(prompt, text_format=CardList)

    pprint(raw)
    if not ask_for_confirmation("Continue and create these 3 cards?"):
        exit(1)

    insert_into_anki(raw, language, language)

parser = argparse.ArgumentParser()
parser.add_argument("-l", "--language", required=False, help="Language to write the question and answer in (default: Indonesian).")
parser.add_argument("topic", nargs="+")
args = parser.parse_args()

language = args.language or "Indonesian"
language = language.capitalize().strip()

topic = " ".join(args.topic).strip()
generate_tech_cards(topic, language)
