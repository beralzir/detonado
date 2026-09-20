#!/usr/bin/env python3
"""Monta guia consultivo e passo a passo, os dois documentos sem estado da skill.

A regra que separa esses dois do guia vivo está em references/documentos.md: só o guia vivo
tem estado. O consultivo não tem caixa nenhuma, e a marca do passo a passo vive no navegador
de quem lê, nunca em git.

Uso:
    documento.py --tipo consultivo --nome comparar-distro --conteudo c.json --dry-run
    documento.py --tipo passo --nome restaurar-backup --conteudo p.json

Formato do JSON, consultivo:
    {"titulo": "...", "subtitulo": "...", "problema": "...",
     "evidencia": [{"afirmacao": "...", "fonte": "..."}],
     "opcoes": [{"titulo": "...", "corpo": "...", "custo": "..."}],
     "recomendacao": "...", "viraria": ["..."]}

Formato do JSON, passo a passo:
    {"titulo": "...", "subtitulo": "...", "antes": ["..."],
     "passos": [{"texto": "...", "comando": "...", "esperado": "..."}],
     "errado": [{"sintoma": "...", "saida": "..."}]}
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
GUIA_DIR = SKILL / "assets" / "guia"


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def inline(t):
    """Crase vira code, asterisco duplo vira negrito. Mesma convencao do resto da skill."""
    t = esc(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)


def paras(t):
    blocos = [b.strip() for b in str(t).split("\n\n") if b.strip()]
    return "\n".join(f"<p>{inline(b)}</p>" for b in blocos) or "<p></p>"


def lista(itens):
    if not itens:
        return '<p class="nota">Nada declarado.</p>'
    return "<ul>\n" + "\n".join(f"<li>{inline(i)}</li>" for i in itens) + "\n</ul>"


def estilo_base():
    tpl = (GUIA_DIR / "guia.template.html").read_text(encoding="utf-8")
    m = re.search(r"<style>(.*?)</style>", tpl, re.DOTALL)
    return re.sub(r"\{\{TOKENS_CSS\}\}", "", m.group(1) if m else "")


def bloco_evidencia(itens):
    if not itens:
        return ('<div class="call aviso"><span class="lb">Sem evidência declarada</span>'
                '<p>Um consultivo sem o que sustenta a recomendação é opinião com tipografia '
                'boa. Declare ao menos uma afirmação e a fonte dela.</p></div>')
    linhas = "\n".join(
        f'<tr><td>{inline(e.get("afirmacao",""))}</td><td>{inline(e.get("fonte","sem fonte"))}</td></tr>'
        for e in itens)
    return ('<div class="tw" tabindex="0" role="group" aria-label="Tabela de afirmações e fontes">'
            '<table><thead><tr><th>Afirmação</th><th>Como se sabe</th></tr></thead><tbody>\n'
            + linhas + "\n</tbody></table></div>")


def bloco_opcoes(itens):
    if not itens:
        return '<p class="nota">Nenhuma opção declarada.</p>'
    out = []
    for o in itens:
        custo = f'<p class="custo">Custo: {inline(o["custo"])}</p>' if o.get("custo") else ""
        out.append(f'<div class="opcao"><h3>{inline(o.get("titulo",""))}</h3>'
                   f'{paras(o.get("corpo",""))}{custo}</div>')
    return "\n".join(out)


def bloco_passos(itens):
    if not itens:
        return '<p class="nota">Nenhum passo declarado.</p>'
    out = []
    for i, p in enumerate(itens, 1):
        cmd = ""
        if p.get("comando"):
            cmd = f'<div class="cb"><pre tabindex="0">{esc(p["comando"])}</pre></div>'
        esp = ""
        if p.get("esperado"):
            esp = f'<p class="esperado"><b>Esperado:</b> {inline(p["esperado"])}</p>'
        else:
            esp = ('<p class="esperado"><b>Esperado:</b> não declarado. Passo sem esperado é '
                   'passo que ninguém sabe se deu certo.</p>')
        out.append(
            f'<div class="passo">\n'
            f'<h3><span class="num">{i:02d}</span>{inline(p.get("texto",""))}</h3>\n'
            f'{cmd}{esp}\n'
            f'<label class="marca"><input type="checkbox" id="p{i}" '
            f'aria-label="Passo {i:02d}, feito nesta leitura"> feito, nesta leitura</label>\n'
            f'</div>')
    return "\n".join(out)


def bloco_errado(itens):
    if not itens:
        return '<p class="nota">Nada declarado. Vale escrever ao menos a falha mais comum.</p>'
    linhas = "\n".join(
        f'<tr><td>{inline(e.get("sintoma",""))}</td><td>{inline(e.get("saida",""))}</td></tr>'
        for e in itens)
    return ('<div class="tw" tabindex="0" role="group" aria-label="Tabela de falhas e saídas">'
            '<table><thead><tr><th>Sintoma</th><th>Saída</th></tr></thead><tbody>\n'
            + linhas + "\n</tbody></table></div>")


def main():
    ap = argparse.ArgumentParser(description="Monta guia consultivo ou passo a passo")
    ap.add_argument("--tipo", choices=["consultivo", "passo"], required=True)
    ap.add_argument("--nome", required=True, help="slug, minúsculas e hífens")
    ap.add_argument("--conteudo", type=Path, required=True, help="JSON com o conteúdo")
    ap.add_argument("--dir", type=Path, default=Path.cwd())
    ap.add_argument("--tokens", choices=["bera", "neutro"], default="bera")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    try:
        d = json.loads(a.conteudo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"ERRO: --conteudo: {e}", file=sys.stderr)
        return 2

    hoje = date.today().strftime("%d/%m/%Y")
    raiz = a.dir.expanduser().resolve()
    destino = raiz / "docs" / f"{a.tipo}-{a.nome}" / f"{a.tipo}-{a.nome}.html"
    tpl_nome = "consultivo.template.html" if a.tipo == "consultivo" else "passo.template.html"
    tpl = (GUIA_DIR / tpl_nome).read_text(encoding="utf-8")
    tokens = (GUIA_DIR / "tokens" / f"{a.tokens}.css").read_text(encoding="utf-8")

    comum = {
        "{{TOKENS_CSS}}": tokens,
        "{{ESTILO_BASE}}": estilo_base(),
        "{{TITULO}}": esc(d.get("titulo", a.nome)),
        "{{SUBTITULO}}": inline(d.get("subtitulo", "")),
        "{{RODAPE}}": f"{hoje} · {destino.name}",
    }
    if a.tipo == "consultivo":
        comum["{{EYEBROW}}"] = "detonado <span aria-hidden='true'>&#9670;</span> CONSULTIVO &middot; decide, não acompanha"
        comum["{{PROBLEMA}}"] = paras(d.get("problema", ""))
        comum["{{EVIDENCIA}}"] = bloco_evidencia(d.get("evidencia", []))
        comum["{{OPCOES}}"] = bloco_opcoes(d.get("opcoes", []))
        comum["{{RECOMENDACAO}}"] = paras(d.get("recomendacao", ""))
        comum["{{VIRARIA}}"] = lista(d.get("viraria", []))
    else:
        comum["{{EYEBROW}}"] = "detonado <span aria-hidden='true'>&#9670;</span> PASSO A PASSO &middot; marca sua, não progresso"
        comum["{{ANTES}}"] = lista(d.get("antes", []))
        comum["{{PASSOS}}"] = bloco_passos(d.get("passos", []))
        comum["{{ERRADO}}"] = bloco_errado(d.get("errado", []))

    saida = tpl
    for k, v in comum.items():
        saida = saida.replace(k, v)

    sobrou = re.findall(r"\{\{[A-Z_]+\}\}", saida)
    if sobrou:
        print(f"ERRO: placeholder sem valor: {', '.join(sorted(set(sobrou)))}", file=sys.stderr)
        return 2
    if a.tipo == "consultivo" and "type=\"checkbox\"" in saida:
        print("ERRO: consultivo com checkbox. Só o guia vivo tem estado.", file=sys.stderr)
        return 2

    if a.dry_run:
        print(f"[dry-run] {a.tipo} {a.nome}: {len(saida)} bytes, sairia em {destino}")
        return 0
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(saida, encoding="utf-8")
    print(f"{destino.relative_to(raiz) if destino.is_relative_to(raiz) else destino}: {len(saida)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
