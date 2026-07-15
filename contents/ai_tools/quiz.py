#!/usr/bin/env python3

import json
import os
from pathlib import Path
from pydantic import BaseModel

from openai_utils import query_agent, RED, GREEN, RESET

# study profiles in the user's home directory
PROFILE_DIR = Path.home() / ".study_profiles"
PROFILE_DIR.mkdir(exist_ok=True)

conversation_history = []
profile = None
profile_path = None

class FirstQuestion(BaseModel):
    undocumented_topics: list[str]
    first_question: str

class Continuation(BaseModel):
    brief_explanation_for_student: str
    next_question: str

class ProfileUpdate(BaseModel):
    updated_profile: str
    newly_learned_concept_names: list[str]
    identified_unknown_concept_names: list[str]

# ============================================================
# PROFILE HELPERS
# ============================================================

def list_profiles():
    return [p.name for p in PROFILE_DIR.glob("*.json")]


def choose_profile(user_topic):
    files = list_profiles()

    prompt = {
        "role": "user",
        "content": (
            "You are organizing study topics.\n\n"
            f"Existing files:\n{files}\n\n"
            f"Requested topic:\n{user_topic}\n\n"
            "Choose the BEST existing file.\n"
            "If none fit, create a BROAD academic category.\n\n"
            "Respond with ONLY one filename ending in .json (no explanation)."
        )
    }

    response = query_agent([prompt]).strip()
    response = os.path.basename(response)  # Sanitize to prevent path traversal

    # If the agent doesn't respond with a valid filename, fail and exit with error message
    if response in files:
        # Existing file
        return response
    elif response.endswith(".json"):
        # New file
        return response
    else:
        print(f"{RED}Error: Invalid filename from agent: '{response}'{RESET}")
        print("Please ensure the topic is clear and try again.")
        raise SystemExit


def load_or_create_profile(filename):
    path = PROFILE_DIR / filename

    if path.exists():
        with open(path, "r") as f:
            try:
                data = json.load(f)
                fail_read = False
            except json.JSONDecodeError:
                fail_read = True
    else:
        fail_read = True

    if fail_read:
        data = {
            "paragraph": "",
            "known_concepts": [],
            "unknown_concepts": []
        }
        path.touch()

    data.setdefault("paragraph", "")
    data.setdefault("known_concepts", [])
    data.setdefault("unknown_concepts", [])

    return data, path


# Given the previous profile and the conversation history, update the profile with new insights about the student's strengths, weaknesses, and recent mistakes.
def update_profile(conversation_history):
    global profile

    analysis_instructions = (
        "You analyze a student's answer history.\n"
        "Provide an updated profile based on the conversation history. "
        "Integrate the prior information and the new information from the conversation history documenting the student's current understanding of the topic. "
        "Do not include specific questions or answers from the conversation history. Instead, focus on explaining broadly the student's level of understanding. "
        "You should synthesize the information in the previous profile with the above conversation, capturing the current state of the student's knowledge into a single paragraph of 5-15 sentences. "
    )

    analysis_object = {
        "role": "system",
        "content": analysis_instructions.format(profile=profile)
    }

    response = query_agent(
        conversation_history + [analysis_object],
        text_format=ProfileUpdate
    )

    known = set(profile.get("known_concepts", []))
    unknown = set(profile.get("unknown_concepts", []))

    for concept in response.newly_learned_concept_names:
        known.add(concept)
        unknown.discard(concept)

    for concept in response.identified_unknown_concept_names:
        unknown.add(concept)
        known.discard(concept)

    profile = {
        "paragraph": response.updated_profile,
        "known_concepts": sorted(known),
        "unknown_concepts": sorted(unknown)
    }


def save_profile():
    global profile, profile_path

    if profile is None or profile_path is None:
        return

    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2)

    print(f"\nSaved profile to {profile_path}")


# ============================================================
# MAIN
# ============================================================

print("Enter a topic to begin quiz (or 'exit' to quit).")

topic = input(f"{RED}> {RESET}").strip()

filename = choose_profile(topic)
subject = filename.rsplit(".", 1)[0]

profile, profile_path = load_or_create_profile(filename)

print(f"{GREEN}Using study profile:{RESET} {filename}")

quiz_instructions = {
    "role": "system",
    "content": (
        f"You are a friendly pedagogical interlocutor for gifted students. "
        f"The student wants to learn about {topic}. "
        f"Student profile paragraph:\n"
        f"{profile.get('paragraph', '')}\n\n"
        f"Known concepts:\n{profile.get('known_concepts', [])}\n\n"
        f"Unknown concepts:\n{profile.get('unknown_concepts', [])}\n\n"
        "Your goal is to help the student learn the topic through guided questions. "
        #"Try to keep your questions simple and explicit. Avoid open-ended or vague questions. "
        #"Questions should have exactly one correct answer. Never ask multiple questions at once. "
        "Don't dryly ask the same questions about one word or topic over and over. "
        "Instead, use each question as an opportunity to guide the student to discover new insights and connections. "
        "Avoid any concepts documented as known. Focus on topics which are not mentioned whatsoever in the profile as either a strength or weakness. "
        f"Start by identifying topics within {subject} which are not yet documented in the profile."
    )
}

conversation_history.append(quiz_instructions)

response = query_agent(
    conversation_history,
    text_format = FirstQuestion
)

string_response = (
    f"Not yet documented topics:\n{response.undocumented_topics}\n\n"
    f"First question:\n{response.first_question}"
)

print(f"{GREEN}{string_response}{RESET}\n")
conversation_history.append({
    "role": "assistant",
    "content": string_response
})

while True:

    user_input = input(f"{RED}> {RESET}").strip()

    if user_input.lower() in ["exit", "quit"]:
        if len(conversation_history) >= 2:
            update_profile(conversation_history)
        # Remove the last newline-separated section of the last entry in the conversation history
        # to avoid including the next question which the student didn't answer.
        # It will have a few lines of text separated by \n\n, only delete the last one.
        conversation_history[-1]["content"] = conversation_history[-1]["content"].rsplit("\n\n", 1)[0]
        save_profile()
        print("Goodbye!")
        raise SystemExit

    conversation_history.append({
        "role": "user",
        "content": user_input
    })

    response = query_agent(
        conversation_history,
        text_format = Continuation
    )

    string_response = (
        f"{response.brief_explanation_for_student}\n\n"
        f"{response.next_question}"
    )

    print(f"{GREEN}{string_response}{RESET}\n")
    conversation_history.append({
        "role": "assistant",
        "content": string_response
    })
