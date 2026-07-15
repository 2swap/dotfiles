#!/usr/bin/env python3
import argparse
from pydantic import BaseModel
from pprint import pprint
from openai_utils import query_agent
from anki_utils import check_deck_exists, translate_items, tts_to_anki_media, anki_connect
from ask_for_confirmation import ask_for_confirmation

class VocabCard(BaseModel):
    Word: str
    Pronunciation: str
    Translation: str
    ExamplePhrase: str
    ExamplePhrasePronunciation: str
    ExamplePhraseTranslation: str

class VocabCardList(BaseModel):
    cards: list[VocabCard]

def what_language_on_front(topic):
    # Use OpenAI to determine the language of the vocab words provided.
    instructions = (
        "You are a language detection assistant. "
        "The user has requested: {t}. "
        "Frequent choices are Spanish, Indonesian, Japanese, Turkish, or Chinese, but it could be any language. "
        "If the user has provided a list of words, determine the language they are in. "
        "If they have requested a topic and specified a language, return that language. "
        "Return the name of the language, with no other text."
    )
    prompt = [{"role": "system", "content": instructions.format(t=topic)}]
    raw = query_agent(prompt, model="gpt-5.4-mini")
    language = raw.strip().capitalize()

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

def make_cards(front_language, back_language, topic):
    if front_language in ["Chinese", "Japanese"]:
        LogographyInstructions = "For Chinese or Japanese, use the pronunciation field and ExamplePhrasePronunciation field to write Pinyin or Furigana. "
    else:
        LogographyInstructions = "For languages other than Chinese or Japanese, leave the pronunciation fields blank. "
    if front_language == "Arabic":
        LogographyInstructions += "For Arabic, make sure to include tashkeel (diacritics) in the word field, and leave the pronunciation fields blank. "
    instructions = (
        f"You are a {front_language} language learning assistant. "
        f"The user is learning these words: {topic}. "
        "Create some flashcards to help them learn. "
        f"Each flash card should have the specified word in the target language, a pronunciation field, and a {back_language} translation. "
        f"{LogographyInstructions}"
        f"Furthermore, for each word, make a short phrase that uses the word in context, and provide a translation of that phrase in {back_language}. "
        "Avoid adding details which don't contribute to understanding of the word's core meaning: "
        "prefer 'Afraid of spiders' to 'I am afraid' or 'not afraid', since 'spiders' is more specific and illustrative of the word 'afraid'. "
    )
    prompt = [{"role": "system", "content": instructions}]
    raw = query_agent(prompt, text_format=VocabCardList, model="gpt-5.5")
    return raw

def anki_add_vocab_note(deck, word, pronunciation, translation, front_sound, back_sound):
    notes = [{
        "deckName": deck,
        "modelName": "VocabCard",
        "fields": {
            "Word": word,
            "Pronunciation": pronunciation,
            "Translation": translation,
            "FrontTTS": "[sound:"+front_sound+"]",
            "BackTTS": "[sound:"+back_sound+"]",
        },
        "options": {
            "allowDuplicate": True
        },
        "tags": []
    }]
    resp_json = anki_connect("addNotes", { "notes": notes } )

def anki_add_sentence_note(deck, front, back, front_sound, back_sound):
    notes = [{
        "deckName": deck,
        "modelName": "BasicWithTTS",
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

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--front-language", required=False, help="The language for the front of the flashcards.")
parser.add_argument("-b", "--back-language", required=False, help="The language for the back of the flashcards.")
# By default, we will make both vocab and sentence cards, but you can disable either with these flags:
parser.add_argument("--no-vocab", action="store_true", help="Don't make vocab cards, only sentence cards.")
parser.add_argument("--no-sentences", action="store_true", help="Don't make sentence cards in addition to vocab cards.")
parser.add_argument("words", nargs="+")
args = parser.parse_args()

do_vocab = not args.no_vocab
do_sentences = not args.no_sentences
if not do_vocab and not do_sentences:
    print("Error: You must make at least one type of card (vocab or sentence).")
    exit(1)

words = " ".join(args.words).strip()
print(f"Words: {words}")

front_language = args.front_language
if not front_language:
    front_language = what_language_on_front(args.words)
back_language = args.back_language
if not back_language:
    back_language = what_language_on_back(front_language)

front_language = front_language.capitalize().strip()
back_language = back_language.capitalize().strip()

check_deck_exists(front_language)

vocab_cards = make_cards(front_language, back_language, words)
pprint(vocab_cards)
if not ask_for_confirmation("Continue?"):
    exit(1)

for card in vocab_cards.cards:
    if do_vocab:
        front_audio = tts_to_anki_media(card.Word, front_language)
        back_audio = tts_to_anki_media(card.Translation, back_language)
        anki_add_vocab_note(front_language, card.Word, card.Pronunciation, card.Translation, front_audio, back_audio)

    if do_sentences:
        front_audio = tts_to_anki_media(card.ExamplePhrase, front_language)
        back_audio = tts_to_anki_media(card.ExamplePhraseTranslation, back_language)
        anki_add_sentence_note(front_language, card.ExamplePhrase, card.ExamplePhraseTranslation, front_audio, back_audio)
