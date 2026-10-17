#!/usr/bin/env python3
"""Trava da prancheta: hook PreToolUse da skill detonado, declarado no frontmatter do SKILL.md.

Duas regras do modo prancheta (references/prancheta.md, seção "A trava") que eram só texto:

1. O Claude não escreve no `db` do Artifact nas coleções que a página lê como atos do Bera:
   `marcas` (passo, opção, premissa e marco) e `estado` (nota geral e aprovação). O
   ArtifactData escreve como o Bera, e o `db` não distingue quem escreveu, então uma escrita
   do Claude ali vira marca ou aprovação dele. Leitura passa, inclusive com `out_dir`, que é
   como a pasta `lido/` nasce. As coleções do Claude, `chat` e `sonda`, passam.
2. Ninguém edita a leitura de volta: Edit, Write, MultiEdit e NotebookEdit em
   `docs/prancheta-<nome>/lido*/` (`lido/`, `lido-2/`, ...) são negados.

Bloquear é sair com 2 e explicar no stderr, que o Claude Code devolve ao modelo. Saída 2 em
PreToolUse bloqueia a chamada mesmo que o hook imprima JSON (documentação de hooks do Claude
Code, consultada em 17/10/2026).

Escrita no `db` com forma que a trava não consegue conferir (coleção ausente, `batch` sem
lista, segmento `.` ou `..`) é negada: a ferramenta recusaria de todo jeito, e a trava não
aposta. Ação desconhecida conta como escrita. Chamada que a trava nem consegue ler também é
negada: o matcher só manda para cá as cinco ferramentas da trava, e um JSON fundo demais
estourava o parser e passava (achado da revisão adversarial de 17/10/2026, com uns 2 KB no
Python 3.9).

O que fica de fora, e a referência diz: Bash escrevendo em `lido/` (sed -i, redirecionamento,
python), sessão retomada antes de o detonado ser invocado de novo, e o conteúdo do que o
Claude grava em `chat`.

Só stdlib, Python 3.9 ou mais. Teste: tests/test_trava.py.
"""

import json
import os
import re
import sys

# As coleções que a página da prancheta lê como atos do Bera. O tests/test_trava.py confere
# esta lista contra as coleções que o template usa: coleção nova na página reprova o teste até
# alguém decidir se ela é do Bera (entra aqui) ou do Claude.
PROTEGIDAS = frozenset({"marcas", "estado"})
LEITURAS = frozenset({"get", "list", "query", "profiles"})
EDICAO = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path",
          "NotebookEdit": "notebook_path"}
LIDO = re.compile(r"(?:^|/)docs/prancheta-[^/]+/lido[^/]*/", re.IGNORECASE)

CABECA = "BLOQUEADO pela trava da prancheta (detonado): "
PARE = ("Pare e diga ao Bera o que a trava barrou, sem tentar por outra ferramenta.")
MSG_DB = (CABECA + "o Claude não escreve em `{col}` no db do Artifact. Numa prancheta, marcas, "
          "nota geral e aprovação são atos do Bera na página, e o db grava qualquer escrita do "
          "ArtifactData como dele. O Claude escreve só em `chat` (as respostas do chat) e em "
          "`sonda`. Aprovação dita no chat é declaração: registre como declarada e peça ao Bera "
          "que aprove na prancheta. " + PARE + " Se este artefato não for uma prancheta, a "
          "trava vale mesmo assim até o fim do processo, e o caminho é uma sessão nova.")
MSG_FORMA = (CABECA + "escrita no db que a trava não consegue conferir ({motivo}). Nada foi "
             "escrito. Refaça com `collection` em cada escrita (no batch, dentro da lista "
             "`writes`).")
MSG_ILEGIVEL = (CABECA + "a trava não conseguiu ler esta chamada ({motivo}), e o que ela não "
                "confere não passa. Nada foi feito. " + PARE)
MSG_LIDO = (CABECA + "{caminho} fica numa pasta de leitura de volta "
            "(docs/prancheta-<nome>/lido*/), que guarda o que o db devolveu e não se edita, por "
            "nenhuma ferramenta. Se a leitura não fecha, leia de novo com o ArtifactData para uma "
            "pasta nova (lido-2/) e rode o --estado nela. Leitura montada à mão em outro lugar "
            "não vale: o --estado só aceita lido*/. " + PARE)


def bloqueia(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(2)


def colecoes(entrada):
    """As coleções que uma chamada do ArtifactData escreve. Lista vazia para leitura, e
    (None, motivo) quando a escrita não tem forma conferível."""
    acao = str(entrada.get("action") or "").strip().lower()
    if acao in LEITURAS:
        return [], None
    cols = []
    if acao == "batch":
        escritas = entrada.get("writes")
        if not isinstance(escritas, list) or not escritas:
            return None, "batch sem a lista `writes`"
        for i, w in enumerate(escritas):
            if not isinstance(w, dict) or not isinstance(w.get("collection"), str):
                return None, "batch com a escrita {} sem `collection`".format(i)
            cols.append(w["collection"])
        if isinstance(entrada.get("collection"), str):
            cols.append(entrada["collection"])
        return cols, None
    col = entrada.get("collection")
    if not isinstance(col, str) or not col.strip():
        return None, "ação `{}` sem `collection`".format(acao or "?")
    return [col], None


def confere_db(entrada):
    cols, motivo = colecoes(entrada)
    if cols is None:
        bloqueia(MSG_FORMA.format(motivo=motivo))
    for col in cols:
        segmentos = col.strip().strip("/").split("/")
        if any(s in (".", "..") for s in segmentos):
            bloqueia(MSG_FORMA.format(motivo="coleção com segmento `.` ou `..`: " + col))
        if segmentos[0].lower() in PROTEGIDAS:
            bloqueia(MSG_DB.format(col=col))


def em_lido(caminho, cwd):
    if not os.path.isabs(caminho) and cwd:
        caminho = os.path.join(cwd, caminho)
    candidatos = {os.path.normpath(caminho)}
    try:
        candidatos.add(os.path.realpath(caminho))
    except (OSError, ValueError):
        pass
    return any(LIDO.search(c.replace(os.sep, "/")) for c in candidatos)


def confere_edicao(nome, entrada, cwd):
    caminho = entrada.get(EDICAO[nome])
    if isinstance(caminho, str) and caminho.strip() and em_lido(caminho.strip(), cwd):
        bloqueia(MSG_LIDO.format(caminho=caminho))


def main():
    try:
        dados = json.load(sys.stdin)
    except Exception as e:  # inclui o RecursionError de JSON fundo demais
        bloqueia(MSG_ILEGIVEL.format(motivo=type(e).__name__))
    if not isinstance(dados, dict):
        bloqueia(MSG_ILEGIVEL.format(motivo="a entrada não é um objeto JSON"))
    nome = dados.get("tool_name") or ""
    entrada = dados.get("tool_input")
    if not isinstance(entrada, dict):
        entrada = {}
    if nome == "ArtifactData":
        confere_db(entrada)
    elif nome in EDICAO:
        confere_edicao(nome, entrada, dados.get("cwd") or "")
    sys.exit(0)


if __name__ == "__main__":
    main()
