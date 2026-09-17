import os

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GENERATION_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))
