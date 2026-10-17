#!/usr/bin/env bash
# Monta o radio-pirata com uma prancheta lida de volta que NAO fecha com a aprovacao: a marca
# pr-3 (a premissa vetada) falta na leitura, e a aprovacao gravada conta um veto.
set -euo pipefail
RAIZ="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cp -R "$RAIZ/evals/fixtures/radio-pirata/." .
mkdir -p docs/prancheta-fase-2
cp "$RAIZ/evals/fixtures/prancheta-exemplo.json" docs/prancheta-fase-2/conteudo.json
python3 - "$RAIZ/evals/fixtures/prancheta-exemplo-estado.json" <<'PY'
import json, sys, pathlib
e = json.load(open(sys.argv[1], encoding="utf-8"))
del e["marcas"]["pr-3"]   # some da leitura; a aprovacao segue contando um veto
base = pathlib.Path("docs/prancheta-fase-2/lido")
for col in ("marcas", "estado", "chat"):
    (base / col).mkdir(parents=True, exist_ok=True)
    for doc, corpo in e[col].items():
        (base / col / f"{doc}.json").write_text(json.dumps(corpo, ensure_ascii=False, indent=1), encoding="utf-8")
PY
echo "scaffold: radio-pirata com docs/prancheta-fase-2/lido (falta pr-3, a leitura nao fecha)"
