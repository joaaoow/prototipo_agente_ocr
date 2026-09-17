from typing import Any

from google.adk.tools import ToolContext

from services.prescription.extraction_service import (
    extract_prescription as run_extraction,
)


async def extract_prescription(tool_context: ToolContext) -> dict[str, Any]:
    """
    Lê a foto da receita médica que o usuário acabou de enviar e extrai medicamento, dose,
    posologia e período, com score de confiança. Use sempre que o usuário pedir para ler ou
    extrair os dados de uma receita.

    Returns:
        dict com status, os medicamentos extraídos, confiança geral, observações, sinal de
        revisão manual (needs_manual_review, RF05), os campos de baixa confiança e a origem
        da leitura (source: "gemini" ou "tesseract_fallback", quando a Gemini API falhou e o
        OCR offline foi usado).
    """
    artifact_ref = tool_context.state.get("prescription_artifact")

    if not artifact_ref:
        return {
            "status": "error",
            "message": "Nenhuma imagem de receita foi encontrada nesta conversa. Peça para o usuário anexar a foto da receita.",
        }

    try:
        image_part = await tool_context.load_artifact(filename=artifact_ref["filename"])

        if image_part is None or image_part.inline_data is None:
            return {"status": "error", "message": "Não foi possível carregar a imagem da receita."}

        image_bytes = image_part.inline_data.data
        mime_type = artifact_ref.get("mime_type") or image_part.inline_data.mime_type

        result = run_extraction(image_bytes, mime_type=mime_type)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {
        "status": "success",
        "medicamentos": [item.model_dump() for item in result.data.medicamentos],
        "confidence_geral": result.data.confidence_geral,
        "observacoes": result.data.observacoes,
        "needs_manual_review": result.needs_manual_review,
        "low_confidence_fields": result.low_confidence_fields,
        "source": result.source,
    }
