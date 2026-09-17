import os

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GENERATION_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))
