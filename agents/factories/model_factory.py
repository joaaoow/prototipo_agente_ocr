import itertools
import os

from dotenv import load_dotenv

from config.gemini_config import DEFAULT_MODEL
from repositories.custom_gemini import CustomGemini

load_dotenv()

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini").lower()


def _load_api_keys() -> list[str]:
    raw = os.getenv("GOOGLE_API_KEYS") or os.getenv("GOOGLE_API_KEY", "")
    keys = [key.strip() for key in raw.split(",") if key.strip()]

    if not keys:
        raise ValueError(
            "Nenhuma chave configurada. Defina GOOGLE_API_KEY ou GOOGLE_API_KEYS (separadas por vírgula) no .env."
        )

    return keys


_api_keys = _load_api_keys()
_key_cycle = itertools.cycle(_api_keys)


def next_api_key() -> str:
    """Revezamento round-robin entre as chaves do tier gratuito (plano estudante)."""
    return next(_key_cycle)


def create_model():
    """Factory responsável por instanciar o provider/model correto."""
    if MODEL_PROVIDER in {"gemini", "google"}:
        return CustomGemini(
            api_key=next_api_key(),
            model=DEFAULT_MODEL,
        )

    raise ValueError(
        f"MODEL_PROVIDER '{MODEL_PROVIDER}' não suportado neste agente. Use 'gemini'."
    )
