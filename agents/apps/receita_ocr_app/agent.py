from google.adk.agents import Agent

from callbacks.review_guard_callback import (
    capture_prescription_image_callback,
    review_guard_after_tool_callback,
)
from factories.model_factory import create_model
from prompts.orchestrator_prompt import ORCHESTRATOR_PROMPT
from tools.extract_prescription import extract_prescription

root_agent = Agent(
    model=create_model(),
    name="receita_ocr_agent",
    description=(
        "Agente que lê fotos de receitas médicas e extrai medicamento, dose, posologia e "
        "período via Gemini multimodal, com fallback de revisão manual (HITL) quando a "
        "confiança da leitura for baixa."
    ),
    instruction=ORCHESTRATOR_PROMPT,
    tools=[extract_prescription],
    before_agent_callback=capture_prescription_image_callback,
    after_tool_callback=review_guard_after_tool_callback,
)
