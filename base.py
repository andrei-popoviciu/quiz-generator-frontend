import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ["API_URL"]
COOKIE_NAME = "session"
QUIZ_GEN_INSTRUCTIONS = (
    "Enter your prompt for the generation of the quiz. "
    "It may include the type and number of questions, subject and "
    "anything else you want to find in the generated quiz."
)
