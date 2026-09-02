# Rádio pirata no Predator

> Projeto aberto em 02/09/2026 com o detonado. Comece pelo `HANDOFF.md`.

## O que é

Streaming de música local por Podman Quadlet, só no tailnet, provado do iPhone.

## Estado verificado em 02/09/2026

| Item | Valor | Prova |
|---|---|---|
| Projeto | aberto, Fase 0 em andamento | commit inicial |

## Convenções do ambiente

- A pasta é o contexto. Entre em `~/workspace/detonado/evals/fixtures/radio-pirata` e chame `claude`, nunca a partir do home.
- `tmux new -A -s radio-pirata` antes de qualquer coisa longa.
- O estado do projeto mora no `HANDOFF.md`. Outros repos apontam para ele, não copiam.
- Guia vivo em `docs/guia-radio-pirata/`, atualizado pelos scripts do detonado, nunca à mão.

## Mapa dos documentos

| Arquivo | O que é |
|---|---|
| `HANDOFF.md` | Ponto de retomada, escrito para o celular. **Comece por ele** |
| `SESSION.md` | Checkpoint da sessão. Apagável quando a fase fechar |
| `tasks/lessons.md` | O que custou caro |
| `docs/guia-radio-pirata/guia-radio-pirata.html` | Guia vivo, fonte da verdade, imagem por caminho relativo |
| `docs/guia-radio-pirata/build_artifact.py` | Deriva a versão publicável com as imagens em base64 |
