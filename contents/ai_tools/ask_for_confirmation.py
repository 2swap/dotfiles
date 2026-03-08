from openai_utils import RED, RESET

def ask_for_confirmation(query):
    while True:
        accepted = input(f"{RED}{query} {RESET}[y/n]: ").strip().lower()
        if accepted in ['y', 'yes']:
            return True
        elif accepted in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'.")
