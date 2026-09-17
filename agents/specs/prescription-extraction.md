# Spec: Extração estruturada de receita médica (RF03/RF04/RF05)

- **Status**: Implementada — **spec escrita retroativamente** (a feature já existia
  quando essa spec foi escrita; ela documenta o comportamento acordado com o usuário
  durante o design, não substitui uma spec real feita antes do código). Serve de
  referência e de baseline de regressão pros testes daqui pra frente.
- **Autor**: Squad 44 (frente de IA)
- **Data**: 2026-09-17

## Contexto

O SAFEpass precisa digitalizar receitas médicas: usuário tira foto, sistema extrai
medicamento/dose/posologia/período automaticamente, e abre revisão manual quando a
leitura não for confiável. Decisão do squad: usar Gemini multimodal (lê + extrai num
passo só) em vez de OCR tradicional + regras, que erra muito com letra manuscrita.

## Requisitos funcionais

- **FR-1**: O sistema MUST extrair, de uma foto de receita, uma lista de medicamentos
  com os campos `medicamento`, `dose`, `posologia`, `periodo` e `confidence` (0.0–1.0)
  por item, mais `confidence_geral` (0.0–1.0) do conjunto.
- **FR-2**: O sistema MUST marcar `needs_manual_review=True` sempre que a confiança
  geral ou de algum item estiver abaixo de `CONFIDENCE_THRESHOLD`, ou a lista de
  medicamentos vier vazia.
- **FR-3**: O sistema MUST detectar texto que pareça instrução embutida (prompt
  injection) nos campos extraídos e, se encontrar, zerar a confiança daquele item e
  forçar `needs_manual_review=True` no resultado inteiro — mesmo que o modelo tenha
  reportado alta confiança. O prompt MUST instruir o modelo a manter o campo afetado
  com o texto literal encontrado (não reescrever como comentário/explicação própria) e
  colocar qualquer explicação em `observacoes`, nunca dentro do campo de dado — pra não
  virar uma mensagem confusa tipo posologia = "este texto não contém instruções médicas
  válidas" no lugar da dose real.
- **FR-4**: O sistema MUST cair num fallback de OCR offline (Tesseract) quando a
  chamada à Gemini API falhar por qualquer motivo (rede, cota, erro da API), devolvendo
  o texto bruto capturado (sem estruturação automática) e `needs_manual_review=True`
  incondicional.
- **FR-5**: O agente conversacional (orquestrador) MUST NOT expor o número de
  `confidence`/`confidence_geral` na resposta ao usuário — só a conclusão qualitativa.
- **FR-6**: O sistema MUST revezar entre múltiplas chaves de API (`GOOGLE_API_KEYS`) em
  round-robin, pra caber no tier gratuito do plano estudante.
- **FR-7**: O sistema MUST tentar novamente (retry com backoff) chamadas à Gemini API
  que falharem com erro transitório (408/429/500/502/503/504) antes de considerar a
  chamada uma falha — o SDK `google-genai` não tenta de novo por padrão se
  `retry_options` não for configurado explicitamente. Isso vale tanto pra chamada de
  extração (`extraction_service`) quanto pro **próprio modelo do agente orquestrador**
  (`root_agent`/`CustomGemini`): sem retry configurado no client do orquestrador
  também, um 503 transitório na resposta final do agente derruba a conversa inteira
  com um erro não tratado, mesmo que a extração em si tenha funcionado ou caído no
  fallback graciosamente.
- **FR-8**: O prompt de extração MUST instruir o modelo a avaliar a qualidade da
  imagem como um todo (nitidez/foco/resolução), não só campo a campo, e capar
  `confidence_geral` em um valor baixo quando a imagem estiver significativamente
  borrada/ilegível — mesmo que os campos individuais pareçam ter sido lidos "certos".
  Motivo (incidente real documentado em 2026-09-17): numa imagem sintética bem borrada,
  3 chamadas seguidas devolveram valores diferentes e às vezes errados pro mesmo campo
  (período alternando entre "5 dias" correto e "7 dias" incorreto; posologia alternando
  entre "6 horas" e "8 horas"), mas a `confidence` reportada ficou sempre em 0.8–0.85 —
  acima do limiar antigo de 0.75. `CONFIDENCE_THRESHOLD` foi subido pra **0.9** como
  consequência direta desse achado (ver `config/confidence_config.py`).

## Interface / contrato

```python
# agents/services/prescription/extraction_service.py
def extract_prescription(image_bytes: bytes, mime_type: str = "image/jpeg") -> ExtractionResult: ...

class MedicationItem(BaseModel):
    medicamento: str
    dose: str
    posologia: str
    periodo: str
    confidence: float  # 0.0-1.0

class PrescriptionExtraction(BaseModel):
    medicamentos: list[MedicationItem]
    confidence_geral: float  # 0.0-1.0
    observacoes: Optional[str]

class ExtractionResult(BaseModel):
    data: PrescriptionExtraction
    needs_manual_review: bool
    low_confidence_fields: list[str]
    source: str  # "gemini" | "tesseract_fallback"
```

