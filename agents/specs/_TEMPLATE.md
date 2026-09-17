# Spec: <nome da feature>

- **Status**: Draft | Em revisão | Aprovada | Implementada
- **Autor**: <nome>
- **Data**: <YYYY-MM-DD>

> Regra: nenhuma linha de código antes dessa spec estar "Aprovada". Se descobrir
> requisito faltando no meio da implementação, PARE e atualize a spec primeiro —
> não improvise.

## Contexto

Por que essa feature existe. O que motivou (RF do desafio, bug, pedido do squad).
2-4 frases, sem enrolação.

## Requisitos funcionais

Numerados, um comportamento testável por item. Use MUST / SHOULD / MAY.

- **FR-1**: O sistema MUST ...
- **FR-2**: O sistema SHOULD ...

## Interface / contrato

Assinatura da função, tool ou endpoint envolvido (é código Python aqui, não precisa
de TypeScript) — o que entra, o que sai, tipos.

```python
def nome_da_funcao(arg: Tipo) -> TipoDeRetorno:
    ...
```

## Critérios de aceite

Formato Given/When/Then. Cada um referencia pelo menos um FR-N.

- **AC-1** (FR-1): Dado <contexto>, quando <ação>, então <resultado esperado>.
- **AC-2** (FR-1): Dado <contexto>, quando <ação>, então <resultado esperado>.

## Casos de borda

Numerados. Cobrir falha de cada dependência externa (API fora do ar, dado inválido,
resposta vazia etc.).

- **EC-1**: ...
- **EC-2**: ...

## Fora de escopo

O que foi considerado e descartado deliberadamente, e por quê. Evita scope creep.

- ...
