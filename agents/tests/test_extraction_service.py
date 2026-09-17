"""Testa services/prescription/extraction_service.py — spec: specs/prescription-extraction.md (AC-1, AC-5, AC-6)."""

from unittest.mock import MagicMock, patch

from services.prescription.extraction_service import (
    MedicationItem,
    PrescriptionExtraction,
    extract_prescription,
)


def _fake_gemini_client(parsed_extraction):
    client = MagicMock()
    response = MagicMock()
    response.parsed = parsed_extraction
    client.models.generate_content.return_value = response
    return client


def test_extract_prescription_returns_structured_data_on_success_ac1():
    fake_extraction = PrescriptionExtraction(
        medicamentos=[
            MedicationItem(medicamento="Dipirona", dose="500mg", posologia="1 cp 8/8h", periodo="5 dias", confidence=0.95)
        ],
        confidence_geral=0.95,
    )

    with patch(
        "services.prescription.extraction_service.build_genai_client",
        return_value=_fake_gemini_client(fake_extraction),
    ):
        result = extract_prescription(b"fake-image-bytes", mime_type="image/jpeg")

    assert result.source == "gemini"
    assert result.needs_manual_review is False
    assert len(result.data.medicamentos) == 1
    assert result.data.medicamentos[0].medicamento == "Dipirona"


def test_extract_prescription_falls_back_to_tesseract_when_gemini_fails_ac5():
    with patch(
        "services.prescription.extraction_service.build_genai_client",
        side_effect=RuntimeError("Gemini API indisponível"),
    ), patch(
        "services.prescription.extraction_service.tesseract_extract_text",
        return_value="Dipirona 500mg - 1 cp 8/8h",
    ):
        result = extract_prescription(b"fake-image-bytes")

    assert result.source == "tesseract_fallback"
    assert result.needs_manual_review is True
    assert result.data.medicamentos == []
    assert "Dipirona 500mg" in result.data.observacoes


def test_extract_prescription_fallback_does_not_raise_when_tesseract_also_fails_ac6():
    with patch(
        "services.prescription.extraction_service.build_genai_client",
        side_effect=RuntimeError("Gemini API indisponível"),
    ), patch(
        "services.prescription.extraction_service.tesseract_extract_text",
        side_effect=RuntimeError("tesseract não instalado"),
    ):
        result = extract_prescription(b"fake-image-bytes")

    assert result.source == "tesseract_fallback"
    assert result.needs_manual_review is True
    assert result.data.medicamentos == []
    assert result.data.observacoes is not None


def test_extract_prescription_falls_back_when_gemini_returns_unparseable_response():
    client = MagicMock()
    response = MagicMock()
    response.parsed = None
    client.models.generate_content.return_value = response

    with patch(
        "services.prescription.extraction_service.build_genai_client",
        return_value=client,
    ), patch(
        "services.prescription.extraction_service.tesseract_extract_text",
        return_value="",
    ):
        result = extract_prescription(b"fake-image-bytes")

    assert result.source == "tesseract_fallback"
