#!/usr/bin/env bash
# Monta o projeto radio-pirata no diretorio de trabalho da rodada, a partir da fixture da skill.
set -euo pipefail
FIXTURE="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}/evals/fixtures/radio-pirata"
if [ ! -d "$FIXTURE" ]; then
  echo "scaffold: fixture nao encontrada em $FIXTURE" >&2
  exit 1
fi
cp -R "$FIXTURE/." .
echo "scaffold: radio-pirata montado, $(find . -name 'guia-*.html' | head -1)"
