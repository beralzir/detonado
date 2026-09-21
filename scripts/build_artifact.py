#!/usr/bin/env python3
"""Gera a versão publicável do guia vivo: imagens em base64 e documentos do repo embutidos.

Por que existe: o CSP dos Artifacts do Claude bloqueia host externo e não serve caminho
relativo, então `img/foo.jpg` não carrega lá e um link para `../../HANDOFF.md` morre. A fonte
da verdade continua sendo o HTML com caminho relativo, que abre bem no repo e no navegador
local. Este script deriva a cópia publicável, que o .gitignore ignora de propósito: derivado
versionado é como duas cópias divergem.

Duas substituições:

1. `<img src="img/x.png">`            vira `data:` em base64.
2. `<a class="doc" href="../../X.md">rótulo</a>` vira um `<details>` com o conteúdo do
   arquivo dentro, markdown já renderizado. No navegador local o mesmo HTML continua sendo
   um link relativo que funciona. Uma fonte, dois comportamentos.

O renderizador de markdown mora aqui dentro de propósito, e não num módulo ao lado: o
`novo_projeto.py` copia este arquivo sozinho para cada projeto, então um import de vizinho
quebraria na cópia. Ele é enxuto e cobre o que os documentos deste método usam. Não é
CommonMark e não tenta ser: o que não reconhece vira parágrafo, nunca erro.

Uso:
    python3 build_artifact.py [GUIA.html]

Sem argumento, usa o único *.html da própria pasta que não termina em .artifact.html.
Saída: <nome>.artifact.html ao lado da fonte.
Sai 0 se gerou, 1 se alguma imagem ou documento faltou (gera mesmo assim e lista), 2 se não
achou a fonte ou o resultado passou de 16 MB.
"""

import base64
import html
import mimetypes
import pathlib
import re
import sys

LIMITE_MB = 16
SRC = re.compile(r'(<img\b[^>]*\bsrc=")([^"]+)(")', re.IGNORECASE)
# Link marcado com class="doc": vira painel com o conteúdo do arquivo embutido.
DOC = re.compile(r'<a\b(?=[^>]*\bclass="doc")[^>]*\bhref="([^"]+)"[^>]*>(.*?)</a>',
                 re.IGNORECASE | re.DOTALL)
# A fonte é um documento completo (html lang, head, body), que é o que o navegador local e o
# cão-guia esperam. O Artifact embrulha o conteúdo no esqueleto dele, então o derivado sai sem
# doctype, html, head e body. Só as tags de embrulho caem, o conteúdo fica inteiro.
EMBRULHO = re.compile(r"<!doctype[^>]*>|</?html[^>]*>|</?head>|</?body[^>]*>", re.IGNORECASE)
TEXTO = {".md", ".markdown", ".txt", ".sh", ".py", ".conf", ".tsv", ".json", ".yml", ".yaml",
         ".toml", ".cfg", ".ini", ".service", ".container", ".volume", ".network"}


