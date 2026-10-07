"""Testes do progresso.py: a data repetida na prova e o --substituir-prova.

Os dois nasceram do mesmo defeito, visto em 07/10/2026: quatro provas de um guia saíram
"Provado em 07/10/2026: 07/10/2026: ...", porque o texto passado em --prova já começava com a
data, e nada no script trocava uma prova registrada. Os testes rodam o script como o Claude
roda, pela linha de comando, num guia temporário com a marcação do template.

Rodar: python3 -m unittest discover -s tests   (na raiz da skill, só stdlib, Python 3.9 ou mais)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "progresso.py"
sys.path.insert(0, str(RAIZ / "scripts"))
import progresso  # noqa: E402

# A marcação de etapa é a que o novo_projeto.py gera a partir de assets/guia/fase.template.html.
GUIA = """<!doctype html>
<html lang="pt-BR">
<body>
<p id="status-atual" data-v="01/10/2026"><strong>01/10/2026: projeto aberto.</strong></p>
<section class="phase" id="f1">
 <div class="phead">
  <label class="pdone"><input type="checkbox" data-done="f1">Fase concluída</label>
 </div>
 <div class="checks">
  <label><input type="checkbox" id="e-f1-1">Comparar as duas opções<small class="pq">Pronto quando: tabela comparativa no HANDOFF</small></label>
  <label><input type="checkbox" id="e-f1-2">Decisão registrada no HANDOFF<small class="pq">Pronto quando: tabela de decisões</small><small class="quem">com Bera</small></label>
 </div>
