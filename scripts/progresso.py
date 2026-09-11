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
    progresso.py GUIA.html --declarar e-f1-2     anota "declarado pelo Bera, sem prova" na etapa
    progresso.py GUIA.html --onde-paramos "texto com `crase` virando code"   reescreve #status-atual
    progresso.py GUIA.html --inserir-fase fases.json   acrescenta fases novas (nav e seção)
    progresso.py GUIA.html --cancelar f3 --motivo "a F1 respondeu antes, e mais barato"

Fase cancelada é escopo que morreu no meio, e não é nem aberta nem fechada. `--cancelar`
troca os checkboxes da fase por uma lista estática com o motivo e a data: as caixas somem,
então tanto este script quanto o JS da própria página param de contá-las, e a barra passa a
medir só o que ainda pode acontecer. Por isso funciona também nos guias já publicados, que
não conhecem classe de CSS nova. É destrutivo de propósito e não tem `--descancelar`:
desfazer é `git checkout` no guia.

Convenção do template: etapa é `<input type="checkbox" id="e-<fase>-<n>">`, fase é
`<input type="checkbox" data-done="<fase>">`. O percentual conta todos os checkboxes, igual ao
script da página. Estado e estrutura do guia mudam só por aqui: o que sobra para edição à mão é
a prosa livre das seções (parágrafos, tabelas, blocos de comando).

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


def hoje() -> str:
    import datetime as _dt
    return _dt.date.today().strftime("%d/%m/%Y")


def inline_code(texto: str) -> str:
    """Mesma conversão do novo_projeto.py: crase vira <code>, asterisco duplo vira <strong>."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from novo_projeto import inline_code as _ic  # noqa: E402
    return _ic(texto)


def declarar(html: str, it: dict, data: str):
    """Anota a etapa como declarada sem prova. Recusa etapa marcada."""
    if it["checked"]:
        return html, "recusado: etapa marcada como provada, desmarque antes de declarar"
    fim_label = html.index("</label>", it["span"][1])
    trecho = html[it["span"][1]:fim_label]
    if 'class="decl"' in trecho:
        return html, f"{it['id']} já tinha declaração, mantida"
    nota = f'<small class="decl">Declarado pelo Bera em {data}, sem prova</small>'
    return html[:fim_label] + nota + html[fim_label:], f"declarou {it['id']} em {data}"


def onde_paramos(html: str, texto: str):
    m = re.search(r'(<p id="status-atual"[^>]*>).*?(</p>)', html, flags=re.S)
    if not m:
        return html, 0
    return html[:m.start()] + m.group(1) + inline_code(texto) + m.group(2) + html[m.end():], 1


def inserir_fase(html: str, caminho_json: Path, itens):
    """Acrescenta fases novas antes da seção de referência, com link na nav."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from novo_projeto import validar_fases, render_fase, render_nav  # noqa: E402
    tpl = Path(__file__).resolve().parent.parent / "assets" / "guia" / "fase.template.html"
    fases = validar_fases(json.loads(caminho_json.read_text(encoding="utf-8")))
    existentes = {it["fase"] for it in itens if it["fase"]}
    repetidas = [f["id"] for f in fases if f["id"] in existentes]
    if repetidas:
        raise ValueError("fase já existe no guia: " + ", ".join(repetidas))
    marca_nav = '   <div class="navsec">Referência</div>'
    marca_sec = '<section id="comandos">'
    if marca_nav not in html or marca_sec not in html:
        raise ValueError("guia sem os marcadores do template (navsec Referência, section#comandos)")
    tpl_fase = tpl.read_text(encoding="utf-8")
    html = html.replace(marca_nav, render_nav(fases) + "\n" + marca_nav, 1)
    html = html.replace(marca_sec, "\n\n".join(render_fase(tpl_fase, f) for f in fases) + "\n\n" + marca_sec, 1)
    return html, [f["id"] for f in fases]


def carimbar(html: str, data: str):
    n = 0
    novo, k = re.subn(r'(id="status-atual"[^>]*\bdata-v=")[^"]*(")', rf"\g<1>{data}\g<2>", html, count=1)
    n += k
    novo, k = re.subn(r'(<[^>]*\bid="atualizado"[^>]*>)[^<]*(</)', rf"\g<1>{data}\g<2>", novo, count=1)
    n += k
    return novo, n


