# Handoff: {{TITULO}}

Atualizado em {{DATA}}. Escrito para ser lido no celular via SSH.

**Projeto aberto, Fase 0 em andamento.** {{OBJETIVO}} Se o Bera perguntar "onde paramos?", a
resposta começa por este parágrafo e pelo `SESSION.md`.

---

## 1. Voltando

```bash
tmux new -A -s {{NOME}}
cd {{DIRETORIO}}
claude
```

Cole na primeira mensagem:

```
Retomando o {{NOME}} com o detonado. Leia o CLAUDE.md, o HANDOFF.md e o SESSION.md
desta pasta antes de qualquer coisa. Estou no celular via SSH: bloco único por vez e resposta curta.
```

## 2. Sanidade em um bloco

```bash
git log --oneline -1
python3 ~/.claude/skills/detonado/scripts/progresso.py docs/guia-{{NOME}}/guia-{{NOME}}.html --resumo
git status -sb | head -1
```

Esperado: o último commit conhecido, o progresso igual ao do guia, árvore limpa. Acrescente aqui
os serviços do projeto conforme existirem, sempre com o esperado logo abaixo. Linhas soltas, sem
chaves em volta: bloco com chaves quebra ao colar no celular. Só comandos que imprimem estado,
nada que reinicie, apague ou instale.

## 3. O que já está de pé

| Item | Valor | Data da prova |
|---|---|---|
| Estrutura do projeto | cinco artefatos criados pelo detonado | {{DATA}} |

## 4. Pendências

| Item | Com quem | Comando ou passo |
|---|---|---|
| Fase 0: publicar o guia e commitar o SESSION.md | Claude | `python3 docs/guia-{{NOME}}/build_artifact.py` |

## 5. Resolvidos

### Na sessão de {{DATA}}

- Projeto aberto com o detonado. Fases validadas com o Bera.

## 5b. O que está publicado

Uma linha por artefato publicado. **A URL sozinha não diz se o que está no ar é o que está em
disco**, e descobrir isso republicando custa caro: o publish obriga a ler a versão publicada
inteira antes de sobrescrever. O `sha256` que o `build_artifact.py` imprime resolve, e
comparar é `sha256sum` no derivado.

| Artefato | URL | sha256 do derivado | Publicado em |
|---|---|---|---|
| `docs/guia-{{NOME}}/` | (primeira publicação registra aqui) | | |

## 6. Onde está cada coisa

| Arquivo | O que é |
|---|---|
| `CLAUDE.md` | Contexto do projeto, estado verificado, mapa dos documentos |
| `HANDOFF.md` | Este arquivo |
| `SESSION.md` | Checkpoint da sessão |
| `tasks/lessons.md` | O que custou caro |
| `docs/guia-{{NOME}}/` | Guia vivo, imagens, invocador do build_artifact |
