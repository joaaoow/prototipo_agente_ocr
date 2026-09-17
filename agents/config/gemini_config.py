import os

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GENERATION_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))

# Sem isso, o SDK do google-genai NÃO tenta de novo em erro nenhum (nem 503 de alta
# demanda, que é quase sempre transitório) — cai fora na primeira falha.
GEMINI_RETRY_ATTEMPTS = int(os.getenv("GEMINI_RETRY_ATTEMPTS", "3"))
GEMINI_RETRY_INITIAL_DELAY = float(os.getenv("GEMINI_RETRY_INITIAL_DELAY", "1"))
GEMINI_RETRY_MAX_DELAY = float(os.getenv("GEMINI_RETRY_MAX_DELAY", "8"))
