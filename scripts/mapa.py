#!/usr/bin/env python3
"""Desenha o mapa do projeto: uma foto datada de todos os guias vivos de uma vez.

O mapa LÊ, nunca escreve estado. Não tem checkbox de propósito: o estado é dos guias, e
dois lugares dizendo a mesma coisa é o que este método existe para evitar.

Fonte de cada número, sem exceção:
    progresso    contagem de caixas, por `progresso.py` usado como biblioteca
    data-fechada data de fechamento da fase, gravada pelo `--fechar`
    data-cancelada  data da morte da fase, gravada pelo `--cancelar`
    git          quando o atributo não existe (guia anterior a essa versão)
    sem registro quando nem o git sabe. Nunca estimativa

Uso:
    mapa.py                         desenha para o projeto no diretório atual
    mapa.py --dir ~/projetos/x      outro projeto
    mapa.py --dry-run               diz o que sairia, sem escrever
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import progresso  # noqa: E402

GUIA_DIR = SKILL / "assets" / "guia"
MAX_COMMITS = 80


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def hoje_br():
    return date.today().strftime("%d/%m/%Y")


def git(args, cwd):
    try:
        r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True,
                           text=True, timeout=25)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def tem_git(raiz):
    return bool(git(["rev-parse", "--git-dir"], raiz))


def fases_do_html(html):
    """Extrai id, tag, titulo e as datas declaradas de cada fase."""
    out = []
    for m in re.finditer(r'<section class="phase" id="([^"]+)"([^>]*)>(.*?)</section>',
                         html, re.DOTALL | re.IGNORECASE):
        fid, attrs, corpo = m.group(1), m.group(2), m.group(3)
        tag = re.search(r'<span class="nnum">([^<]*)</span>', corpo)
        tit = re.search(r'<h2[^>]*>(.*?)</h2>', corpo, re.DOTALL)
        titulo = re.sub(r"<[^>]+>", "", tit.group(1)).strip() if tit else fid
        out.append({
            "id": fid,
            "tag": tag.group(1).strip() if tag else fid.upper(),
            "titulo": titulo,
            "fechada_em": (re.search(r'data-fechada="([^"]*)"', attrs) or [None, None])[1]
                          if 'data-fechada=' in attrs else None,
            "cancelada_em": (re.search(r'data-cancelada="([^"]*)"', attrs) or [None, None])[1]
                            if 'data-cancelada=' in attrs else None,
            "cancelada": 'data-cancelada=' in attrs or "Fase cancelada" in corpo,
        })
    return out


def data_por_git(raiz, rel, fase_id, fechada):
    """Quando a fase apareceu, e quando passou a ler como fechada. Vazio se o git nao souber."""
    if not tem_git(raiz):
        return None, None
    saida = git(["log", "--reverse", "--format=%H %ad", "--date=short", "--", rel], raiz)
    if not saida:
        return None, None
    commits = [l.split(" ", 1) for l in saida.splitlines()][:MAX_COMMITS]
    inicio = fim = None
    for sha, quando in commits:
        blob = git(["show", f"{sha}:{rel}"], raiz)
        if not blob:
            continue
        sec = re.search(r'<section class="phase" id="' + re.escape(fase_id) + r'"(.*?)</section>',
                        blob, re.DOTALL | re.IGNORECASE)
        if not sec:
            continue
        if inicio is None:
            inicio = quando
        if fim is None and fechada:
            cb = re.search(r'<label class="pdone"[^>]*>.*?<input[^>]*data-done="'
                           + re.escape(fase_id) + r'"([^>]*)>', sec.group(1),
                           re.DOTALL | re.IGNORECASE)
            if cb and "checked" in cb.group(1):
                fim = quando
    return inicio, fim


def iso(br):
    """DD/MM/AAAA para AAAA-MM-DD. Devolve None se nao for data."""
    if not br:
        return None
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", br.strip())
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return br if re.match(r"^\d{4}-\d{2}-\d{2}$", br.strip()) else None


def coletar(raiz):
    """Le todos os guias do projeto. Devolve um dicionario por guia."""
    guias = []
    for gdir in sorted((raiz / "docs").glob("guia-*")):
        alvos = list(gdir.glob("guia-*.html"))
        alvos = [a for a in alvos if not a.name.endswith(".artifact.html")]
        if not alvos:
            continue
        caminho = alvos[0]
        html = progresso.ler(caminho)
        itens = progresso.inventario(html)
        ordem, fases = progresso.por_fase(itens)
        meta = {f["id"]: f for f in fases_do_html(html)}
        rel = str(caminho.relative_to(raiz))

        lista = []
        for fid in ordem:
            info = fases[fid]
            m = meta.get(fid, {"tag": fid.upper(), "titulo": fid,
                               "fechada_em": None, "cancelada_em": None, "cancelada": False})
            etapas = info["etapas"]
            feitas = sum(1 for e in etapas if e["checked"])
            fechada = bool(info["fechada"])
            ini = fim = None
            origem = "declarado"
            if m["cancelada_em"]:
                fim = m["cancelada_em"]
            elif m["fechada_em"]:
                fim = m["fechada_em"]
            elif fechada or m["cancelada"]:
                origem = "git"
                ini, fim = data_por_git(raiz, rel, fid, True)
                if not fim:
                    origem = "sem registro"
            if ini is None and origem != "sem registro":
                gi, _ = data_por_git(raiz, rel, fid, False)
                ini = gi
            lista.append({**m, "etapas": len(etapas), "feitas": feitas,
                          "fechada": fechada, "inicio": ini, "fim": fim, "origem": origem})

        # A conta e a do progresso.py e a do <script> da propria pagina: todos os checkboxes.
        # Contar so as etapas daria um numero que discorda do guia, e percentual que discorda
        # da fonte e exatamente o bug que este metodo existe para nao ter.
        total = len(itens)
        feitas = sum(1 for i in itens if i["checked"])
        guias.append({
            "vivo": len(itens) > 0,
            "nome": gdir.name.replace("guia-", ""),
            "arquivo": rel,
            "fases": lista,
            "total": total,
            "feitas": feitas,
            "pct": round(100 * feitas / total) if total else 0,
            "fechadas": sum(1 for f in lista if f["fechada"]),
            "canceladas": sum(1 for f in lista if f["cancelada"]),
            "status": progresso.resumo(itens),
            "avisos": progresso.inconsistencias(itens),
        })
    return guias


# ---------- desenho ----------

def bloco_tiles(guias):
    out = []
    for g in [x for x in guias if x["vivo"]]:
        cls = " cancelada" if g["total"] == 0 else ""
        estado = g["status"]
        if g["avisos"]:
            estado += " · " + "; ".join(g["avisos"][:2])
        out.append(
            f'<div class="tile{cls}">\n'
            f'  <h3>{esc(g["nome"])}</h3>\n'
            f'  <p class="n">{g["pct"]}%<small>{g["feitas"]}/{g["total"]} caixas</small></p>\n'
            f'  <div class="bar"><i style="width:{g["pct"]}%"></i></div>\n'
            f'  <p class="st">{esc(estado)}</p>\n'
            f'</div>')
    mortos = [g["nome"] for g in guias if not g["vivo"]]
    nota = ""
    if mortos:
        nota = ('\n<p class="nota">Sem tile, porque não têm fase nem caixa e portanto não medem '
                'progresso: ' + ", ".join(esc(m) for m in mortos) + ". Estão nas fontes, como documento.</p>")
    if not out:
        return '<p class="nota">Nenhum guia vivo em <code>docs/</code>.</p>' + nota
    return "\n".join(out) + nota


def bloco_timeline(guias):
    linhas = []
    for g in guias:
        for f in g["fases"]:
            linhas.append({**f, "guia": g["nome"]})
    datados = [l for l in linhas if iso(l["inicio"]) or iso(l["fim"])]
    sem = [l for l in linhas if l not in datados]
    if not datados:
        return ('<div class="call aviso"><span class="lb">Sem linha do tempo</span>'
                '<p>Nenhuma fase tem data: o <code>data-fechada</code> só existe em fase fechada '
                'depois desta versão, e o git não soube dizer. A linha do tempo volta assim que '
                'a primeira fase fechar por <code>--fechar</code>.</p></div>')

    todas = sorted({d for l in datados for d in (iso(l["inicio"]), iso(l["fim"])) if d})
    hoje = date.today().isoformat()
    ini_eixo, fim_eixo = todas[0], max(todas[-1], hoje)
    d0 = date.fromisoformat(ini_eixo).toordinal()
    d1 = max(date.fromisoformat(fim_eixo).toordinal(), d0 + 1)
    larg_rot, larg_eixo = 190, 560
    def x(d):
        return larg_rot + (date.fromisoformat(d).toordinal() - d0) / (d1 - d0) * larg_eixo
    alt = 34
    h = 44 + alt * len(datados) + 26
    p = [f'<svg viewBox="0 0 {larg_rot + larg_eixo + 30} {h}" role="img" '
         f'aria-label="Linha do tempo das fases, de {ini_eixo} a {fim_eixo}">']
    p.append(f'<line x1="{x(hoje):.0f}" y1="24" x2="{x(hoje):.0f}" y2="{h-26}" '
             f'stroke="var(--t5)" stroke-dasharray="3 3"/>')
    p.append(f'<text x="{x(hoje):.0f}" y="16" fill="var(--t4)" font-size="11" '
             f'text-anchor="middle" font-family="var(--sans)">hoje</text>')
    for i, l in enumerate(datados):
        y = 44 + i * alt
        rot = f'{l["tag"]} · {l["guia"]}'
        p.append(f'<text x="0" y="{y+4}" fill="var(--t3)" font-size="12" '
                 f'font-family="var(--sans)">{esc(rot[:30])}</text>')
        a, b = iso(l["inicio"]), iso(l["fim"])
        cor = "var(--t4)" if l["cancelada"] else ("var(--accent)" if l["fechada"] else "var(--t5)")
        if a and b and b > a:
            p.append(f'<rect x="{x(a):.0f}" y="{y-7}" width="{max(x(b)-x(a),3):.0f}" height="14" '
                     f'fill="{cor}" opacity="{0.35 if l["cancelada"] else 1}"/>')
        elif b:
            p.append(f'<circle cx="{x(b):.0f}" cy="{y}" r="6" fill="{cor}"/>')
        elif a:
            p.append(f'<rect x="{x(a):.0f}" y="{y-7}" width="{max(x(hoje)-x(a),3):.0f}" height="14" '
                     f'fill="none" stroke="{cor}" stroke-dasharray="4 3"/>')
    p.append("</svg>")
    legenda = ('<p class="legenda">'
               '<span><i style="background:var(--accent)"></i>fase fechada</span>'
               '<span><i style="border-style:dashed"></i>fase aberta, até hoje</span>'
               '<span><i style="background:var(--t4);opacity:.35"></i>fase cancelada</span></p>')
    nota = ""
    if sem:
        nomes = ", ".join(f'{l["tag"]} ({l["guia"]})' for l in sem[:6])
        nota = (f'<p class="nota">Sem registro de data, e por isso fora da linha: {esc(nomes)}. '
                f'Data estimada não entra aqui.</p>')
    return ('<figure><div class="rolagem">' + "\n".join(p) + "</div>"
            f'<figcaption>Foto de {hoje_br()}. Data vem de <code>data-fechada</code>, '
            f'<code>data-cancelada</code> ou do git, nunca de estimativa.</figcaption></figure>'
            + legenda + nota)


def bloco_fluxograma(raiz, guias):
    for cand in (raiz / "mapa.json", raiz / "docs" / "mapa.json"):
        if cand.exists():
            try:
                dados = json.loads(cand.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                return f'<div class="call perigo"><span class="lb">mapa.json inválido</span><p>{esc(e)}</p></div>'
            arestas = dados.get("depende", [])
            if not arestas:
                break
            itens = "\n".join(
                f'<li><strong>{esc(a.get("de",""))}</strong> depende de '
                f'<strong>{esc(a.get("para",""))}</strong>'
                + (f' <span class="nota">({esc(a["porque"])})</span>' if a.get("porque") else "")
                + "</li>" for a in arestas)
            return f'<ul>\n{itens}\n</ul>'
    ids = ", ".join(f'{f["id"]}' for g in guias for f in g["fases"][:3]) or "f1, f2"
    return ('<div class="call aviso"><span class="lb">Fluxograma não sai</span>'
            '<p>Dependência entre frentes não é dado que o guia tenha: ninguém declarou. '
            'Para o fluxograma existir, escreva um <code>mapa.json</code> na raiz do projeto '
            'assim, e rode de novo:</p>'
            '<pre>{\n  "depende": [\n    {"de": "f2", "para": "f1", '
            '"porque": "só depois do backup"}\n  ]\n}</pre>'
            f'<p class="nota">Ids disponíveis neste projeto: {esc(ids)}.</p></div>')


def bloco_pra_onde(guias):
    abertas = [(g["nome"], f) for g in guias for f in g["fases"]
               if not f["fechada"] and not f["cancelada"]]
    if not abertas:
        return '<p class="nota">Nenhuma fase aberta. Tudo que foi aberto fechou ou foi cancelado.</p>'
    li = []
    for nome, f in abertas:
        falta = f["etapas"] - f["feitas"]
        li.append(f'<li><strong>{esc(f["tag"])} · {esc(f["titulo"])}</strong> '
                  f'<span class="nota">({esc(nome)}, {falta} de {f["etapas"]} etapas sem prova)</span></li>')
    return "<ol>\n" + "\n".join(li) + "\n</ol>"


def bloco_de_pe(guias):
    fechadas = [(g["nome"], f) for g in guias for f in g["fases"] if f["fechada"] or f["cancelada"]]
    if not fechadas:
        return '<p class="nota">Nenhuma fase fechada ainda.</p>'
    linhas = []
    for nome, f in fechadas:
        estado = "cancelada" if f["cancelada"] else "fechada"
        quando = f["fim"] or "sem registro"
        fonte = {"declarado": "guia", "git": "git", "sem registro": "nenhuma"}.get(f["origem"], f["origem"])
        linhas.append(f'<tr><td>{esc(f["tag"])} · {esc(f["titulo"])}</td><td>{esc(nome)}</td>'
                      f'<td>{esc(estado)}</td><td>{esc(quando)}</td><td>{esc(fonte)}</td></tr>')
    return ('<div class="tw" tabindex="0" role="group" aria-label="Tabela de fases encerradas">'
            '<table><thead><tr><th>Fase</th><th>Guia</th><th>Estado</th><th>Quando</th>'
            '<th>Fonte da data</th></tr></thead><tbody>\n'
            + "\n".join(linhas) + "\n</tbody></table></div>")


def bloco_fontes(guias):
    li = [f'<li><a class="doc" href="../../{esc(g["arquivo"])}">{esc(g["arquivo"])}</a></li>'
          for g in guias]
    for doc in ("HANDOFF.md", "SESSION.md", "CLAUDE.md"):
        li.append(f'<li><a class="doc" href="../../{doc}">{doc}</a></li>')
    return "<ul>\n" + "\n".join(li) + "\n</ul>"


def estilo_base():
    tpl = (GUIA_DIR / "guia.template.html").read_text(encoding="utf-8")
    m = re.search(r"<style>(.*?)</style>", tpl, re.DOTALL)
    css = m.group(1) if m else ""
    return re.sub(r"\{\{TOKENS_CSS\}\}", "", css)


def main():
    ap = argparse.ArgumentParser(description="Desenha o mapa do projeto a partir dos guias vivos")
    ap.add_argument("--dir", type=Path, default=Path.cwd())
    ap.add_argument("--tokens", choices=["bera", "neutro"], default="bera")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    raiz = a.dir.expanduser().resolve()
    if not (raiz / "docs").is_dir():
        print(f"ERRO: {raiz} não tem docs/. O mapa se desenha a partir dos guias vivos do projeto.",
              file=sys.stderr)
        return 2
    guias = coletar(raiz)
    if not guias:
        print("ERRO: nenhum guia vivo em docs/guia-*/. Sem guia não há o que mapear.",
              file=sys.stderr)
        return 2

    nome = raiz.name
    destino = raiz / "docs" / f"mapa-{nome}" / f"mapa-{nome}.html"
    tokens = (GUIA_DIR / "tokens" / f"{a.tokens}.css").read_text(encoding="utf-8")
    tpl = (GUIA_DIR / "mapa.template.html").read_text(encoding="utf-8")

    vivos = [g for g in guias if g["vivo"]]
    total = sum(g["total"] for g in vivos)
    feitas = sum(g["feitas"] for g in vivos)
    pct = round(100 * feitas / total) if total else 0
    onde = (f'<p>{len(vivos)} guia(s) vivo(s), {feitas} de {total} caixas provadas ({pct}%). '
            f'O estado vivo está nos guias; isto aqui é foto de {hoje_br()}.</p>')

    saida = (tpl
             .replace("{{TOKENS_CSS}}", tokens)
             .replace("{{ESTILO_BASE}}", estilo_base())
             .replace("{{TITULO}}", f"Mapa do {nome}")
             .replace("{{EYEBROW}}", "detonado <span aria-hidden='true'>&#9670;</span> MAPA &middot; só lê, não marca")
             .replace("{{SUBTITULO}}", f"Foto de {hoje_br()}. O estado vivo está nos guias, e por isso este mapa não tem caixa para marcar.")
             .replace("{{TILES}}", bloco_tiles(guias))
             .replace("{{ONDE_PARAMOS}}", onde)
             .replace("{{FLUXOGRAMA}}", bloco_fluxograma(raiz, guias))
             .replace("{{TIMELINE}}", bloco_timeline(guias))
             .replace("{{PRA_ONDE}}", bloco_pra_onde(guias))
             .replace("{{DE_PE}}", bloco_de_pe(guias))
             .replace("{{FONTES}}", bloco_fontes(guias))
             .replace("{{RODAPE}}", f"Foto de {hoje_br()} · {destino.relative_to(raiz)}"))

    if a.dry_run:
        print(f"[dry-run] mapa de {nome}: {len(vivos)} guia(s) vivo(s), {feitas}/{total} caixas, {pct}%")
        for g in vivos:
            print(f"  {g['nome']}: {g['status']}")
        for g in [x for x in guias if not x["vivo"]]:
            print(f"  {g['nome']}: sem fase nem caixa, nao mede progresso")
        print(f"[dry-run] sairia em {destino}")
        return 0

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(saida, encoding="utf-8")
    print(f"{destino.relative_to(raiz)}: {len(vivos)} guia(s) vivo(s), {feitas}/{total} caixas, {pct}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
