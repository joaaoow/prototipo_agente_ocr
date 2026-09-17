import re

from config.confidence_config import CONFIDENCE_THRESHOLD

_SUSPICIOUS_PATTERNS = [
    re.compile(r"ignor[ae]\s+(as\s+)?instru", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now", re.IGNORECASE),
    re.compile(r"a\s+partir\s+de\s+agora\s+voc[eê]\s+[ée]", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?above", re.IGNORECASE),
]


def contains_prompt_injection(text: str) -> bool:
    """Detecta texto que parece instrução embutida (ex.: adversária, escrita na própria receita)."""
    if not text:
        return False

    return any(pattern.search(text) for pattern in _SUSPICIOUS_PATTERNS)


def apply_hitl_guard(extraction):
    """
    Aplica a política de HITL como segurança sobre o resultado bruto do modelo:
    não confia no self-report de confiança — zera a confiança de item suspeito e
    força needs_manual_review sempre que houver suspeita ou confiança abaixo do limiar.

    Retorna (needs_manual_review: bool, low_confidence_fields: list[str]).
    """
    low_confidence_fields: list[str] = []
    forced_review = False

    for index, item in enumerate(extraction.medicamentos):
        campos = " ".join(
            filter(None, [item.medicamento, item.dose, item.posologia, item.periodo])
        )

        if contains_prompt_injection(campos):
            item.confidence = 0.0
            forced_review = True

        label = item.medicamento or f"item_{index}"

        if item.confidence < CONFIDENCE_THRESHOLD:
            low_confidence_fields.append(label)

    needs_manual_review = (
        forced_review
        or extraction.confidence_geral < CONFIDENCE_THRESHOLD
        or bool(low_confidence_fields)
        or not extraction.medicamentos
    )

    return needs_manual_review, low_confidence_fields
