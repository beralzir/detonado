#!/usr/bin/env python3
"""Lê e atualiza o estado do guia vivo do detonado.

O estado é o atributo `checked` de cada checkbox. Este script é o único jeito sancionado de
mudar esse estado: edição à mão é como o guia diverge do que foi provado.

Uso:
    progresso.py GUIA.html                       resumo por fase
    progresso.py GUIA.html --listar              todas as etapas, com id e estado
    progresso.py GUIA.html --resumo              uma linha, para o bloco de sanidade
    progresso.py GUIA.html --json                estado completo em JSON
    progresso.py GUIA.html --marcar e-f1-2 e-f1-3
    progresso.py GUIA.html --desmarcar e-f1-3
    progresso.py GUIA.html --fechar f1           marca "Etapa concluída" da fase
    progresso.py GUIA.html --reabrir f1
    progresso.py GUIA.html --carimbar 02/09/2026 data em #status-atual[data-v] e #atualizado

Convenção do template: etapa é `<input type="checkbox" id="e-<fase>-<n>">`, fase é
`<input type="checkbox" data-done="<fase>">`. O percentual conta todos os checkboxes, igual ao
script da página.

Sai 0 em sucesso, 1 se há inconsistência (fase fechada com etapa aberta) e nada foi alterado,
2 se um id não existe, o arquivo não é um guia do detonado, ou a entrada é inválida.
"""

import argparse
import json
import re
import sys
from pathlib import Path

TAG = re.compile(r"<input\b[^>]*\btype=\"checkbox\"[^>]*>", re.IGNORECASE)
ID = re.compile(r"\bid=\"([^\"]+)\"")
DONE = re.compile(r"\bdata-done=\"([^\"]+)\"")
CHECKED = re.compile(r"\s+checked\b(?:=\"[^\"]*\")?")
ETAPA = re.compile(r"^e-([a-z0-9][a-z0-9-]*)-(\d+)$")
DATA = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def ler(caminho: Path) -> str:
    try:
        return caminho.read_text(encoding="utf-8")
    except OSError as e:
        print(f"ERRO: não consegui ler {caminho}: {e}", file=sys.stderr)
        sys.exit(2)


def inventario(html: str):
    """Lista de dicts na ordem do documento: id, fase, tipo (etapa|fase), checked, span."""
    itens = []
    for m in TAG.finditer(html):
        tag = m.group(0)
        mid = ID.search(tag)
        mdone = DONE.search(tag)
        checked = bool(CHECKED.search(tag))
        if mdone:
            itens.append({"id": mdone.group(1), "fase": mdone.group(1), "tipo": "fase",
                          "checked": checked, "span": m.span()})
        elif mid:
            me = ETAPA.match(mid.group(1))
            if me:
                itens.append({"id": mid.group(1), "fase": me.group(1), "tipo": "etapa",
                              "checked": checked, "span": m.span()})
            else:
                itens.append({"id": mid.group(1), "fase": None, "tipo": "solto",
                              "checked": checked, "span": m.span()})
        else:
            itens.append({"id": None, "fase": None, "tipo": "sem-id",
                          "checked": checked, "span": m.span()})
    return itens


def set_checked(html: str, span, valor: bool) -> str:
    ini, fim = span
    tag = html[ini:fim]
    tem = bool(CHECKED.search(tag))
    if valor and not tem:
        tag = tag[:-1].rstrip() + " checked>"
        if tag.endswith("/ checked>"):
            tag = tag[:-10].rstrip() + " checked>"
    elif not valor and tem:
        tag = CHECKED.sub("", tag)
    return html[:ini] + tag + html[fim:]


def por_fase(itens):
    fases = {}
    ordem = []
    for it in itens:
        if it["fase"] is None:
            continue
        if it["fase"] not in fases:
            fases[it["fase"]] = {"etapas": [], "fechada": None}
            ordem.append(it["fase"])
        if it["tipo"] == "etapa":
            fases[it["fase"]]["etapas"].append(it)
        elif it["tipo"] == "fase":
            fases[it["fase"]]["fechada"] = it["checked"]
    return ordem, fases


def inconsistencias(itens):
    avisos = []
    ordem, fases = por_fase(itens)
    for f in ordem:
        d = fases[f]
        abertas = [e["id"] for e in d["etapas"] if not e["checked"]]
        if d["fechada"] and abertas:
            avisos.append(f"fase {f} fechada com etapa aberta: {', '.join(abertas)}")
        if d["fechada"] is False and d["etapas"] and not abertas:
            avisos.append(f"fase {f} com todas as etapas provadas, pronta para --fechar {f}")
    soltos = [it for it in itens if it["tipo"] in ("solto", "sem-id")]
    if soltos:
        avisos.append(f"{len(soltos)} checkbox fora da convenção (sem id e-<fase>-<n> nem data-done)")
    return avisos


