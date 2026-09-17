# Agente OCR de Receitas — SAFEpass (Squad 44, Desafio 04)

Agente de IA que lê a foto de uma receita médica e devolve os dados já estruturados —
medicamento, dose, posologia e período — usando a Gemini API (multimodal), com fallback
de revisão manual (HITL) quando a leitura não estiver confiável. Cobre os requisitos
funcionais RF03 (OCR), RF04 (dados em card estruturado) e RF05 (revisão manual) do
módulo de histórico médico digital.

Esta pasta cobre **só a frente de IA**. API HTTP, banco de dados e frontend são
responsabilidade de outras frentes do squad.

## Por que Gemini multimodal em vez de OCR tradicional

OCR tradicional (Tesseract + regras) erra muito em receita médica (letra manuscrita,
fotos tortas/borradas). A Gemini API lê a imagem e já devolve o JSON estruturado num
único passo — sem um motor de OCR separado. Quando a confiança da leitura vem baixa, o
agente sinaliza isso explicitamente em vez de arriscar um dado errado, para o front
abrir a tela de preenchimento/correção manual (RF05).

## Arquitetura

Um único agente ADK (`root_agent`, orquestrador conversacional) com uma ferramenta que
chama o Gemini diretamente. A extração **não é um segundo agente** — é só uma função
determinística (imagem entra, JSON sai), o que evita complexidade desnecessária e um bug
conhecido do ADK com `AgentTool` e conteúdo multimodal (ver `Decisões de design`).

```
Usuário (adk web) — anexa foto da receita na mensagem
        │
        ▼
before_agent_callback: capture_prescription_image_callback
  → acha a imagem na mensagem, salva como Artifact, guarda a
    referência (filename) no state da sessão
        │
        ▼
root_agent (orquestrador, LlmAgent + Gemini)
  → decide chamar a tool quando há foto de receita
        │
        ▼
tool: extract_prescription
  → carrega a imagem do Artifact
  → chama extraction_service.extract_prescription(...)
        │
        ▼
extraction_service (função pura, SEM agente ADK)
  → client.models.generate_content(imagem + prompt, response_schema=PrescriptionExtraction)
  → se a Gemini API falhar (sem rede/cota/erro): fallback offline via Tesseract
    (texto bruto, sem estruturação automática, needs_manual_review sempre true)
  → aplica security.review_guard (HITL como segurança) no caminho Gemini
  → devolve ExtractionResult (dados + needs_manual_review + low_confidence_fields + source)
        │
        ▼
after_tool_callback: review_guard_after_tool_callback
  → grava needs_manual_review/low_confidence_fields no state da sessão
        │
        ▼
root_agent responde ao usuário (nunca expõe o número de confidence,
só a conclusão em linguagem natural)
```

### Estrutura de pastas

| Pasta | Responsabilidade |
|---|---|
| `apps/receita_ocr_app/` | `agent.py` (o `root_agent`, único agente ADK) e `runner.py` (helper de teste fora do `adk web`) |
| `tools/` | `extract_prescription.py` — a ferramenta ADK chamada pelo orquestrador |
| `services/prescription/` | `extraction_service.py` — chamada direta ao Gemini + schemas Pydantic (`MedicationItem`, `PrescriptionExtraction`, `ExtractionResult`) |
| `prompts/` | `orchestrator_prompt.py` (como o agente conversa com o usuário) e `extract_prescription_prompt.py` (instrução da chamada de extração — não fala com o usuário) |
| `security/` | `review_guard.py` — HITL como segurança: detecta prompt injection e força revisão manual, sem confiar no self-report de confiança do modelo |
| `callbacks/` | `review_guard_callback.py` — captura a imagem anexada (via Artifact) e propaga o sinal de revisão manual pro state da sessão |
| `factories/` | `model_factory.py` — cria o model do agente e faz o revezamento de chaves (`GOOGLE_API_KEYS`) |
| `repositories/` | `custom_gemini.py` — client do `google-genai`, reaproveitado pelo agente ADK e pela extração direta; `tesseract_ocr.py` — OCR bruto offline, usado só como fallback |
| `config/` | `gemini_config.py` (modelo/temperatura) e `confidence_config.py` (limiar de confiança) |

## HITL (human-in-the-loop) — dupla camada

1. **No prompt** (`extract_prescription_prompt.py`): instrui o modelo a preferir declarar
   confiança baixa a "chutar" um campo ilegível, e a nunca inventar dado que não esteja
   claramente legível.
2. **Como segurança** (`security/review_guard.py`): não confia cegamente no que o modelo
   reporta. Se detectar um padrão de prompt injection no texto extraído, zera a confiança
   daquele item e força `needs_manual_review=True` no resultado inteiro, mesmo que o
   modelo tenha reportado alta confiança.

