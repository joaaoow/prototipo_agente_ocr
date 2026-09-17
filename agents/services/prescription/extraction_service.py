from typing import Optional

from google.genai import types
from pydantic import BaseModel, Field

from config.gemini_config import DEFAULT_MODEL, GENERATION_TEMPERATURE
from factories.model_factory import next_api_key
from prompts.extract_prescription_prompt import EXTRACT_PRESCRIPTION_PROMPT
from repositories.custom_gemini import build_genai_client
from repositories.tesseract_ocr import extract_text as tesseract_extract_text
from security.review_guard import apply_hitl_guard


class MedicationItem(BaseModel):
    medicamento: str
    dose: str
    posologia: str
    periodo: str
    confidence: float = Field(ge=0.0, le=1.0)


class PrescriptionExtraction(BaseModel):
    medicamentos: list[MedicationItem]
    confidence_geral: float = Field(ge=0.0, le=1.0)
    observacoes: Optional[str] = None


class ExtractionResult(BaseModel):
    data: PrescriptionExtraction
    needs_manual_review: bool
    low_confidence_fields: list[str]
    source: str = "gemini"


def extract_prescription(image_bytes: bytes, mime_type: str = "image/jpeg") -> ExtractionResult:
    """
    Envia a foto da receita pro Gemini e devolve os dados estruturados com score de confiança.
    Chamada direta ao modelo multimodal (sem agente ADK por trás) — só extração, nada mais.

    Se a chamada à Gemini API falhar por qualquer motivo (sem rede, cota estourada em
    todas as chaves, erro da API), cai no fallback offline via Tesseract: devolve o texto
    bruto lido da imagem para revisão manual, sem tentar estruturar automaticamente.
    """
    try:
        return _extract_with_gemini(image_bytes, mime_type)
    except Exception:
        return _extract_with_tesseract_fallback(image_bytes)


def _extract_with_gemini(image_bytes: bytes, mime_type: str) -> ExtractionResult:
    client = build_genai_client(api_key=next_api_key())

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            EXTRACT_PRESCRIPTION_PROMPT,
        ],
        config=types.GenerateContentConfig(
            temperature=GENERATION_TEMPERATURE,
            response_mime_type="application/json",
            response_schema=PrescriptionExtraction,
        ),
    )

    extraction: Optional[PrescriptionExtraction] = response.parsed

    if extraction is None:
        raise ValueError("Gemini não retornou um JSON estruturado válido para a receita.")

    needs_manual_review, low_confidence_fields = apply_hitl_guard(extraction)

    return ExtractionResult(
        data=extraction,
        needs_manual_review=needs_manual_review,
        low_confidence_fields=low_confidence_fields,
        source="gemini",
    )


def _extract_with_tesseract_fallback(image_bytes: bytes) -> ExtractionResult:
    try:
        raw_text = tesseract_extract_text(image_bytes)
    except Exception:
        raw_text = ""

    observacoes = (
        f"Leitura automática indisponível no momento. Texto bruto capturado via OCR offline "
        f"(Tesseract) para revisão manual:\n\n{raw_text}"
        if raw_text
        else "Leitura automática indisponível e o OCR offline não conseguiu extrair texto desta imagem."
    )

    # Sem estruturação automática nesse caminho: confiar em regex/heurística pra separar
    # medicamento/dose/posologia/período do texto bruto do Tesseract arriscaria dado errado
    # sem um LLM pra validar — melhor devolver vazio e revisão manual obrigatória (RF05).
    extraction = PrescriptionExtraction(medicamentos=[], confidence_geral=0.0, observacoes=observacoes)

    return ExtractionResult(
        data=extraction,
        needs_manual_review=True,
        low_confidence_fields=[],
        source="tesseract_fallback",
    )