def resumo(itens) -> str:
    total = len(itens)
    marc = sum(1 for it in itens if it["checked"])
    pct = round(marc * 100 / total) if total else 0
    ordem, fases = por_fase(itens)
    fechadas = sum(1 for f in ordem if fases[f]["fechada"])
    return f"{marc}/{total} caixas, {pct}%, {fechadas}/{len(ordem)} fases fechadas"


def carimbar(html: str, data: str):
    n = 0
    novo, k = re.subn(r'(id="status-atual"[^>]*\bdata-v=")[^"]*(")', rf"\g<1>{data}\g<2>", html, count=1)
    n += k
    novo, k = re.subn(r'(<[^>]*\bid="atualizado"[^>]*>)[^<]*(</)', rf"\g<1>{data}\g<2>", novo, count=1)
    n += k
    return novo, n


def main() -> int:
    ap = argparse.ArgumentParser(description="Estado do guia vivo do detonado")
    ap.add_argument("guia", type=Path)
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--resumo", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--marcar", nargs="+", metavar="ID", default=[])
    ap.add_argument("--desmarcar", nargs="+", metavar="ID", default=[])
    ap.add_argument("--fechar", nargs="+", metavar="FASE", default=[])
    ap.add_argument("--reabrir", nargs="+", metavar="FASE", default=[])
    ap.add_argument("--carimbar", metavar="DD/MM/AAAA")
    a = ap.parse_args()

    html = ler(a.guia)
    itens = inventario(html)
    if not itens:
        print(f"ERRO: {a.guia} não tem checkbox nenhum, não parece um guia do detonado", file=sys.stderr)
        return 2

    if a.carimbar and not DATA.match(a.carimbar):
        print("ERRO: --carimbar espera DD/MM/AAAA", file=sys.stderr)
        return 2

    mudancas = []
    alvo = {}
    for i in a.marcar:
        alvo[("etapa", i)] = True
    for i in a.desmarcar:
        alvo[("etapa", i)] = False
    for f in a.fechar:
        alvo[("fase", f)] = True
    for f in a.reabrir:
        alvo[("fase", f)] = False

    if alvo:
        indice = {}
        for it in itens:
            if it["tipo"] == "etapa":
                indice[("etapa", it["id"])] = it
            elif it["tipo"] == "fase":
                indice[("fase", it["fase"])] = it
        faltando = [f"{t} {i}" for (t, i) in alvo if (t, i) not in indice]
        if faltando:
            print("ERRO: id inexistente no guia: " + ", ".join(faltando), file=sys.stderr)
            print("Ids válidos: " + ", ".join(
                (it["id"] if it["tipo"] == "etapa" else f"fase {it['fase']}")
                for it in itens if it["tipo"] in ("etapa", "fase")), file=sys.stderr)
            return 2
        # aplica de trás para a frente para os spans não deslocarem
        for chave, valor in sorted(alvo.items(), key=lambda kv: -indice[kv[0]]["span"][0]):
            it = indice[chave]
            if it["checked"] != valor:
                html = set_checked(html, it["span"], valor)
                mudancas.append(f"{'marcou' if valor else 'desmarcou'} {chave[0]} {chave[1]}")
        itens = inventario(html)

    if a.carimbar:
        html, n = carimbar(html, a.carimbar)
        mudancas.append(f"carimbou {a.carimbar} em {n} lugar(es)")
        if n == 0:
            print("AVISO: nenhum #status-atual[data-v] ou #atualizado encontrado para carimbar", file=sys.stderr)

    if mudancas:
        a.guia.write_text(html, encoding="utf-8")

    avisos = inconsistencias(itens)

    if a.json:
        ordem, fases = por_fase(itens)
        print(json.dumps({
            "arquivo": str(a.guia),
            "resumo": resumo(itens),
            "fases": [{"id": f, "fechada": fases[f]["fechada"],
                       "etapas": [{"id": e["id"], "checked": e["checked"]} for e in fases[f]["etapas"]]}
                      for f in ordem],
            "mudancas": mudancas, "avisos": avisos,
        }, ensure_ascii=False, indent=2))
    elif a.resumo:
        print(resumo(itens))
    else:
        for m in mudancas:
            print("  " + m)
        ordem, fases = por_fase(itens)
        for f in ordem:
            d = fases[f]
            marc = sum(1 for e in d["etapas"] if e["checked"])
            estado = "fechada" if d["fechada"] else ("aberta" if d["fechada"] is False else "sem caixa de fase")
            print(f"{f:8} {marc}/{len(d['etapas'])} etapas  {estado}")
            if a.listar:
                for e in d["etapas"]:
                    print(f"         [{'x' if e['checked'] else ' '}] {e['id']}")
        print(resumo(itens))
        for av in avisos:
            print("AVISO: " + av)

    if avisos and not mudancas and any(a.startswith("fase") and "fechada com etapa aberta" in a for a in avisos):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