O número de confiança nunca é mostrado ao usuário — o `root_agent` só comunica a
conclusão em linguagem natural ("ficou claro" / "precisa confirmar antes de salvar").

## Fallback offline (Tesseract)

Se a chamada à Gemini API falhar por qualquer motivo (sem rede, cota estourada em todas
as chaves do revezamento, erro da API), `extraction_service` cai automaticamente para
OCR local via Tesseract (`repositories/tesseract_ocr.py`). Nesse caminho:

- Não há estruturação automática dos campos — regex/heurística sobre texto de receita
  médica é arriscado demais sem um LLM validando, então o texto bruto vai direto pro
  campo `observacoes` para o usuário conferir e preencher manualmente.
- `needs_manual_review` vem sempre `true` e `source` vem `"tesseract_fallback"`, para o
  orquestrador explicar a situação ao usuário (sem revelar detalhe técnico do erro).
- Requer o **binário do Tesseract instalado no sistema** (o pacote `pytesseract` é só um
  wrapper em Python, não inclui o motor de OCR). No Windows, instale via
  [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) com o pacote de
  idioma português, e aponte `TESSERACT_CMD` no `.env` se o binário não estiver no PATH
  (ex.: `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`).

## Decisões de design

- **Sem `AgentTool` nem sub-agente aninhado para a extração**: seria overkill para uma
  chamada determinística de passo único, e `AgentTool` tem um bug documentado que
  descarta conteúdo multimodal do evento de retorno ([google/adk-python#2914](https://github.com/google/adk-python/discussions/2914),
  [#729](https://github.com/google/adk-python/issues/729)).
- **Imagem via Artifact, não bytes crus no `state`**: é o padrão recomendado pelos
  mantenedores do ADK para mover binário entre um callback e uma tool.
- **Rotação de chaves**: `factories/model_factory.py` faz round-robin entre as chaves do
  `.env` (tier gratuito do plano estudante), usado tanto pelo `root_agent` quanto pela
  chamada direta de extração.

## Como rodar

1. Instalar dependências:
   ```
   pip install -r requirements.txt
   ```
2. Criar um `.env` nesta pasta (`agents/`) com uma das duas opções:
   ```
   GOOGLE_API_KEY=sua-chave
   # ou, para revezar entre várias chaves do plano estudante:
   GOOGLE_API_KEYS=chave1,chave2,chave3
   ```
3. Rodar o `adk web` **apontando para `apps`** (não para `agents/` direto — o ADK trata
   cada subpasta do diretório passado como um app, então `agents/` sozinho lista as
   pastas erradas):
   ```
   adk web apps
   ```
4. Abrir a URL impressa no terminal, selecionar `receita_ocr_app`, anexar a foto de uma
   receita na mensagem e pedir para extrair os dados.

## SDD + TDD — como trabalhamos daqui pra frente

Este projeto segue **spec-first**: nenhuma feature nova entra sem uma spec aprovada em
`specs/`, e nenhum código sobe sem teste cobrindo os critérios de aceite dela.

1. **Escrever a spec antes do código**, usando `specs/_TEMPLATE.md` como base. Preencher
   requisitos funcionais (FR-N), critérios de aceite em Given/When/Then (AC-N,
   referenciando o FR) e casos de borda (EC-N). Ver `specs/prescription-extraction.md`
   como exemplo (nota: essa spec foi escrita retroativamente, documentando o que já
   existia — as próximas devem vir *antes* do código).
2. **Escrever os testes a partir dos critérios de aceite** — cada AC-N e EC-N vira pelo
   menos um teste em `tests/`, e eles devem falhar antes de implementar (red).
3. **Implementar até os testes passarem** (green), sem adicionar nada que não esteja na
   spec.
4. **Rodar a suíte inteira antes de subir qualquer mudança**:
   ```
   pip install -r requirements-dev.txt
   pytest
   ```

Os testes existentes (`tests/test_review_guard.py`, `tests/test_extraction_service.py`,
`tests/test_model_factory.py`, `tests/test_extract_prescription_tool.py`) usam mocks pra
não depender de chave de API real nem do binário do Tesseract — rodam offline e rápido.
Testes de integração de verdade contra a Gemini API (com chave real, via `adk web`) são
complementares, não substituem essa suíte.

## Fora de escopo (outras frentes)

API FastAPI, banco de dados PostgreSQL, frontend React, fine-tuning e caminho de
produção com Claude API — mencionados no plano do squad, mas não fazem parte desta
pasta.
