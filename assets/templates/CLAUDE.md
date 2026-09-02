# {{TITULO}}

> Projeto aberto em {{DATA}} com o detonado. Comece pelo `HANDOFF.md`.

## O que é

{{OBJETIVO}}

## Estado verificado em {{DATA}}

| Item | Valor | Prova |
|---|---|---|
| Projeto | aberto, Fase 0 em andamento | commit inicial |

## Convenções do ambiente

- A pasta é o contexto. Entre em `{{DIRETORIO}}` e chame `claude`, nunca a partir do home.
- `tmux new -A -s {{NOME}}` antes de qualquer coisa longa.
- O estado do projeto mora no `HANDOFF.md`. Outros repos apontam para ele, não copiam.
- Guia vivo em `docs/guia-{{NOME}}/`, atualizado pelos scripts do detonado, nunca à mão.

## Mapa dos documentos

| Arquivo | O que é |
|---|---|
| `HANDOFF.md` | Ponto de retomada, escrito para o celular. **Comece por ele** |
| `SESSION.md` | Checkpoint da sessão. Apagável quando a fase fechar |
| `tasks/lessons.md` | O que custou caro |
| `docs/guia-{{NOME}}/guia-{{NOME}}.html` | Guia vivo, fonte da verdade, imagem por caminho relativo |
| `docs/guia-{{NOME}}/build_artifact.py` | Deriva a versão publicável com as imagens em base64 |
