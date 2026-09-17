"""Testa tools/extract_prescription.py — spec: specs/prescription-extraction.md (EC-4).

Usa um fake de ToolContext em vez do real do ADK: só precisamos de `.state` (dict) e
`.load_artifact` (async), que é toda a superfície que a tool usa.
"""

import asyncio

from tools.extract_prescription import extract_prescription


class _FakeToolContext:
    def __init__(self, state=None, artifact=None):
        self.state = state or {}
        self._artifact = artifact

    async def load_artifact(self, filename):
        return self._artifact


def test_tool_returns_error_when_no_image_was_sent_ec4():
    tool_context = _FakeToolContext(state={})

    result = asyncio.run(extract_prescription(tool_context))

    assert result["status"] == "error"
    assert "imagem" in result["message"].lower()


def test_tool_returns_error_when_artifact_cannot_be_loaded():
    tool_context = _FakeToolContext(
        state={"prescription_artifact": {"filename": "prescription_image", "mime_type": "image/jpeg"}},
        artifact=None,
    )

    result = asyncio.run(extract_prescription(tool_context))

    assert result["status"] == "error"
