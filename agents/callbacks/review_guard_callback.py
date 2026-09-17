from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool, ToolContext

PRESCRIPTION_ARTIFACT_FILENAME = "prescription_image"


async def capture_prescription_image_callback(callback_context: CallbackContext) -> None:
    """
    Roda antes do agente processar o turno. Se o usuário anexou uma imagem na mensagem,
    salva como Artifact e grava só a referência no state (nunca os bytes crus).
    """
    user_content = callback_context.user_content

    if not user_content or not user_content.parts:
        return

    for part in user_content.parts:
        if part.inline_data and part.inline_data.mime_type and part.inline_data.mime_type.startswith("image/"):
            await callback_context.save_artifact(
                filename=PRESCRIPTION_ARTIFACT_FILENAME,
                artifact=part,
            )
            callback_context.state["prescription_artifact"] = {
                "filename": PRESCRIPTION_ARTIFACT_FILENAME,
                "mime_type": part.inline_data.mime_type,
            }
            return


def review_guard_after_tool_callback(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict,
) -> Optional[dict]:
    """
    Roda depois da tool extract_prescription. Registra no state da sessão se a receita
    precisa de revisão manual (RF05), pra ficar disponível além do texto da resposta.
    """
    if tool.name != "extract_prescription":
        return None

    tool_context.state["needs_manual_review"] = tool_response.get("needs_manual_review", True)
    tool_context.state["low_confidence_fields"] = tool_response.get("low_confidence_fields", [])

    return None
