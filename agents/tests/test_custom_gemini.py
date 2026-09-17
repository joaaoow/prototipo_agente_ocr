"""Testa repositories/custom_gemini.py — spec: specs/prescription-extraction.md (AC-9).

Regressão de um bug real: sem retry_options no nível do Client, o modelo do próprio
root_agent (orquestrador) não tentava de novo em 503 transitório e derrubava a
conversa inteira com um erro não tratado — mesmo quando a extração em si tinha
funcionado ou caído no fallback Tesseract graciosamente.
"""

from repositories.custom_gemini import CustomGemini, build_genai_client


def test_build_genai_client_has_retry_configured_ac9():
    client = build_genai_client(api_key="dummy-key")

    retry_options = client._api_client._http_options.retry_options

    assert retry_options is not None
    assert retry_options.attempts > 1


def test_custom_gemini_api_client_has_retry_configured_ac9():
    """O modelo usado pelo root_agent (orquestrador) precisa do mesmo retry — não só a extração."""
    gemini = CustomGemini(api_key="dummy-key", model="gemini-flash-latest")

    retry_options = gemini.api_client._api_client._http_options.retry_options

    assert retry_options is not None
    assert retry_options.attempts > 1