# --------------------------------------------------------------- markdown, mínimo e testado
# Run de N crases abre e só um run de exatamente N fecha, como no CommonMark. O regex
# ingênuo `([^`]+)` emparelha a terceira crase de um ```` ``` ```` solto com outra crase
# adiante e engole o texto do meio, quebrando o negrito em volta. Apareceu numa lição do
# lessons.md que cita ```` ```markdown ```` como prosa, em 10/09/2026.
_CODE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.S)
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITAL = re.compile(r"(?<![\*\w])\*([^\*\n]+)\*(?!\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_FENCE = re.compile(r"^```+\s*([A-Za-z0-9_+-]*)\s*$")
_SEP = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$")


def _inline(txt: str) -> str:
    """Escapa e aplica marcação inline.

    O código inline sai primeiro para sentinelas, e só volta no fim. Fazer o contrário, ou
    seja, fatiar o texto nos trechos de código e marcar cada pedaço, quebra negrito que
    começa ou termina em código: em ``**`ntfs-3g` no lugar do `ntfs3`.**`` os dois `**`
    caem em pedaços diferentes e o par nunca casa. Custou uma rodada em 10/09/2026.
    """
    guardado: list[str] = []

    def _guarda(m: re.Match) -> str:
        guardado.append(m.group(2))
        return f"\x00{len(guardado) - 1}\x00"

    # 1. tira o código de circulação, 2. escapa, 3. marca, 4. devolve o código escapado
    esc = html.escape(_CODE.sub(_guarda, txt), quote=False)
    esc = _LINK.sub(lambda m: f'<a href="{html.escape(m.group(2), quote=True)}"'
                              f' rel="noopener">{m.group(1)}</a>', esc)
    esc = _BOLD.sub(r"<strong>\1</strong>", esc)
    esc = _ITAL.sub(r"<em>\1</em>", esc)
    return re.sub(r"\x00(\d+)\x00",
                  lambda m: "<code>" + html.escape(guardado[int(m.group(1))], quote=False)
                            + "</code>", esc)


def _celulas(linha: str) -> list[str]:
    linha = linha.strip()
    if linha.startswith("|"):
        linha = linha[1:]
    if linha.endswith("|"):
        linha = linha[:-1]
    return [c.strip() for c in linha.split("|")]


def render(md: str) -> str:
    """Markdown para HTML. Devolve fragmento, sem body nem wrapper."""
    linhas = md.replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(linhas)

    while i < n:
        linha = linhas[i]

        # bloco de código cercado: conteúdo literal, sem marcação inline
        m = _FENCE.match(linha.strip())
        if m:
            lang = m.group(1)
            i += 1
            corpo = []
            while i < n and not _FENCE.match(linhas[i].strip()):
                corpo.append(linhas[i])
                i += 1
            i += 1  # consome a cerca de fechamento, se houver
            cls = f' class="lang-{html.escape(lang, quote=True)}"' if lang else ""
            out.append(f'<pre tabindex="0"><code{cls}>'
                       + html.escape("\n".join(corpo), quote=False) + "</code></pre>")
            continue

        # tabela: linha com | seguida de linha separadora
        if "|" in linha and i + 1 < n and _SEP.match(linhas[i + 1].strip()):
            cab = _celulas(linha)
            i += 2
            corpo = []
            while i < n and "|" in linhas[i] and linhas[i].strip():
                corpo.append(_celulas(linhas[i]))
                i += 1
            th = "".join(f"<th>{_inline(c)}</th>" for c in cab)
            trs = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in ln) + "</tr>"
                          for ln in corpo)
            out.append('<div class="tw" tabindex="0" role="group" aria-label="Tabela do documento">'
                       f"<table><tr>{th}</tr>{trs}</table></div>")
            continue

        # título
        m = re.match(r"^(#{1,6})\s+(.*)$", linha)
        if m:
            nivel = min(len(m.group(1)) + 2, 6)  # h1 do doc vira h3 dentro do painel
            out.append(f"<h{nivel}>{_inline(m.group(2).strip())}</h{nivel}>")
            i += 1
            continue

        # regra horizontal
        if re.match(r"^\s*([-*_])\s*(\1\s*){2,}$", linha):
            out.append("<hr>")
            i += 1
            continue

        # citação
        if linha.lstrip().startswith(">"):
            corpo = []
            while i < n and linhas[i].lstrip().startswith(">"):
                corpo.append(linhas[i].lstrip()[1:].lstrip())
                i += 1
            out.append("<blockquote>" + _inline(" ".join(corpo)) + "</blockquote>")
            continue

        # lista
        m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", linha)
        if m:
            ordenada = not m.group(2)[0] in "-*+"
            itens = []
            while i < n:
                mm = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", linhas[i])
                if not mm:
                    # continuação indentada do item anterior
                    if itens and linhas[i].startswith(("  ", "\t")) and linhas[i].strip():
                        itens[-1] += " " + linhas[i].strip()
                        i += 1
                        continue
                    break
                itens.append(mm.group(3).strip())
                i += 1
            tag = "ol" if ordenada else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in itens) + f"</{tag}>")
            continue

        # linha em branco
        if not linha.strip():
            i += 1
            continue

        # parágrafo: junta até a próxima linha em branco ou início de outro bloco
        corpo = []
        while i < n and linhas[i].strip():
            l = linhas[i]
            if (_FENCE.match(l.strip()) or re.match(r"^#{1,6}\s", l)
                    or re.match(r"^(\s*)([-*+]|\d+[.)])\s+", l) or l.lstrip().startswith(">")
                    or ("|" in l and i + 1 < n and _SEP.match(linhas[i + 1].strip()))):
                break
            corpo.append(l.strip())
            i += 1
        if corpo:
            out.append("<p>" + _inline(" ".join(corpo)) + "</p>")

    return "\n".join(out)


# ------------------------------------------------------------------------------- embutidos

def _painel(rotulo: str, rel: str, caminho: pathlib.Path) -> str:
    """Um <details> com o conteúdo do arquivo dentro. Markdown renderiza, resto vira <pre>."""
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    if caminho.suffix.lower() in {".md", ".markdown"}:
        corpo = render(texto)
    else:
        lang = caminho.suffix.lstrip(".") or "txt"
        corpo = (f'<pre tabindex="0"><code class="lang-{html.escape(lang, quote=True)}">'
                 + html.escape(texto, quote=False) + "</code></pre>")
    linhas = texto.count("\n") + 1
    return (
        '<details class="doc">'
        f'<summary><span class="docname">{rotulo}</span>'
        f'<span class="docmeta">{linhas} linhas · {rel}</span></summary>'
        f'<div class="docbody">{corpo}</div>'
        "</details>"
    )


def escolher_fonte(aqui: pathlib.Path) -> pathlib.Path | None:
    cands = [p for p in aqui.glob("*.html") if not p.name.endswith(".artifact.html")]
    return cands[0] if len(cands) == 1 else None



# O publish do Artifact monta um <html> proprio em volta deste arquivo e NAO carrega o lang do
# documento: uma pagina em portugues e anunciada como ingles pelo leitor de tela (WCAG 3.1.1).
# O HTML fonte tem lang="pt-BR" e abre certo no navegador local, entao a correcao pertence a
# este derivador, nao ao template. Medido em 20/09/2026: axe acusa html-has-lang na montagem
# reproduzida do publish, e some com este bloco.
AFIRMA_LANG = (
    "<script>/* o wrapper do publish nao carrega o lang do documento */\n"
    "if(document.documentElement.lang!=='pt-BR'){document.documentElement.lang='pt-BR';}\n"
    "</script>\n"
)


def afirmar_lang(html: str) -> str:
    if "documentElement.lang" in html:
        return html
    return html + AFIRMA_LANG


def main() -> int:
    aqui = pathlib.Path(__file__).resolve().parent
    if len(sys.argv) > 1:
        fonte = pathlib.Path(sys.argv[1]).resolve()
    else:
        fonte = escolher_fonte(aqui)
        if fonte is None:
            print("ERRO: passe o caminho do guia, não achei um único *.html aqui", file=sys.stderr)
            return 2
    if not fonte.is_file():
        print(f"ERRO: não achei {fonte}", file=sys.stderr)
        return 2

    base = fonte.parent
    texto_html = fonte.read_text(encoding="utf-8")
    faltando, embutidas, docs = [], 0, 0

    def troca_img(m: re.Match) -> str:
        nonlocal embutidas
        rel = m.group(2)
        if rel.startswith(("data:", "http://", "https://", "//")):
            return m.group(0)
        caminho = (base / rel).resolve()
        if not caminho.is_file():
            faltando.append(rel)
            return m.group(0)
        mime = mimetypes.guess_type(caminho.name)[0] or "application/octet-stream"
        dado = base64.b64encode(caminho.read_bytes()).decode("ascii")
        embutidas += 1
        return f"{m.group(1)}data:{mime};base64,{dado}{m.group(3)}"

    def troca_doc(m: re.Match) -> str:
        nonlocal docs
        rel, rotulo = m.group(1), m.group(2)
        if rel.startswith(("data:", "http://", "https://", "//", "#")):
            return m.group(0)
        caminho = (base / rel).resolve()
        if not caminho.is_file():
            faltando.append(rel)
            return m.group(0)
        if caminho.suffix.lower() not in TEXTO:
            faltando.append(f"{rel} (extensão não embutível)")
            return m.group(0)
        docs += 1
        return _painel(rotulo, rel, caminho)

    saida_html = EMBRULHO.sub("", DOC.sub(troca_doc, SRC.sub(troca_img, texto_html))).strip() + "\n"
    saida = fonte.with_name(fonte.stem + ".artifact.html")
    tamanho_mb = len(saida_html.encode("utf-8")) / (1024 * 1024)
    if tamanho_mb > LIMITE_MB:
        print(f"ERRO: {tamanho_mb:.1f} MB passa do limite de {LIMITE_MB} MB do Artifact. "
              "Reduza as imagens ou embuta menos documentos.", file=sys.stderr)
        return 2
    saida.write_text(afirmar_lang(saida_html), encoding="utf-8")
    print(f"{saida.name}: {embutidas} imagem(ns), {docs} documento(s) embutido(s), "
          f"{tamanho_mb:.2f} MB")
    if faltando:
        print("AVISO: não encontrados, mantidos com caminho relativo:", file=sys.stderr)
        for f in faltando:
            print("  " + f, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
