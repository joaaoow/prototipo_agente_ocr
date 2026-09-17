import uuid
from typing import Optional

from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from apps.receita_ocr_app.agent import root_agent

APP_NAME = "receita_ocr_app"

_session_service = InMemorySessionService()
_artifact_service = InMemoryArtifactService()
_runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=_session_service,
    artifact_service=_artifact_service,
)


async def run_prescription_extraction(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    user_id: str = "anonymous",
    session_id: Optional[str] = None,
) -> dict:
    """
    Helper pra testar o agente fora do `adk web` (scripts/testes futuros). Monta a mensagem
    do usuário do mesmo jeito que o adk web geraria ao anexar um arquivo na conversa.
    """
    session_id = session_id or str(uuid.uuid4())
    await _session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)

    message = types.Content(
        role="user",
        parts=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part(text="Extraia os dados desta receita médica."),
        ],
    )

    final_response = None

    async for event in _runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    session = await _session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)

    return {
        "response": final_response,
        "needs_manual_review": session.state.get("needs_manual_review", True),
        "low_confidence_fields": session.state.get("low_confidence_fields", []),
    }
