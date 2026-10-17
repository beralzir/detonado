"""Testes do prancheta.py: o gate do conteúdo, a leitura do estado e a cascata dos marcos.

Cada teste planta um erro no JSON de exemplo (evals/fixtures/prancheta-exemplo.json) ou no
estado lido de volta (prancheta-exemplo-estado.json) e confere que o script reprova com a saída
certa e sem escrever nada. Os testes rodam o script como o Claude roda, pela linha de comando.
A paridade da cascata compara a conta do Python com a do JS do template, pelo node, quando ele
existe na máquina.

Rodar: python3 -m unittest discover -s tests   (na raiz da skill, só stdlib, Python 3.9 ou mais)
"""

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "prancheta.py"
TEMPLATE = RAIZ / "assets" / "guia" / "prancheta.template.html"
TOKENS = RAIZ / "assets" / "guia" / "tokens"
EXEMPLO = json.loads((RAIZ / "evals" / "fixtures" / "prancheta-exemplo.json").read_text(encoding="utf-8"))
ESTADO = json.loads((RAIZ / "evals" / "fixtures" / "prancheta-exemplo-estado.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(RAIZ / "scripts"))
import prancheta  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="prancheta-"))
        self.saida = self.tmp / "docs" / "prancheta-fase-2" / "prancheta-fase-2.html"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def roda(self, conteudo=None, estado=None, extra=(), nome="fase-2"):
        c = self.tmp / "conteudo.json"
        c.write_text(json.dumps(EXEMPLO if conteudo is None else conteudo, ensure_ascii=False), encoding="utf-8")
        args = [sys.executable, str(SCRIPT), "--nome", nome, "--dir", str(self.tmp), "--conteudo", str(c), *extra]
        if estado is not None:
            pasta = estado if isinstance(estado, Path) else self.lido(estado, nome)
            args += ["--estado", str(pasta)]
        return subprocess.run(args, capture_output=True, text=True)

    def lido(self, estado, nome="fase-2", pasta="lido"):
        """Grava o estado como o out_dir do ArtifactData grava, em
        docs/prancheta-<nome>/<pasta>/<coleção>/<id>.json, com a hora da leitura (lido_em da
        fixture) como hora dos arquivos: o --estado lê a hora da leitura pelos arquivos."""
        base = self.tmp / "docs" / f"prancheta-{nome}" / pasta
        shutil.rmtree(base, ignore_errors=True)
        for col in ("marcas", "estado", "chat"):
            (base / col).mkdir(parents=True)
            for i, corpo in (estado.get(col) or {}).items():
                (base / col / f"{i}.json").write_text(json.dumps(corpo, ensure_ascii=False), encoding="utf-8")
        if estado.get("lido_em"):
            t = datetime.fromisoformat(estado["lido_em"].replace("Z", "+00:00")).timestamp()
            for arq in base.rglob("*.json"):
                os.utime(str(arq), (t, t))
        return base

    def reprova(self, conteudo, trecho, estado=None, rc=2):
        r = self.roda(conteudo, estado)
        self.assertEqual(r.returncode, rc, r.stdout + r.stderr)
        self.assertIn(trecho, r.stdout + r.stderr)
        self.assertFalse(self.saida.exists(), "reprovou e mesmo assim escreveu")
        return r

    def dados(self):
        html = self.saida.read_text(encoding="utf-8")
        m = re.search(r'<script type="application/json" id="prancheta-dados">(.*?)</script>', html, re.S)
        return html, json.loads(m.group(1))


def mexe(f):
    """Cópia funda do exemplo, com a alteração aplicada."""
    c = copy.deepcopy(EXEMPLO)
    f(c)
    return c


