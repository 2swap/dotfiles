#!/usr/bin/env python3
from pprint import pprint
import argparse
from openai_utils import query_agent
from anki_utils import check_deck_exists, insert_into_anki, translate_items
from ask_for_confirmation import ask_for_confirmation

def what_language_on_front(topic):
    # Use OpenAI to determine the language of the vocab words provided.
    instructions = (
        "You are a language detection assistant. "
        "The vocab words are: {t}. "
        "The language will likely be Spanish, Indonesian, Japanese, Turkish, or Chinese. "
        "Return the name of the language, with no other text."
    )
    prompt = [{"role": "system", "content": instructions.format(t=topic)}]
    raw = query_agent(prompt, model="gpt-5-nano")
    # Clean the response to get just the language name.
    language = raw.strip().capitalize()

    # Ask user for confirmation, since the model might be wrong.
    if not ask_for_confirmation(f"Is the language '{language}'?"):
        language = input("Please enter the correct language: ").strip().capitalize()

    return language

def what_language_on_back(front_language):
    if front_language == "Spanish":
        return "English"
    if front_language == "Indonesian" or front_language == "Japanese":
        return "Spanish"
    else:
        return "Indonesian"

def vocab(front_language, back_language, topic):
    instructions = (
        "You are an assistant that generates short phrases (2-4 words) in {fl}. "
        "Make a JSON list of strings, with 3 strings for each of these vocab words: {t}. "
        "You may change the conjugation or tense of the vocab words. "
        "For example, if the vocab word were 'inside', you might say 'use your inside voice', 'flip it inside out', 'inside or outside', 'insider trading', etc. "
    )

    prompt = [{"role": "system", "content": instructions.format(t=topic, fl=front_language)}]

    check_deck_exists(front_language)
    raw = query_agent(prompt)
    print(raw)
    if not ask_for_confirmation("Continue?"):
        exit(1)
    translations = translate_items(raw, front_language, back_language)
    pprint(translations)
    insert_into_anki(translations, front_language, back_language)

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--front-language", required=False, help="The language for the front of the flashcards.")
parser.add_argument("-b", "--back-language", required=False, help="The language for the back of the flashcards.")
parser.add_argument("words", nargs="+")
args = parser.parse_args()

front_language = args.front_language
if not front_language:
    front_language = what_language_on_front(args.words)
back_language = args.back_language
if not back_language:
    back_language = what_language_on_back(front_language)

front_language = front_language.capitalize().strip()
back_language = back_language.capitalize().strip()

words = " ".join(args.words).strip()
vocab(front_language, back_language, words)
