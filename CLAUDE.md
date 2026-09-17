# SAFEpass — Squad 44, Desafio 04 — Agente OCR de Receitas

Protótipo da frente de IA do módulo de histórico médico digital do SAFEpass
(Residência Tecnológica UCB / Porto Digital). Lê a foto de uma receita médica com a
Gemini API (multimodal) e devolve os dados já estruturados — medicamento, dose,
posologia, período — com fallback de revisão manual (HITL) quando a leitura não estiver
confiável. Cobre RF03 (OCR), RF04 (card estruturado) e RF05 (revisão manual).

## Estado atual do repositório

**Só a pasta `agents/` tem conteúdo real.** As pastas `agents/api`, `agents/datasets`,
`agents/db`, `agents/utils` são placeholders vazios de outras frentes do squad (API
HTTP, dados, banco). **Não crie nem edite arquivos fora de `agents/` sem o usuário pedir
explicitamente** — outras pessoas do squad trabalham nessas frentes em paralelo.

Para a arquitetura completa do agente (fluxo, decisões de design, HITL, fallback
offline), veja **[`agents/README.md`](agents/README.md)**. Para um mapa navegável do
código com diagramas, veja **[`docs/CODEBASE_MAP.md`](docs/CODEBASE_MAP.md)**.

## Stack

- **IA**: Google ADK (Agent Development Kit) + Gemini API (`google-genai`), com
  fallback offline via Tesseract quando a Gemini API falha.
- **Linguagem**: Python.
- Frontend (React+TS), backend HTTP (FastAPI) e banco (PostgreSQL) fazem parte do plano
  geral do squad, mas **não existem neste repositório ainda** — são de outras frentes.

## Resumo da arquitetura do agente

Um único agente ADK (`root_agent`, em `agents/apps/receita_ocr_app/agent.py`) decide
quando chamar a ferramenta `extract_prescription`. A extração em si **não é um segundo
agente** — é uma função determinística que chama o Gemini direto
(`agents/services/prescription/extraction_service.py`), com `response_schema` Pydantic
pra sair já estruturado. Se a Gemini API falhar, cai automaticamente num fallback
offline via Tesseract (texto bruto, revisão manual sempre obrigatória nesse caminho).

A confiança da leitura nunca é mostrada ao usuário como número — só como conclusão em
linguagem natural, e serve de gatilho pro HITL (RF05): sempre que a confiança estiver
baixa, houver suspeita de prompt injection na receita, ou o fallback offline tiver sido
usado, o agente força `needs_manual_review=True`.

## Como rodar (dentro de `agents/`)

```bash
pip install -r requirements.txt
# preencher .env com GOOGLE_API_KEY (ou GOOGLE_API_KEYS=chave1,chave2,chave3)
adk web apps   # não `adk web` sozinho — ver gotcha no CODEBASE_MAP.md
```

## Workflow: SDD + TDD (obrigatório para código novo em `agents/`)

Este projeto vai crescer do protótipo até produção, então seguimos spec-first desde já:

1. **Nenhuma feature nova sem spec aprovada primeiro** em `agents/specs/` (usar
   `agents/specs/_TEMPLATE.md`: requisitos FR-N, critérios de aceite Given/When/Then
   AC-N referenciando o FR, casos de borda EC-N). Não escrever spec depois do código —
   isso vira documentação, não spec.
2. **Testes vêm da spec, antes da implementação**: cada AC-N/EC-N vira teste em
   `agents/tests/`, que deve falhar antes do código existir (red), depois passar
   (green).
3. **Rodar `pytest` (de dentro de `agents/`) antes de qualquer coisa subir** — não sobe
   nada sem os testes passando.
4. Se durante a implementação aparecer necessidade fora da spec, **parar e atualizar a
   spec primeiro**, não improvisar.

Ver `agents/README.md` → "SDD + TDD" para os comandos e `agents/specs/prescription-extraction.md`
como exemplo de spec (retroativa — a próxima deve vir antes do código).

## Convenções específicas deste projeto

- Imports entre pacotes de `agents/` são sem prefixo (`from factories.model_factory import ...`),
  porque `agents/` é o cwd quando o `adk web`/scripts rodam.
- Um arquivo = um papel (prompt, guard, callback, tool, service, factory, repository) —
  evite juntar responsabilidades num arquivo só.
- Imagem de receita sempre passa por Artifact do ADK (`save_artifact`/`load_artifact`),
  nunca como bytes crus em `session.state`.
- Número de confiança (`confidence`/`confidence_geral`) é interno — nunca deve aparecer
  na resposta ao usuário.
