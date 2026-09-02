#!/usr/bin/env python3
"""Gera a versão publicável do guia vivo, com as imagens embutidas em base64.

Por que existe: o CSP dos Artifacts do Claude bloqueia host externo e não serve caminho
relativo, então `img/foo.jpg` não carrega lá. A fonte da verdade continua sendo o HTML com
caminho relativo, que abre bem no repo e no navegador local. Este script só deriva a cópia
publicável, que o .gitignore do projeto ignora de propósito: derivado versionado é como duas
cópias divergem.

Uso:
    python3 build_artifact.py [GUIA.html]

Sem argumento, usa o único *.html da própria pasta que não termina em .artifact.html.
Saída: <nome>.artifact.html ao lado da fonte.
Sai 0 se gerou, 1 se alguma imagem faltou (gera mesmo assim e lista), 2 se não achou a fonte
ou o resultado passou de 16 MB.
"""

import base64
import mimetypes
import pathlib
import re
import sys

LIMITE_MB = 16
SRC = re.compile(r'(<img\b[^>]*\bsrc=")([^"]+)(")', re.IGNORECASE)
# A fonte é um documento completo (html lang, head, body), que é o que o navegador local e o
# cão-guia esperam. O Artifact embrulha o conteúdo no esqueleto dele, então o derivado sai sem
# doctype, html, head e body. Só as tags de embrulho caem, o conteúdo fica inteiro.
EMBRULHO = re.compile(r"<!doctype[^>]*>|</?html[^>]*>|</?head>|</?body[^>]*>", re.IGNORECASE)


def escolher_fonte(aqui: pathlib.Path) -> pathlib.Path | None:
    cands = [p for p in aqui.glob("*.html") if not p.name.endswith(".artifact.html")]
    return cands[0] if len(cands) == 1 else None


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
    html = fonte.read_text(encoding="utf-8")
    faltando, embutidas = [], 0

    def troca(m: re.Match) -> str:
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

    saida_html = EMBRULHO.sub("", SRC.sub(troca, html)).strip() + "\n"
    saida = fonte.with_name(fonte.stem + ".artifact.html")
    tamanho_mb = len(saida_html.encode("utf-8")) / (1024 * 1024)
    if tamanho_mb > LIMITE_MB:
        print(f"ERRO: {tamanho_mb:.1f} MB passa do limite de {LIMITE_MB} MB do Artifact. "
              "Reduza as imagens antes de publicar.", file=sys.stderr)
        return 2
    saida.write_text(saida_html, encoding="utf-8")
    print(f"{saida.name}: {embutidas} imagem(ns) embutida(s), {tamanho_mb:.2f} MB")
    if faltando:
        print("AVISO: imagens não encontradas, mantidas com caminho relativo:", file=sys.stderr)
        for f in faltando:
            print("  " + f, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
