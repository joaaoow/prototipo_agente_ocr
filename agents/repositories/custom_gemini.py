import os
from functools import cached_property
from typing import Optional

from google.adk.models import Gemini
from google.genai import Client


def build_genai_client(api_key: Optional[str] = None) -> Client:
    """Instancia o client do google-genai, usado tanto pelo agente ADK quanto pela extração direta."""
    return Client(api_key=api_key or os.getenv("GOOGLE_API_KEY"))


class CustomGemini(Gemini):
    api_key: Optional[str] = None

    @cached_property
    def api_client(self):
        return build_genai_client(self.api_key)