</section>
<footer>Guia vivo, atualizado pela última vez em <span id="atualizado">01/10/2026</span>.</footer>
</body>
</html>
"""


class Guia(unittest.TestCase):
    """Um guia temporário por teste."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.guia = Path(tmp.name) / "guia.html"
        self.guia.write_text(GUIA, encoding="utf-8")

    def rodar(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        return subprocess.run([sys.executable, str(SCRIPT), str(self.guia), *args],
                              capture_output=True, encoding="utf-8", env=env)

    def marcar(self, etapa, prova, *extra, data="07/10/2026"):
        r = self.rodar("--marcar", etapa, "--prova", prova, "--carimbar", data, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def html(self):
        return self.guia.read_text(encoding="utf-8")

    def provas(self, etapa):
        label = re.search(r'id="' + etapa + r'"[^>]*>(.*?)</label>', self.html(), re.DOTALL)
        return re.findall(r'<small class="prova"[^>]*>(.*?)</small>', label.group(1), re.DOTALL)

    def marcada(self, etapa):
        return " checked" in re.search(r'<input\b[^>]*\bid="' + etapa + r'"[^>]*>', self.html()).group(0)

    def com_prova_antiga(self, etapa, nota):
        """Grava à mão o estado de partida do teste, como o defeito deixou o guia."""
        html = self.html().replace(f'id="{etapa}">', f'id="{etapa}" checked>', 1)
        fim = html.index("</label>", html.index(f'id="{etapa}"'))
        self.guia.write_text(html[:fim] + nota + html[fim:], encoding="utf-8")


class DataRepetida(Guia):
    """A prova que já começa com a data do carimbo perde a repetição, com AVISO."""

    def test_prova_que_comeca_com_a_data_perde_a_repeticao(self):
        r = self.marcar("e-f1-1", "07/10/2026: tabela no HANDOFF")
        self.assertEqual(self.provas("e-f1-1"), ["Provado em 07/10/2026: tabela no HANDOFF"])
        self.assertTrue(self.marcada("e-f1-1"))
        self.assertIn('AVISO: --prova começava com "07/10/2026:"', r.stderr)
        self.assertIn("registrou a prova de e-f1-1, sem a data repetida no começo do texto", r.stdout)

    def test_sem_carimbar_vale_a_data_de_hoje(self):
        hoje = progresso.hoje()
        r = self.rodar("--marcar", "e-f1-1", "--prova", f"{hoje}: tabela no HANDOFF")
        if progresso.hoje() != hoje:
            self.skipTest("o dia virou no meio do teste")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.provas("e-f1-1"), [f"Provado em {hoje}: tabela no HANDOFF"])

    def test_variacoes_do_mesmo_comeco_saem(self):
        for texto in ("07/10/2026:tabela", "  07/10/2026 : tabela", "07/10/2026: 07/10/2026: tabela",
                      "Provado em 07/10/2026: tabela", "provado em 07/10/2026: 07/10/2026: tabela"):
            with self.subTest(texto=texto):
                self.assertEqual(progresso.sem_data_repetida(texto, "07/10/2026"), ("tabela", True))

    def test_data_que_nao_repete_o_carimbo_fica(self):
        for texto in ("06/10/2026: tabela", "schema aplicado em 07/10/2026: saída 0",
                      "07/10/2026 10:00: deploy", "07/10/2026 sem dois-pontos"):
            with self.subTest(texto=texto):
                self.assertEqual(progresso.sem_data_repetida(texto, "07/10/2026"), (texto, False))

    def test_prova_sem_texto_e_recusada_sem_gravar(self):
        antes = self.html()
        for prova, motivo in (("07/10/2026:", "--prova sem texto depois de tirar a data repetida"),
                              ("   ", "--prova sem texto. Sem evidência")):
            with self.subTest(prova=prova):
                r = self.rodar("--marcar", "e-f1-1", "--prova", prova, "--carimbar", "07/10/2026")
                self.assertEqual(r.returncode, 2)
                self.assertIn(motivo, r.stderr)
                self.assertEqual(self.html(), antes)

    def test_json_continua_valido_com_o_aviso(self):
        r = self.marcar("e-f1-1", "07/10/2026: tabela no HANDOFF", "--json")
        saida = json.loads(r.stdout)
        self.assertIn("registrou a prova de e-f1-1, sem a data repetida no começo do texto",
                      saida["mudancas"])
        self.assertIn("AVISO: --prova", r.stderr)


class SubstituirProva(Guia):
    """Prova registrada fica, e só o --substituir-prova a troca."""

    def test_sem_a_flag_a_prova_registrada_fica(self):
        self.marcar("e-f1-1", "primeira prova")
        r = self.marcar("e-f1-1", "segunda prova", data="08/10/2026")
        self.assertIn("e-f1-1 já tinha prova registrada, mantida", r.stdout)
        self.assertEqual(self.provas("e-f1-1"), ["Provado em 07/10/2026: primeira prova"])

    def test_com_a_flag_a_prova_e_trocada(self):
        self.marcar("e-f1-1", "primeira prova")
        self.marcar("e-f1-2", "decisão na tabela")
        r = self.marcar("e-f1-1", "segunda prova", "--substituir-prova", data="08/10/2026")
        self.assertIn("substituiu a prova de e-f1-1", r.stdout)
        self.assertEqual(self.provas("e-f1-1"), ["Provado em 08/10/2026: segunda prova"])
        self.assertTrue(self.marcada("e-f1-1"))
        self.assertEqual(self.provas("e-f1-2"), ["Provado em 07/10/2026: decisão na tabela"])
        self.assertEqual(self.rodar("--listar").returncode, 0)

    def test_corrige_a_prova_com_a_data_duplicada(self):
        nota = '<small class="prova">Provado em 07/10/2026: 07/10/2026: tabela no HANDOFF</small>'
        for prova in ("tabela no HANDOFF", "07/10/2026: tabela no HANDOFF"):
            with self.subTest(prova=prova):
                self.guia.write_text(GUIA, encoding="utf-8")
                self.com_prova_antiga("e-f1-1", nota)
                r = self.marcar("e-f1-1", prova, "--substituir-prova")
                self.assertIn("substituiu a prova de e-f1-1", r.stdout)
                self.assertEqual(self.provas("e-f1-1"), ["Provado em 07/10/2026: tabela no HANDOFF"])

    def test_prova_antiga_em_mais_de_uma_linha_tambem_sai(self):
        self.com_prova_antiga("e-f1-1", '<small class="prova">Provado em 07/10/2026: linha um\nlinha dois</small>')
        self.marcar("e-f1-1", "uma linha só", "--substituir-prova")
        self.assertEqual(self.provas("e-f1-1"), ["Provado em 07/10/2026: uma linha só"])

    def test_prova_falsa_desmarcada_e_trocada_ao_remarcar(self):
        self.marcar("e-f1-1", "prova falsa")
        self.assertEqual(self.rodar("--desmarcar", "e-f1-1").returncode, 0)
        self.assertFalse(self.marcada("e-f1-1"))
        self.marcar("e-f1-1", "prova real", "--substituir-prova", data="09/10/2026")
        self.assertTrue(self.marcada("e-f1-1"))
        self.assertEqual(self.provas("e-f1-1"), ["Provado em 09/10/2026: prova real"])

    def test_etapa_sem_prova_registra_e_avisa(self):
        r = self.marcar("e-f1-2", "decisão na tabela", "--substituir-prova")
        self.assertIn("registrou a prova de e-f1-2, sem prova anterior para substituir", r.stdout)
        self.assertEqual(self.provas("e-f1-2"), ["Provado em 07/10/2026: decisão na tabela"])

    def test_prova_fora_do_formato_e_recusada(self):
        self.com_prova_antiga("e-f1-1", '<small class="prova" title="à mão">Provado em 07/10/2026: tabela</small>')
        r = self.marcar("e-f1-1", "outra tabela", "--substituir-prova")
        self.assertIn("recusado: a prova de e-f1-1 está fora do formato do script", r.stdout)
        self.assertEqual(self.provas("e-f1-1"), ["Provado em 07/10/2026: tabela"])

    def test_sem_marcar_e_recusado_sem_gravar(self):
        antes = self.html()
        for args in (("--substituir-prova",), ("--substituir-prova", "--prova", "tabela")):
            with self.subTest(args=args):
                r = self.rodar(*args)
                self.assertEqual(r.returncode, 2)
                self.assertIn("--substituir-prova vai junto com --marcar", r.stderr)
                self.assertEqual(self.html(), antes)

    def test_prova_ainda_substitui_a_declaracao(self):
        self.assertEqual(self.rodar("--declarar", "e-f1-2", "--carimbar", "06/10/2026").returncode, 0)
        r = self.marcar("e-f1-2", "decisão na tabela")
        self.assertIn("registrou a prova de e-f1-2, substituindo a declaração", r.stdout)
        self.assertNotIn('class="decl"', self.html())
        self.assertEqual(self.provas("e-f1-2"), ["Provado em 07/10/2026: decisão na tabela"])


if __name__ == "__main__":
    unittest.main()
