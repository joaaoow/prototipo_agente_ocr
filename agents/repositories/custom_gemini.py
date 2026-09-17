import os
from functools import cached_property
from typing import Optional

from google.adk.models import Gemini
from google.genai import Client, types

from config.gemini_config import (
    GEMINI_RETRY_ATTEMPTS,
    GEMINI_RETRY_INITIAL_DELAY,
    GEMINI_RETRY_MAX_DELAY,
)


def build_genai_client(api_key: Optional[str] = None) -> Client:
    """
    Instancia o client do google-genai, usado tanto pelo agente ADK (root_agent)
    quanto pela extração direta.

    Sem `http_options.retry_options`, o client não tenta de novo em erro nenhum —
    nem em 503 "alta demanda", que é quase sempre transitório. Isso vale tanto para
    as próprias respostas do orquestrador (root_agent) quanto para a extração: sem
    esse default aqui, só a extração tinha retry (configurado por chamada), e o
    orquestrador quebrava a conversa inteira no primeiro 503.
    """
    return Client(
        api_key=api_key or os.getenv("GOOGLE_API_KEY"),
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=GEMINI_RETRY_ATTEMPTS,
                initial_delay=GEMINI_RETRY_INITIAL_DELAY,
                max_delay=GEMINI_RETRY_MAX_DELAY,
            )
        ),
    )


class CustomGemini(Gemini):
    api_key: Optional[str] = None

    @cached_property
    def api_client(self):
        return build_genai_client(self.api_key)
