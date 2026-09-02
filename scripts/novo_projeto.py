#!/usr/bin/env python3
"""Abre ou adota um projeto no formato do detonado.

Cria, a partir dos templates da skill, os cinco artefatos: CLAUDE.md, HANDOFF.md, SESSION.md,
tasks/lessons.md e docs/guia-<nome>/ (guia vivo, build_artifact.py, img/). Nunca sobrescreve:
arquivo existente é pulado e relatado, o que torna o script seguro para adotar projeto que já
tem parte da estrutura.

Uso:
    novo_projeto.py --nome homelab --titulo "Homelab: RomM no Predator" \
        --objetivo "Servidor de jogos antigos no Predator, por Podman Quadlet, só no tailnet." \
        --fases fases.json [--dir ~/projetos/homelab] [--tokens bera|neutro] [--dry-run]

O JSON das fases está descrito em references/metodo.md. Crase no texto da etapa vira <code>.
Sai 0 se criou ou pulou sem erro, 2 se faltou entrada ou o JSON é inválido.
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL / "assets" / "templates"
GUIA = SKILL / "assets" / "guia"
ID_OK = re.compile(r"^[a-z0-9][a-z0-9-]*$")
GITIGNORE = "docs/**/*.artifact.html\n*.env\n.DS_Store\n__pycache__/\n"


def erro(msg: str) -> int:
    print("ERRO: " + msg, file=sys.stderr)
    return 2


def inline_code(texto: str) -> str:
    """Escapa HTML e converte `crase` em <code>."""
    partes = texto.split("`")
    out = []
    for i, p in enumerate(partes):
        p = html.escape(p, quote=False)
        out.append(f"<code>{p}</code>" if i % 2 == 1 else p)
    return "".join(out)


def validar_fases(dados) -> list:
    if not isinstance(dados, dict) or not isinstance(dados.get("fases"), list) or not dados["fases"]:
        raise ValueError('esperava {"fases": [...]} com pelo menos uma fase')
    ids = set()
    fases = []
    for n, f in enumerate(dados["fases"]):
        for campo in ("id", "tag", "titulo", "etapas"):
            if campo not in f:
                raise ValueError(f"fase {n}: falta o campo '{campo}'")
        if not ID_OK.match(f["id"]):
            raise ValueError(f"fase {n}: id '{f['id']}' fora do padrão [a-z0-9-]")
        if f["id"] in ids:
            raise ValueError(f"id repetido: {f['id']}")
        ids.add(f["id"])
        if not isinstance(f["etapas"], list) or not f["etapas"]:
            raise ValueError(f"fase {f['id']}: etapas vazias")
        etapas = []
        for k, e in enumerate(f["etapas"], start=1):
            if isinstance(e, str):
                e = {"texto": e}
            if not isinstance(e, dict) or not e.get("texto"):
                raise ValueError(f"fase {f['id']}, etapa {k}: precisa de 'texto'")
            etapas.append({"n": k, "texto": e["texto"], "prova": e.get("prova", ""), "quem": e.get("quem", "")})
        fases.append({"id": f["id"], "tag": f["tag"], "titulo": f["titulo"],
                      "resumo": f.get("resumo", ""), "etapas": etapas})
    return fases


def render_fase(tpl: str, f: dict) -> str:
    linhas = []
    for e in f["etapas"]:
        extra = ""
        if e["prova"]:
            extra += f'<small class="pq">Pronto quando: {inline_code(e["prova"])}</small>'
        if e["quem"]:
            extra += f'<small class="quem">com {html.escape(e["quem"])}</small>'
        linhas.append(f'  <label><input type="checkbox" id="e-{f["id"]}-{e["n"]}">{inline_code(e["texto"])}{extra}</label>')
    return (tpl.replace("{{ID}}", f["id"])
               .replace("{{TAG}}", html.escape(f["tag"]))
               .replace("{{TITULO}}", inline_code(f["titulo"]))
               .replace("{{RESUMO}}", inline_code(f["resumo"]))
               .replace("{{ETAPAS}}", "\n".join(linhas)))


def render_nav(fases: list) -> str:
    out = []
    for f in fases:
        out.append(f'   <a href="#{f["id"]}"><span class="dot" data-dot="{f["id"]}"></span>'
                   f'<span class="nnum">{html.escape(f["id"].upper())}</span>{inline_code(f["titulo"])}</a>')
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Abre ou adota um projeto no formato do detonado")
    ap.add_argument("--nome", required=True, help="nome curto, minúsculas e hífens")
    ap.add_argument("--titulo", required=True)
    ap.add_argument("--objetivo", required=True, help="uma frase")
    ap.add_argument("--fases", required=True, type=Path, help="JSON das fases")
    ap.add_argument("--dir", type=Path, help="padrão ~/projetos/<nome>")
    ap.add_argument("--tokens", choices=["bera", "neutro"], default="bera")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not ID_OK.match(a.nome):
        return erro("nome fora do padrão: minúsculas, dígitos e hífens")
    destino = (a.dir or Path.home() / "projetos" / a.nome).expanduser().resolve()
    home = str(Path.home())
    dir_legivel = "~" + str(destino)[len(home):] if str(destino).startswith(home) else str(destino)

    try:
        fases = validar_fases(json.loads(a.fases.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError) as e:
        return erro(f"JSON das fases: {e}")

    faltam = [p for p in (TEMPLATES / "CLAUDE.md", TEMPLATES / "HANDOFF.md", TEMPLATES / "SESSION.md",
                          TEMPLATES / "lessons.md", GUIA / "guia.template.html", GUIA / "fase.template.html",
                          GUIA / "tokens" / f"{a.tokens}.css", SKILL / "scripts" / "build_artifact.py")
              if not p.is_file()]
    if faltam:
        return erro("template ausente na skill: " + ", ".join(str(p) for p in faltam))

    data = dt.date.today().strftime("%d/%m/%Y")
    mes = dt.date.today().strftime("%m/%Y")
    subs = {"{{NOME}}": a.nome, "{{TITULO}}": a.titulo, "{{OBJETIVO}}": a.objetivo,
            "{{DATA}}": data, "{{DIRETORIO}}": dir_legivel}

    def preencher(texto: str) -> str:
        for k, v in subs.items():
            texto = texto.replace(k, v)
        return texto

    guia_dir = destino / "docs" / f"guia-{a.nome}"
    arquivos = {
        destino / "CLAUDE.md": preencher((TEMPLATES / "CLAUDE.md").read_text(encoding="utf-8")),
        destino / "HANDOFF.md": preencher((TEMPLATES / "HANDOFF.md").read_text(encoding="utf-8")),
        destino / "SESSION.md": preencher((TEMPLATES / "SESSION.md").read_text(encoding="utf-8")),
        destino / "tasks" / "lessons.md": preencher((TEMPLATES / "lessons.md").read_text(encoding="utf-8")),
        destino / ".gitignore": GITIGNORE,
        guia_dir / "img" / ".gitkeep": "",
    }

    tpl_guia = (GUIA / "guia.template.html").read_text(encoding="utf-8")
    tpl_fase = (GUIA / "fase.template.html").read_text(encoding="utf-8")
    tokens = (GUIA / "tokens" / f"{a.tokens}.css").read_text(encoding="utf-8")
    guia = (tpl_guia.replace("{{TOKENS_CSS}}", tokens)
                    .replace("{{NAV_FASES}}", render_nav(fases))
                    .replace("{{SECOES_FASES}}", "\n\n".join(render_fase(tpl_fase, f) for f in fases))
                    .replace("{{EYEBROW}}", f"guia vivo &nbsp;·&nbsp; {mes}")
                    .replace("{{ARQUIVO}}", f"docs/guia-{a.nome}/guia-{a.nome}.html")
                    .replace("{{TITULO}}", html.escape(a.titulo))
                    .replace("{{RESUMO}}", inline_code(a.objetivo))
                    .replace("{{NOME}}", a.nome)
                    .replace("{{DATA}}", data))
    arquivos[guia_dir / f"guia-{a.nome}.html"] = guia
    arquivos[guia_dir / "build_artifact.py"] = (SKILL / "scripts" / "build_artifact.py").read_text(encoding="utf-8")

    sobra = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", guia)))
    if sobra:
        return erro("placeholder não preenchido no guia: " + ", ".join(sobra))

    criados, pulados = [], []
    for caminho, conteudo in arquivos.items():
        rel = caminho.relative_to(destino)
        if caminho.exists():
            pulados.append(str(rel))
            continue
        criados.append(str(rel))
        if not a.dry_run:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(conteudo, encoding="utf-8")
            if caminho.suffix == ".py":
                os.chmod(caminho, 0o755)

    print(f"{'[dry-run] ' if a.dry_run else ''}projeto {a.nome} em {dir_legivel}")
    for c in criados:
        print("  criado  " + c)
    for p in pulados:
        print("  pulado  " + p + " (já existia, não sobrescrevo)")
    if ".gitignore" in pulados:
        print("  confira se o .gitignore existente tem: " + " ".join(GITIGNORE.split()))
    if not (destino / ".git").exists():
        print("  sem .git: rode `git init -b main` e faça o commit inicial")
    return 0


if __name__ == "__main__":
    sys.exit(main())
