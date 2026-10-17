#!/usr/bin/env bash
# Monta o radio-pirata com um conteudo de prancheta em que um fato perdeu a fonte.
set -euo pipefail
RAIZ="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cp -R "$RAIZ/evals/fixtures/radio-pirata/." .
mkdir -p docs/prancheta-fase-2
python3 - "$RAIZ/evals/fixtures/prancheta-exemplo.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1], encoding="utf-8"))
del c["fatos"][2]["fonte"]   # "O app do iPhone le a biblioteca pelo tailnet"
open("docs/prancheta-fase-2/conteudo.json", "w", encoding="utf-8").write(json.dumps(c, ensure_ascii=False, indent=1))
PY
echo "scaffold: radio-pirata com fato sem fonte em docs/prancheta-fase-2/conteudo.json"