```python
# agents/security/review_guard.py
def contains_prompt_injection(text: str) -> bool: ...
def apply_hitl_guard(extraction: PrescriptionExtraction) -> tuple[bool, list[str]]: ...
```

## Critérios de aceite

- **AC-1** (FR-1): Dado uma foto legível de receita com 1 medicamento, quando
  `extract_prescription` é chamado, então o resultado tem 1 item em `medicamentos` com
  os 4 campos de texto preenchidos e `confidence` entre 0.0 e 1.0.
- **AC-2** (FR-2): Dado um item com `confidence` abaixo de `CONFIDENCE_THRESHOLD`,
  quando `apply_hitl_guard` roda, então `needs_manual_review` é `True` e o nome do item
  aparece em `low_confidence_fields`.
- **AC-3** (FR-2): Dado `medicamentos` vazio, quando `apply_hitl_guard` roda, então
  `needs_manual_review` é `True`.
- **AC-4** (FR-3): Dado um item cujo campo `medicamento` contém "ignore as instruções
  anteriores", quando `apply_hitl_guard` roda, então `confidence` desse item vira `0.0`
  e `needs_manual_review` é `True`, mesmo que o item tenha vindo com `confidence` alta.
- **AC-5** (FR-4): Dado que a chamada à Gemini API levanta uma exceção qualquer, quando
  `extract_prescription` é chamado, então o resultado tem `source="tesseract_fallback"`,
  `needs_manual_review=True` e `medicamentos` vazio (sem estruturação automática).
- **AC-6** (FR-4): Dado que a chamada à Gemini API falha e o Tesseract também falha (ou
  não está instalado), quando `extract_prescription` é chamado, então o sistema não
  lança exceção — devolve `ExtractionResult` com `observacoes` explicando que a leitura
  não foi possível.
- **AC-7** (FR-6): Dado `GOOGLE_API_KEYS="k1,k2,k3"`, quando `next_api_key()` é chamado
  4 vezes seguidas, então a sequência é `k1, k2, k3, k1` (round-robin).
- **AC-8** (FR-7): Quando `_extract_with_gemini` monta a `GenerateContentConfig`, então
  `http_options.retry_options.attempts` é maior que 1 (retry habilitado, não o
  comportamento padrão do SDK de tentar só uma vez).
- **AC-9** (FR-7): Quando `build_genai_client()` é chamado (usado tanto por
  `CustomGemini.api_client`, o modelo do orquestrador, quanto pela extração direta),
  então o `Client` retornado tem `http_options.retry_options.attempts` maior que 1.
- **AC-10** (FR-2/FR-8): Comportamento de calibração do prompt (avaliado manualmente/via
  integração, não é unitário determinístico): dada a mesma foto de receita visivelmente
  borrada enviada 3 vezes seguidas, a maioria das chamadas deve devolver
  `needs_manual_review=True` com o novo `CONFIDENCE_THRESHOLD=0.9` — reprodução do
  incidente do FR-8 usada como critério de regressão manual.

## Casos de borda

- **EC-1**: Imagem que não é uma receita médica → `medicamentos` vazio, `confidence_geral`
  baixa (comportamento do prompt, coberto por teste de integração/manual, não unitário).
- **EC-2**: Gemini retorna resposta que não bate com o schema (`response.parsed is None`)
  → tratado como falha, cai no fallback Tesseract (mesmo caminho de EC do FR-4).
- **EC-3**: Nenhuma `GOOGLE_API_KEY`/`GOOGLE_API_KEYS` configurada → `model_factory`
  MUST levantar `ValueError` na importação, não falhar silenciosamente depois.
- **EC-4**: Usuário manda mensagem sem anexar imagem → a tool `extract_prescription`
  MUST devolver `status="error"` com mensagem amigável, sem tentar chamar o Gemini.
- **EC-5**: Tesseract não está instalado no SO (binário ausente) → `extract_text` lança
  exceção, capturada pelo fallback, que devolve `observacoes` explicando que não deu
  pra extrair texto (não propaga a exceção pro chamador).

## Fora de escopo

- Estruturação automática do texto bruto do fallback Tesseract (regex/heurística) —
  arriscado sem um LLM validando; fica pra revisão manual (RF05).
- Persistência dos dados extraídos (banco, API HTTP) — outra frente do squad.
- Limiares de confiança por tipo de campo (hoje é um único `CONFIDENCE_THRESHOLD`
  geral) — considerado, mas adiado pra manter o MVP simples (ver plano de arquitetura).