def cancelar(html: str, fase: str, motivo: str, data: str):
    """Troca os checkboxes de uma fase por uma lista estatica com o motivo.

    Escopo que morreu no meio nao e aberto nem fechado, e o guia nao tinha como dizer isso.
    Marcar como fechada mentiria, e deixar aberta faz a barra prometer trabalho que nao
    existe. A saida e tirar as caixas: o que sai do numerador sai tambem do denominador,
    nos dois contadores, o deste script e o do <script> da propria pagina, sem precisar
    tocar no JS de guia nenhum. E por isso que funciona nos guias ja publicados.

    Estilo inline, e nao classe: guia gerado antes desta versao nao tem a regra no <style>,
    e injetar CSS num arquivo ja publicado e mais invasivo que a propria mudanca.
    """
    sec = re.compile(
        r'(<section class="phase" id="' + re.escape(fase) + r'")(.*?)(</section>)',
        re.DOTALL | re.IGNORECASE)
    m = sec.search(html)
    if not m:
        return None, f"fase {fase} nao encontrada no guia"
    abertura, corpo, fim = m.group(1), m.group(2), m.group(3)
    if 'data-cancelada=' in abertura or 'data-cancelada=' in corpo[:200]:
        return None, f"fase {fase} ja esta cancelada"

    bloco = re.search(r'<div class="checks">(.*?)</div>', corpo, re.DOTALL | re.IGNORECASE)
    if not bloco:
        return None, f"fase {fase} nao tem bloco de etapas para cancelar"

    # Cada etapa vira item de lista, sem o input. O "pronto quando" fica: ele explica o que
    # a fase teria provado, e e justamente o que se perde ao cancelar.
    itens = []
    for lab in re.finditer(r'<label>(.*?)</label>', bloco.group(1), re.DOTALL | re.IGNORECASE):
        texto = re.sub(r'<input\b[^>]*>', '', lab.group(1), flags=re.IGNORECASE).strip()
        itens.append(f'   <li style="margin-bottom:8px">{texto}</li>')
    lista = "\n".join(itens) if itens else '   <li>sem etapas</li>'

    aviso = (
        f'<div class="call aviso" data-cancelada="{data}">\n'
        f'  <span class="lb">CANCELADA</span>\n'
        f'  <p><strong>Cancelada em {data}.</strong> {motivo}</p>\n'
        f' </div>\n'
        f' <ul style="opacity:.6;margin:0 0 20px;padding-left:20px">\n{lista}\n </ul>'
    )
    corpo_novo = corpo.replace(bloco.group(0), aviso)
    # A fase deixa de ter caixa de "Fase concluida": nao foi concluida nem esta pendente.
    corpo_novo = re.sub(
        r'<label class="pdone">.*?</label>',
        '<span class="pdone" style="opacity:.6">Fase cancelada</span>',
        corpo_novo, count=1, flags=re.DOTALL | re.IGNORECASE)
    abertura_nova = abertura + f' data-cancelada="{data}"'
    novo_html = html[:m.start()] + abertura_nova + corpo_novo + fim + html[m.end():]

    # A navegacao lateral tambem mente se nao for tocada: o ponto da fase fica apagado
    # (o JS procura .pdone input, que acabou de sumir) e a linha continua parecendo
    # pendente. Estilo inline pelo mesmo motivo do resto: guia ja publicado nao tem classe.
    nav = re.compile(
        r'(<a href="#' + re.escape(fase) + r'")((?:(?!</a>).)*</a>)',
        re.DOTALL | re.IGNORECASE)
    def marca_nav(mm):
        corpo_nav = mm.group(2)
        if 'cancelada' in corpo_nav.lower():
            return mm.group(0)
        corpo_nav = corpo_nav.replace('</a>', ' <span style="font-size:10px;letter-spacing:.1em">CANCELADA</span></a>', 1)
        return mm.group(1) + ' style="opacity:.45;text-decoration:line-through"' + corpo_nav
    return nav.sub(marca_nav, novo_html, count=1), None


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
    ap.add_argument("--declarar", nargs="+", metavar="ID", default=[])
    ap.add_argument("--onde-paramos", metavar="TEXTO")
    ap.add_argument("--inserir-fase", metavar="FASES.json", type=Path)
    ap.add_argument("--cancelar", nargs="+", metavar="FASE", default=[],
                    help="escopo que morreu: tira as caixas da fase e escreve o motivo")
    ap.add_argument("--motivo", metavar="TEXTO",
                    help="obrigatorio com --cancelar: por que a fase morreu")
    a = ap.parse_args()

    html = ler(a.guia)
    itens = inventario(html)
    if not itens:
        print(f"ERRO: {a.guia} não tem checkbox nenhum, não parece um guia do detonado", file=sys.stderr)
        return 2

    if a.carimbar and not DATA.match(a.carimbar):
        print("ERRO: --carimbar espera DD/MM/AAAA", file=sys.stderr)
        return 2

    if a.cancelar and not a.motivo:
        print("ERRO: --cancelar exige --motivo. Fase que morre sem motivo escrito vira\n       caixa orfa daqui a um mes, que e o problema que este comando existe para evitar.",
              file=sys.stderr)
        return 2
    if a.motivo and not a.cancelar:
        print("ERRO: --motivo so faz sentido com --cancelar", file=sys.stderr)
        return 2

    mudancas = []
    if a.inserir_fase:
        try:
            html, novas = inserir_fase(html, a.inserir_fase, itens)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(f"ERRO: --inserir-fase: {e}", file=sys.stderr)
            return 2
        mudancas.append("inseriu fase(s) " + ", ".join(novas))
        itens = inventario(html)

    for f in a.cancelar:
        html_novo, erro = cancelar(html, f, a.motivo, hoje())
        if erro:
            print(f"ERRO: --cancelar: {erro}", file=sys.stderr)
            return 2
        html = html_novo
        mudancas.append(f"cancelou a fase {f}")
    if a.cancelar:
        itens = inventario(html)
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

    if a.declarar:
        indice = {it["id"]: it for it in itens if it["tipo"] == "etapa"}
        faltando = [i for i in a.declarar if i not in indice]
        if faltando:
            print("ERRO: id inexistente no guia: " + ", ".join(faltando), file=sys.stderr)
            return 2
        data = a.carimbar or hoje()
        for i in sorted(a.declarar, key=lambda i: -indice[i]["span"][0]):
            html, msg = declarar(html, indice[i], data)
            mudancas.append(msg)
        itens = inventario(html)

    if a.onde_paramos:
        html, n = onde_paramos(html, a.onde_paramos)
        if n == 0:
            print("ERRO: não achei <p id=\"status-atual\"> para reescrever", file=sys.stderr)
            return 2
        mudancas.append("reescreveu o bloco Onde paramos")
        if not a.carimbar:
            a.carimbar = hoje()

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
