# O mapa do projeto

Uma foto datada de todos os guias vivos de uma vez. Nasceu à mão no `predator-servidor-ia` em
20/09/2026 e virou mecanismo aqui.

**O mapa lê, nunca escreve.** Não tem checkbox, de propósito. O estado é dos guias, e dois
lugares dizendo a mesma coisa é o que este método existe para evitar. Pedido de marcar algo no
mapa se responde com "isso é no guia".

## Rodar

```bash
python3 ~/.claude/skills/detonado/scripts/mapa.py --dry-run
python3 ~/.claude/skills/detonado/scripts/mapa.py
python3 ~/.claude/skills/detonado/scripts/mapa.py --dir ~/projetos/outro
```

Sai em `docs/mapa-<projeto>/mapa-<projeto>.html`. Sem `docs/` ou sem nenhum `docs/guia-*/`, o
script sai com 2 e diz o que faltou: sem guia não há o que mapear.

## As seções

1. **Cabeçalho**, com a data da foto e a frase dizendo que o estado vivo está nos guias.
2. **Tiles**, um por guia vivo: percentual, caixas provadas, barra e a linha de estado.
3. **Onde paramos**, o agregado em uma frase.
4. **O que trava o quê**, o fluxograma. Só sai com dependência declarada (ver abaixo).
5. **Linha do tempo por fase**, com barra para fase datada, ponto para fase que só tem fim, e
   contorno tracejado para fase aberta até hoje.
6. **Pra onde vamos**, as fases abertas, com quantas etapas ainda estão sem prova.
7. **O que já está de pé**, tabela com fase, guia, estado, quando e **a fonte daquela data**.
8. **Fontes e guias vivos**, links para cada guia e para o registro.

## De onde vem cada número

| Número | Fonte |
|---|---|
| Caixas e percentual | `progresso.py` usado como biblioteca, nunca por shell e nunca digitado |
| Fase fechada | atributo `data-fechada`, gravado pelo `--fechar` |
| Fase cancelada | atributo `data-cancelada`, gravado pelo `--cancelar` |
| Fase sem atributo | git, varrendo o histórico do guia até achar quando ela fechou |
| Nada disso | o texto **sem registro**. Nunca estimativa |

A conta de caixas é a mesma do `progresso.py` e a mesma do `<script>` dentro do guia: todos os
checkboxes. Contar só as etapas daria um número que discorda do guia, e percentual que discorda
da fonte é bug, não arredondamento.

**Guia sem fase e sem caixa não vira tile.** Ele aparece numa nota dizendo que não mede
progresso, e nas fontes como documento. Um tile de 0% ali mentiria, sugerindo trabalho parado
onde não há trabalho a medir.

## Quando o fluxograma não sai

Dependência entre frentes não é dado que o guia tenha: ninguém nunca declarou. Sem declaração o
fluxograma **não sai**, e o mapa diz por quê e mostra o formato. Para declarar, um `mapa.json`
na raiz do projeto:

```json
{
  "depende": [
    {"de": "f2", "para": "f1", "porque": "só depois do backup"}
  ]
}
```

Inventar seta a partir de ordem de fase seria o jeito mais rápido de o mapa ficar bonito e
mentiroso na segunda semana.

## Publicar

Igual ao guia vivo: o derivado sai pelo `build_artifact.py`, a primeira publicação registra a
URL no HANDOFF, e republicar passa a mesma URL. Senão nasce um segundo link e o que está no
iPhone para de refletir o projeto. Publicar é ação externa, e só com ok do Bera.

Os portões de saída são os mesmos do guia, os dois manual-only: anti-slop e `cão-guia`.
