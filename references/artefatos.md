# Os artefatos

Cinco nascem com o projeto e três são opcionais. O que vai em cada um, quando atualizar, o
que nunca entra. Templates em `assets/templates/`.

| Artefato | Papel | Atualiza quando | Apagável |
|---|---|---|---|
| `CLAUDE.md` | Contexto do projeto para a sessão: o que é, estado verificado com data, convenções, mapa dos documentos | estado verificado mudou, documento novo entrou | não |
| `HANDOFF.md` | Ponto de retomada. Comece por ele | o ponto de retomada mudou | não |
| `SESSION.md` | Checkpoint da sessão, fora da janela de contexto | a cada ~5 passos, antes de compactar, ao fechar | sim, quando a fase fecha |
| `tasks/lessons.md` | O que custou caro | quando algo custou caro | não |
| `docs/guia-<projeto>/` | Guia vivo, imagens, script de build | a cada etapa provada | não |
| `docs/mapa-<projeto>/` | Mapa, a foto datada de todos os guias. Opcional | quando quiser a foto | sim, é foto |
| `docs/consultivo-<nome>/` | Guia consultivo: decide, sem estado nenhum. Opcional | quando a recomendação mudar | sim |
| `docs/passo-<nome>/` | Passo a passo: receita reusável, marca efêmera no navegador. Opcional | quando o procedimento mudar | sim |

## CLAUDE.md

Curto. O que o projeto é, em três parágrafos. Uma seção "Estado verificado em <data>" com tabela
(item, valor, prova). Convenções do ambiente que mudam o jeito de trabalhar (a pasta é o contexto,
tmux antes de coisa longa). Mapa dos documentos, com o HANDOFF em negrito e "comece por ele".

Não entra: histórico de sessões (SESSION e git), procedimento passo a passo (guia), estado de
outro projeto (aponte).

## HANDOFF.md

Escrito para ser lido no celular por SSH. Seções numeradas, sempre as mesmas, para o dedo achar:

0. Parágrafo de abertura com a data, e a hora quando houver mais de uma sessão no mesmo dia,
   dizendo em cinco linhas onde o projeto está e o que
   falta. Se o Bera perguntar "onde paramos", a resposta começa aqui.
1. **Voltando.** Os comandos para entrar (tmux, cd, claude) e a mensagem para colar na primeira
   linha da sessão.
2. **Sanidade em um bloco.** Um bloco único, idempotente, que imprime o estado dos serviços e
   valores que importam, com o "esperado" logo abaixo.
3. **O que já está de pé.** Tabela item, valor, data da prova.
4. **Pendências.** O que falta, com quem está (Claude ou Bera) e o comando pronto quando houver.
5. **Resolvidos.** Por sessão, a mais recente primeiro. Sintoma, causa, o que ficou.
6. **Onde está cada coisa.** Tabela arquivo e papel.

Regras: blocos únicos, nunca dez pequenos. Comando seguido do esperado. Toda afirmação de estado
leva data. Nunca cópia do estado de outro projeto: aponte para o HANDOFF dele.

## SESSION.md

O checkpoint que sobrevive à compactação. Formato de `assets/templates/SESSION.md`:

- Cabeçalho: data, "anterior: <data>", quando pode ser apagado.
- **O que fechou.** Tabela item e prova, com os hashes dos commits.
- **O fio aberto.** Três blocos: o que está provado bom (para não repetir), o que prova que
  falha, próxima hipótese, marcada "não testada".
- **O que falta.** Tabela item e quem.
- **Pendências de segurança**, se houver (chave impressa, porta aberta).
- **Formatos âncora.** Os formatos que decaem com o contexto longo, reafirmados: pergunta com
  até 4 opções por `AskUserQuestion`, PT-BR sem travessão e sem ponto e vírgula, prova antes de
  "feito", e o que mais a sessão tiver ensinado.
- **Vigilância.** O que conferir no próximo boot, na próxima atualização.

Quando a fase fecha, o que importa migra: estado para o HANDOFF, lição para o lessons. O
SESSION pode ser apagado ou zerado.

## tasks/lessons.md

Só o que custou tempo. Seções por tema. Cada lição em duas linhas: **sintoma ou regra em
negrito**, contexto com data e o comando certo. Caso isolado leva "[a confirmar]" até o Bera
dizer que é padrão.

Lição de infraestrutura fica no projeto. Lição de como trabalhar com o Bera fica em
`<bancada>/marvin/tasks/lessons.md`, e o projeto aponta. Não duplique.

## docs/guia-<projeto>/

`guia-<projeto>.html` (fonte da verdade, imagem por caminho relativo), `img/` (com `alt` em
todas), `build_artifact.py` (copiado pelo `novo_projeto.py`), e `guia-<projeto>.artifact.html`
derivado e ignorado pelo git. Detalhe em `references/guia-vivo.md`.

## Estado tem dono

| Informação | Dono | Quem aponta |
|---|---|---|
| Estado do projeto (versões, serviços, portas) | `HANDOFF.md` do projeto | Marvin, outros projetos |
| Brief, links curados, decisões de escopo | `<bancada>/marvin/projetos/<nome>.md` | HANDOFF do projeto |
| Como o Bera quer ser atendido | `<bancada>/marvin/contexto/preferencias.md` | ninguém copia |
| Lição de infra | `tasks/lessons.md` do projeto | Marvin, se virar regra geral |
| Lição de como trabalhar | `<bancada>/marvin/tasks/lessons.md` | projeto |

## Adotar um projeto existente

Leia o que existe antes de criar qualquer coisa. `novo_projeto.py` não sobrescreve e relata o
que pulou. Se o projeto já tem um HANDOFF com outra estrutura, não reformate: acrescente o que
falta (Voltando, Sanidade) e registre a divergência no SESSION. Guia vivo só entra se houver
fase aberta para ele mostrar.

## .gitignore mínimo

```
docs/**/*.artifact.html
*.env
.DS_Store
__pycache__/
```