class TestConteudo(Base):
    def test_exemplo_gera_pagina_completa(self):
        r = self.roda()
        self.assertEqual(r.returncode, 0, r.stderr)
        html, d = self.dados()
        self.assertNotIn("{{", html)
        self.assertEqual(d["modo"], "aberto")
        self.assertIsNone(d["estado"])
        self.assertEqual(d["chave_local"], "detonado:prancheta:radio-pirata:fase-2")
        self.assertEqual([f["rotulo"] for f in d["conteudo"]["fases"]], ["F0", "F1", "F2"])
        # os dois temas, como o Artifact pede, e as séries validadas nos dois
        self.assertIn('@media (prefers-color-scheme: dark){:root:not([data-theme="light"])', html)
        self.assertIn(':root[data-theme="dark"]', html)
        self.assertEqual(html.count("--serie-1"), 3 + html.count("var(--serie-1)"))

    def test_fixture_de_estado_traz_a_versao_do_exemplo(self):
        g, c = prancheta.valida_conteudo(copy.deepcopy(EXEMPLO))
        self.assertEqual(ESTADO["estado"]["aprovacao"]["conteudo"], prancheta.versao_conteudo(c),
                         "o exemplo mudou: grave a versão nova na fixture de estado")

    def test_dry_run_nao_escreve(self):
        r = self.roda(extra=("--dry-run",))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[dry-run]", r.stdout)
        self.assertFalse(self.saida.exists())

    def test_fato_sem_fonte(self):
        self.reprova(mexe(lambda c: c["fatos"][0].pop("fonte")), "fato sem fonte é opinião")

    def test_fato_com_status_fora_da_lista(self):
        self.reprova(mexe(lambda c: c["fatos"][1].update(status="provavel")), "`status` precisa ser")

    def test_passo_sem_pronto(self):
        self.reprova(mexe(lambda c: c["fases"][1]["passos"][0].pop("pronto")), "não tem como ser aprovado")

    def test_passo_com_pronto_em_branco(self):
        self.reprova(mexe(lambda c: c["fases"][1]["passos"][0].update(pronto="   ")), "`pronto` está vazia")

    def test_chave_desconhecida_com_dica(self):
        self.reprova(mexe(lambda c: c.update(pedido=[])), "chave desconhecida `pedido`, talvez `pedidos`")

    def test_cinco_perguntas(self):
        cinco = [{"titulo": f"P{i}", "recomendacao": "sim"} for i in range(5)]
        self.reprova(mexe(lambda c: c.update(perguntas=cinco)), "o chat leva até 4")

    def test_pergunta_sem_recomendacao(self):
        self.reprova(mexe(lambda c: c["perguntas"][0].pop("recomendacao")), "sem a sua leitura")

    def test_id_repetido_entre_passo_e_premissa(self):
        self.reprova(mexe(lambda c: c["premissas"][0].update(id="f1-1")), "id `f1-1` repetido")

    def test_id_que_colide_com_marco(self):
        self.reprova(mexe(lambda c: c["premissas"][0].update(id="m-f1")), "id do marco da fase `f1`")

    def test_opcao_fora_sem_porque(self):
        self.reprova(mexe(lambda c: c["opcoes"][1].pop("porque_fora")), "precisa de `porque_fora`")

    def test_depois_de_cita_fase_seguinte(self):
        self.reprova(mexe(lambda c: c["fases"][1]["agenda"].update(depois_de=["f2"])), "só anda para a frente")

    def test_agenda_e_quando_juntos(self):
        self.reprova(mexe(lambda c: c["fases"][1].update(quando="18 a 19/10")), "tire o `quando`")

    def test_prazo_que_nao_existe(self):
        self.reprova(mexe(lambda c: c["fases"][2]["agenda"].update(prazo="ferias")), "`prazo` cita `ferias`")

    def test_prazo_estourado_na_propria_recomendacao(self):
        self.reprova(mexe(lambda c: c["linha_do_tempo"]["datas_fixas"][0].update(data="2026-10-21")),
                     "já termina depois do prazo")

    def test_segmento_com_quem_errado(self):
        self.reprova(mexe(lambda c: c["fases"][0]["agenda"]["segmentos"][0].update(quem="bera")),
                     "`quem` precisa ser claude ou voce")

    def test_url_que_nao_e_http(self):
        self.reprova(mexe(lambda c: c["fontes"][0].update(url="javascript:alert(1)")), "http:// ou https://")

    def test_injecao_de_script_vira_texto(self):
        ataque = "</script><script>alert(1)</script><!--"
        r = self.roda(mexe(lambda c: c.update(lede=ataque)))
        self.assertEqual(r.returncode, 0, r.stderr)
        html, d = self.dados()
        self.assertNotIn("<script>alert", html)
        self.assertEqual(d["conteudo"]["lede"], ataque)

    def test_nome_fora_do_formato(self):
        r = self.roda(nome="Fase 2")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--nome", r.stderr)

    def test_sem_dir_nao_roda(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--nome", "x"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("--dir", r.stderr)


class TestEstado(Base):
    def estado(self, f=None):
        e = copy.deepcopy(ESTADO)
        if f:
            f(e)
        return e

    def test_aprovado_gera_versao_so_leitura_e_resumo(self):
        r = self.roda(estado=self.estado())
        self.assertEqual(r.returncode, 0, r.stderr)
        html, d = self.dados()
        self.assertEqual(d["modo"], "aprovado")
        self.assertEqual(set(d["estado"]["marcas"]), {"f1-2", "f0-2", "m-f1", "op-2", "pr-3"})
        self.assertIn("Aprovada em 17/10/2026", r.stdout)
        self.assertIn("F2: 21 a 22/10 (era 20 a 21/10), cascata de F1", r.stdout)
        self.assertIn("Incluir · Opção · Aviso quando o servidor cair (fora da recomendação)", r.stdout)
        self.assertIn("2. Nome do serviço: sem resposta registrada", r.stdout)
        self.assertNotIn("F0-2", r.stdout, "marca igual à recomendação, sem nota, não é mudança")

    def test_marca_depois_da_aprovacao_desatualiza(self):
        e = self.estado(lambda e: e["marcas"]["m-f1"].update(em="2026-10-17T18:20:00.000Z"))
        r = self.reprova(None, "APROVAÇÃO DESATUALIZADA", estado=e, rc=3)
        self.assertIn("m-f1", r.stdout)

    def test_sem_aprovacao_nao_escreve(self):
        self.reprova(None, "SEM APROVAÇÃO", estado=self.estado(lambda e: e["estado"].pop("aprovacao")), rc=3)

    def test_aprovacao_desfeita_nao_escreve(self):
        self.reprova(None, "Aprovação desfeita",
                     estado=self.estado(lambda e: e["estado"]["aprovacao"].update(aprovado=False)), rc=3)

    def test_id_que_nao_existe(self):
        e = self.estado(lambda e: e["marcas"].update({"zz-9": {"tipo": "passo", "valor": "manter", "em": "2026-10-17T18:00:00Z"}}))
        self.reprova(None, "marcas/zz-9: id que não existe", estado=e)

    def test_valor_invalido(self):
        self.reprova(None, "inválido para passo", estado=self.estado(lambda e: e["marcas"]["f1-2"].update(valor="talvez")))

    def test_atalho_fora_da_lista(self):
        self.reprova(None, "`atalhos` fora da lista",
                     estado=self.estado(lambda e: e["marcas"]["f1-2"].update(atalhos=["Qualquer coisa"])))

    def test_tipo_trocado(self):
        self.reprova(None, "e o item é passo", estado=self.estado(lambda e: e["marcas"]["f1-2"].update(tipo="premissa")))

    def test_marco_fora_do_limite(self):
        self.reprova(None, "inteiro de -30 a 30", estado=self.estado(lambda e: e["marcas"]["m-f1"].update(valor=99)))

    def test_le_pasta_do_out_dir_com_e_sem_envelope(self):
        pasta = self.tmp / "docs" / "prancheta-fase-2" / "lido"
        for col in ("marcas", "estado", "chat"):
            (pasta / col).mkdir(parents=True)
        for i, m in ESTADO["marcas"].items():
            corpo = {"id": i, "version": 3, "data": m} if i.startswith("f") else m
            (pasta / "marcas" / f"{i}.json").write_text(json.dumps(corpo), encoding="utf-8")
        for k, v in ESTADO["estado"].items():
            (pasta / "estado" / f"{k}.json").write_text(json.dumps(v), encoding="utf-8")
        for k, v in ESTADO["chat"].items():
            (pasta / "chat" / f"{k}.json").write_text(json.dumps(v), encoding="utf-8")
        r = self.roda(estado=pasta)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Aprovada em", r.stdout)

    # Auditoria da rodada trava (17/10/2026): uma leitura montada à mão fora de lido*/ passava
    # pela trava, que só protege lido*/, e pelo --estado, que aceitava qualquer pasta ou JSON.
    def test_leitura_fora_de_lido_reprova(self):
        boa = self.lido(self.estado())
        outra = self.tmp / "docs" / "prancheta-fase-2" / "leitura"
        fora = self.tmp / "lido"
        de_outra = self.tmp / "docs" / "prancheta-rodada-1" / "lido"
        for destino in (outra, fora, de_outra):
            shutil.copytree(str(boa), str(destino))
        arquivo = self.tmp / "estado.json"
        arquivo.write_text(json.dumps(self.estado(), ensure_ascii=False), encoding="utf-8")
        atalho = self.tmp / "docs" / "prancheta-fase-2" / "lido-3"
        os.symlink(str(fora), str(atalho))
        for pasta in (outra, fora, de_outra, arquivo, atalho):
            with self.subTest(pasta=str(pasta.relative_to(self.tmp))):
                self.reprova(None, "não é uma leitura de volta desta prancheta", estado=pasta)

    def test_releitura_em_lido_2_vale(self):
        r = self.roda(estado=self.lido(self.estado(), pasta="lido-2"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Aprovada em", r.stdout)

    def test_versao_aprovada_nao_se_reabre(self):
        self.assertEqual(self.roda(estado=self.estado()).returncode, 0)
        r = self.roda()
        self.assertEqual(r.returncode, 2)
        self.assertIn("já é a versão aprovada", r.stderr)

    # Achados da auditoria de prompt de 17/10/2026: a aprovação tem de valer para o plano visto.
    def test_conteudo_mudou_depois_da_aprovacao(self):
        mudado = mexe(lambda c: c["fases"][1]["passos"][1].update(titulo="Subir, provar e medir"))
        self.reprova(mudado, "APROVAÇÃO DE OUTRA VERSÃO", estado=self.estado(), rc=3)

    def test_aprovacao_de_outra_prancheta(self):
        self.reprova(None, "APROVAÇÃO DE OUTRA VERSÃO", rc=3,
                     estado=self.estado(lambda e: e["estado"]["aprovacao"].update(nome="rodada-1")))

    def test_leitura_sem_marcas_nao_fecha(self):
        self.reprova(None, "a leitura não fecha com a aprovação", estado=self.estado(lambda e: e.update(marcas={})))

    def test_resumo_que_nao_fecha(self):
        self.reprova(None, "ajustes 3 na aprovação e 1 nas marcas lidas",
                     estado=self.estado(lambda e: e["estado"]["aprovacao"]["resumo"].update(ajustes=3)))

    def test_resposta_do_chat_depois_da_aprovacao_rotulada(self):
        r = self.roda(estado=self.estado())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("cópia simples da pasta (17/10/2026 às", r.stdout)
        self.assertIn("registrada depois da aprovação", r.stdout)


class TestCronograma(unittest.TestCase):
    LINHAS = [{"id": "a", "ini": 0, "dur": 1.0, "deps": []},
              {"id": "b", "ini": 1, "dur": 2.0, "deps": ["a"]},
              {"id": "c", "ini": 1, "dur": 1.5, "deps": ["a"]},
              {"id": "d", "ini": 3, "dur": 1.0, "deps": ["b", "c"]},
              {"id": "e", "ini": 0, "dur": 4.0, "deps": []}]
    VETORES = [{}, {"a": 2}, {"a": -1}, {"c": 3}, {"b": 1, "c": 2}, {"a": 1, "d": -1}, {"e": 5, "a": -2}]

    def test_adiar_empurra_as_que_dependem(self):
        r = prancheta.cronograma(self.LINHAS, {"a": 2})
        self.assertEqual(r["b"]["efetivo"], 2)
        self.assertEqual(r["d"]["efetivo"], 2)
        self.assertEqual(r["e"]["efetivo"], 0, "fase sem dependência não anda")
        self.assertEqual(r["b"]["causa"], "a")

    def test_antecipar_puxa(self):
        r = prancheta.cronograma(self.LINHAS, {"a": -1})
        self.assertEqual(r["d"]["ini"], 2)

    def test_duas_dependencias_vale_a_maior(self):
        r = prancheta.cronograma(self.LINHAS, {"b": 1, "c": 2})
        self.assertEqual(r["d"]["efetivo"], 2)
        self.assertEqual(r["d"]["causa"], "c")

    def test_periodo_em_texto(self):
        from datetime import date
        o = date(2026, 10, 30)
        self.assertEqual(prancheta.periodo_txt(o, 0, 0.5), "30/10")
        self.assertEqual(prancheta.periodo_txt(o, 0, 2), "30 a 31/10")
        self.assertEqual(prancheta.periodo_txt(o, 0, 2.5), "30/10 a 01/11")

    @unittest.skipUnless(shutil.which("node"), "node ausente: paridade com o JS não testada")
    def test_paridade_com_o_js_do_template(self):
        tpl = TEMPLATE.read_text(encoding="utf-8")
        m = re.search(r"// <cronograma>.*?\n(.*?)// </cronograma>", tpl, re.S)
        self.assertIsNotNone(m, "marcadores <cronograma> sumiram do template")
        js = m.group(1) + "\nconst L = " + json.dumps(self.LINHAS) + ", V = " + json.dumps(self.VETORES) + \
            ";\nconsole.log(JSON.stringify(V.map(v => cronograma(L, v))));"
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        do_js = json.loads(r.stdout)
        for v, saida_js in zip(self.VETORES, do_js):
            do_py = prancheta.cronograma(self.LINHAS, v)
            self.assertEqual(set(do_py), set(saida_js))
            for i in do_py:
                for k in ("proprio", "efetivo", "ini", "fim", "causa"):
                    self.assertEqual(do_py[i][k], saida_js[i][k], f"vetor {v}, fase {i}, campo {k}")


class TestTokens(unittest.TestCase):
    def variaveis(self, nome):
        return set(re.findall(r"(--[a-z0-9-]+)\s*:", (TOKENS / nome).read_text(encoding="utf-8")))

    def test_claro_tem_o_mesmo_contrato_do_escuro(self):
        self.assertEqual(self.variaveis("neutro-claro.css"), self.variaveis("neutro.css"))

    def test_tema_sem_serie_reprova(self):
        tmp = Path(tempfile.mkdtemp(prefix="tokens-"))
        try:
            (tmp / "tokens").mkdir()
            (tmp / "tokens" / "x.css").write_text(":root{--bg:#000;--serie-1:#111;--serie-2:#222}", encoding="utf-8")
            (tmp / "tokens" / "x-claro.css").write_text(":root{--bg:#fff;--serie-1:#111}", encoding="utf-8")
            antes, prancheta.GUIA_DIR = prancheta.GUIA_DIR, tmp
            try:
                with self.assertRaisesRegex(ValueError, "falta --serie-2"):
                    prancheta.tokens_css("x")
            finally:
                prancheta.GUIA_DIR = antes
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
