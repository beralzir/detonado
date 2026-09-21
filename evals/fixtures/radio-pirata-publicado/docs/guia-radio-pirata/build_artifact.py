#!/usr/bin/env python3
"""Invoca o build_artifact.py da skill detonado.

Não é cópia, de propósito: cópia de script envelhece e diverge da skill. Se a skill não
estiver instalada, este arquivo diz onde ela deveria estar em vez de falhar torto.
"""
import pathlib
import runpy
import sys

ALVO = pathlib.Path.home() / ".claude" / "skills" / "detonado" / "scripts" / "build_artifact.py"

if not ALVO.is_file():
    sys.exit(f"ERRO: skill detonado não encontrada em {ALVO}.\n"
             "Instale pelo starter-kit, ou rode o script da skill direto pelo caminho dela.")
sys.argv[0] = str(ALVO)
runpy.run_path(str(ALVO), run_name="__main__")
