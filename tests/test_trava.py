"""Testes da trava da prancheta: hooks/trava_prancheta.py e o bloco hooks do SKILL.md.

Cada caso monta o JSON que o Claude Code entrega a um hook PreToolUse e roda o script como o
harness roda, com os argumentos que o frontmatter declara. Saída 2 é bloqueio, 0 é passagem.
Os erros plantados são as escritas que a trava existe para barrar: marca, nota geral e
aprovação gravadas pelo Claude no db, e a leitura de volta editada para o --estado passar. Os
casos de passagem são o ciclo legítimo: chat, sonda, leitura com out_dir para lido/ e a edição
do resto do projeto. O Bash em lido/ fica fora do matcher de propósito, porque é lacuna
declarada na referência.

Rodar: python3 -m unittest discover -s tests   (na raiz da skill, só stdlib, Python 3.9 ou mais)
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HOOK = RAIZ / "hooks" / "trava_prancheta.py"
SKILL = RAIZ / "SKILL.md"
REFERENCIA = RAIZ / "references" / "prancheta.md"
TEMPLATE = RAIZ / "assets" / "guia" / "prancheta.template.html"
URL = "https://claude.ai/artifact/AAAAAAAAAAAAAAAAAAAAAA"
PROJ = "/p/radio-pirata"
LIDO = PROJ + "/docs/prancheta-fase-2/lido"
EDITORES = ("Edit", "Write", "MultiEdit", "NotebookEdit")
DO_CLAUDE = {"chat", "sonda"}
# Eventos em que o Claude Code não roda hook de skill (conferido pela portas-em-automatico no
# 2.1.286 e no 2.1.289): hook declarado neles seria código morto.
SEM_HOOK_DE_SKILL = {"PreCompact", "PostCompact", "Notification", "ConfigChange",
                     "InstructionsLoaded", "Elicitation", "ElicitationResult",
                     "DirectoryAdded", "WorktreeCreate", "WorktreeRemove"}


def bloco_hooks():
    front = SKILL.read_text(encoding="utf-8").split("\n---", 1)[0]
    return front, (front.split("\nhooks:", 1)[1] if "\nhooks:" in front else "")


def argumentos_declarados():
    _, bloco = bloco_hooks()
    achados = re.findall(r"^\s*args:\s*(\[.*\])\s*$", bloco, re.M)
    return json.loads(achados[0]) if achados else []


def comando():
    """O comando do frontmatter, com a pasta da skill no lugar do ${CLAUDE_PLUGIN_ROOT} e o
    Python que roda os testes no lugar do python3, para a suíte valer nas duas versões."""
    return [sys.executable] + [a.replace("${CLAUDE_PLUGIN_ROOT}", str(RAIZ))
                               for a in argumentos_declarados()]


def roda(carga):
    texto = carga if isinstance(carga, str) else json.dumps(carga, ensure_ascii=False)
    r = subprocess.run(comando(), input=texto, capture_output=True, text=True)
    return r.returncode, r.stderr


def db(acao, colecao=None, **extra):
    entrada = {"action": acao, "url": URL}
    if colecao is not None:
        entrada["collection"] = colecao
    entrada.update(extra)
    return {"hook_event_name": "PreToolUse", "tool_name": "ArtifactData",
            "tool_input": entrada, "cwd": PROJ}


def edicao(ferramenta, caminho, cwd=PROJ):
    chave = "notebook_path" if ferramenta == "NotebookEdit" else "file_path"
    return {"hook_event_name": "PreToolUse", "tool_name": ferramenta,
            "tool_input": {chave: caminho, "content": "{}"}, "cwd": cwd}


def carrega_hook():
    spec = importlib.util.spec_from_file_location("trava_prancheta", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Base(unittest.TestCase):
    def bloqueia(self, carga, trecho="trava da prancheta"):
        codigo, erro = roda(carga)
        self.assertEqual(codigo, 2, "devia bloquear: {}\nstderr: {}".format(carga, erro))
        self.assertIn(trecho, erro)
        return erro

    def passa(self, carga):
        codigo, erro = roda(carga)
        self.assertEqual(codigo, 0, "devia passar: {}\nstderr: {}".format(carga, erro))
        self.assertEqual(erro, "")


class TestDb(Base):
    def test_escrita_do_claude_em_marcas_e_estado_bloqueia(self):
        for acao in ("set", "update", "str_replace", "delete"):
            for col, doc in (("marcas", "m-f1"), ("estado", "aprovacao"), ("estado", "geral")):
                with self.subTest(acao=acao, col=col, doc=doc):
                    erro = self.bloqueia(db(acao, col, doc_id=doc, data={"aprovado": True}))
                    self.assertIn("`{}`".format(col), erro)
                    self.assertIn("declarada", erro)
                    self.assertIn("sem tentar por outra ferramenta", erro)
                    self.assertIn("sessão nova", erro)

    def test_batch_com_uma_escrita_protegida_bloqueia(self):
        mista = [{"op": "set", "collection": "chat", "doc_id": "p1", "data": {}},
                 {"op": "set", "collection": "estado", "doc_id": "aprovacao", "data": {}}]
        self.bloqueia(db("batch", writes=mista), "`estado`")
        so_marcas = [{"op": "update", "collection": "marcas", "doc_id": d, "data": {}}
                     for d in ("f1-1", "f1-2")]
        self.bloqueia(db("batch", writes=so_marcas), "`marcas`")
        chat_no_topo = [{"op": "set", "collection": "chat", "doc_id": "p1", "data": {}}]
        self.bloqueia(db("batch", "estado", writes=chat_no_topo), "`estado`")

    def test_acao_desconhecida_conta_como_escrita(self):
        self.bloqueia(db("patch", "estado", doc_id="aprovacao"))
        self.bloqueia(db("", "marcas", doc_id="m-f1"))
        self.bloqueia(db("SET", "marcas", doc_id="m-f1"))

    def test_caixa_e_subcolecao_nao_escapam(self):
        for col in ("Marcas", "ESTADO", "marcas/m-f1/historico", "/estado"):
            with self.subTest(col=col):
                self.bloqueia(db("set", col, doc_id="x", data={}))

    def test_forma_que_a_trava_nao_confere_bloqueia(self):
        for carga in (db("set", doc_id="aprovacao", data={}),
                      db("update", "  ", doc_id="aprovacao", data={}),
                      db("batch"),
                      db("batch", writes=[]),
                      db("batch", writes={"collection": "chat"}),
                      db("batch", writes=[{"op": "set", "doc_id": "x", "data": {}}]),
                      db("set", "chat/../estado", doc_id="aprovacao", data={}),
                      {"tool_name": "ArtifactData"}):
            with self.subTest(carga=carga):
                self.bloqueia(carga, "não consegue conferir")

    def test_chat_e_sonda_passam(self):
        for acao in ("set", "update", "str_replace", "delete"):
            for col in sorted(DO_CLAUDE):
                with self.subTest(acao=acao, col=col):
                    self.passa(db(acao, col, doc_id="p1", data={"resposta": "ok"}))
        self.passa(db("batch", writes=[
            {"op": "set", "collection": "chat", "doc_id": "p1", "data": {}},
            {"op": "delete", "collection": "sonda", "doc_id": "teste", "if_version": 1}]))

    def test_leitura_passa_inclusive_para_lido(self):
        self.passa(db("get", "estado", doc_id="aprovacao"))
        self.passa(db("query", "marcas", query={"limit": 1000}))
        self.passa(db("profiles", ids=["u_" + "a" * 22]))
        for col in ("marcas", "estado", "chat"):
            with self.subTest(col=col):
                self.passa(db("list", col, query={"limit": 1000}, out_dir=LIDO))

    def test_db_de_outro_artefato_segue_livre(self):
        self.passa(db("set", "itens", doc_id="a", data={}))
        self.passa(db("update", "data/users/me/decks", doc_id="d1", data={}))
        self.passa(db("batch", writes=[
            {"op": "set", "collection": "tarefas", "doc_id": "t1", "data": {}}]))


class TestLido(Base):
    def test_edicao_da_leitura_bloqueia(self):
        for ferramenta in EDITORES:
            for caminho in (LIDO + "/marcas/m-f1.json",
                            LIDO + "/estado/aprovacao.json",
                            PROJ + "/docs/prancheta-fase-2/lido-2/chat/p1.json"):
                with self.subTest(ferramenta=ferramenta, caminho=caminho):
                    self.bloqueia(edicao(ferramenta, caminho), "não se edita")

    def test_caixa_ponto_ponto_e_caminho_relativo_nao_escapam(self):
        self.bloqueia(edicao("Write", PROJ + "/Docs/Prancheta-Fase-2/LIDO/marcas/m-f1.json"))
        self.bloqueia(edicao("Edit", PROJ + "/docs/prancheta-fase-2/x/../lido/estado/aprovacao.json"))
        self.bloqueia(edicao("Edit", "docs/prancheta-fase-2/lido/marcas/m-f1.json"))
        # Só a junção com o cwd vê este: o caminho nu não tem docs/ (revisão adversarial).
        erro = self.bloqueia(edicao("Write", "lido/marcas/m-f1.json",
                                    cwd=PROJ + "/docs/prancheta-fase-2"))
        self.assertIn("o --estado só aceita lido*/", erro)
        self.assertIn("sem tentar por outra ferramenta", erro)

    def test_atalho_para_lido_bloqueia(self):
        tmp = Path(tempfile.mkdtemp(prefix="trava-"))
        try:
            lido = tmp / "docs" / "prancheta-fase-2" / "lido"
            (lido / "marcas").mkdir(parents=True)
            (lido / "marcas" / "m-f1.json").write_text("{}", encoding="utf-8")
            os.symlink(str(lido), str(tmp / "atalho"))
            os.symlink(str(tmp / "docs"), str(tmp / "espelho"))
            self.bloqueia(edicao("Write", str(tmp / "atalho" / "marcas" / "m-f1.json")))
            self.bloqueia(edicao("Edit", str(tmp / "espelho" / "prancheta-fase-2" / "lido"
                                             / "marcas" / "m-f1.json")))
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)

    def test_resto_do_projeto_passa(self):
        for caminho in (PROJ + "/docs/prancheta-fase-2/conteudo.json",
                        PROJ + "/docs/prancheta-fase-2/prancheta-fase-2.html",
                        PROJ + "/docs/prancheta-fase-2/lido.md",
                        PROJ + "/docs/notas/lido/resumo.md",
                        PROJ + "/docs/guia-radio-pirata/guia-radio-pirata.html",
                        PROJ + "/SESSION.md",
                        PROJ + "/HANDOFF.md"):
            for ferramenta in ("Edit", "Write"):
                with self.subTest(ferramenta=ferramenta, caminho=caminho):
                    self.passa(edicao(ferramenta, caminho))


class TestRobustez(Base):
    def test_entrada_ilegivel_bloqueia(self):
        # O matcher só manda para cá as ferramentas da trava: o que ela não lê, não passa.
        for texto in ("", "não é json", "[]", "42"):
            with self.subTest(texto=texto):
                self.bloqueia(texto, "não conseguiu ler")

    def test_json_fundo_demais_nao_escapa(self):
        # Revisão adversarial de 17/10/2026: aninhamento fundo estourava o parser, caía no
        # except e liberava a escrita (uns mil níveis no 3.9, uns 120 mil no 3.14).
        fundo = 200000
        carga = json.dumps(db("set", "estado", doc_id="aprovacao", data={"aprovado": True}))
        carga = carga.replace('"aprovado": true', '"aprovado": true, "pad": ' + "[" * fundo + "]" * fundo)
        self.bloqueia(carga, "não conseguiu ler")
        raso = {"nivel": [[[["ok"]]]] * 10}
        self.passa(db("set", "chat", doc_id="p1", data=raso))

    def test_outra_ferramenta_passa(self):
        self.passa({"tool_name": "Read", "tool_input": {"file_path": LIDO + "/marcas/m-f1.json"}})
        # Lacuna declarada: o Bash fica fora do matcher e o script não o confere.
        self.passa({"tool_name": "Bash", "tool_input": {"command": "sed -i s/a/b/ " + LIDO
                                                                   + "/marcas/m-f1.json"}})


class TestFrontmatter(unittest.TestCase):
    def test_bloco_hooks_resolve_pela_pasta_da_skill(self):
        _, bloco = bloco_hooks()
        self.assertTrue(bloco, "SKILL.md sem bloco hooks no frontmatter")
        eventos = re.findall(r"^  ([A-Za-z]+):\s*$", bloco, re.M)
        self.assertEqual(eventos, ["PreToolUse"])
        self.assertFalse(set(eventos) & SEM_HOOK_DE_SKILL)
        self.assertEqual(re.findall(r"^\s*command:\s*(\S+)\s*$", bloco, re.M), ["python3"])
        args = argumentos_declarados()
        self.assertEqual(args, ["-I", "${CLAUDE_PLUGIN_ROOT}/hooks/trava_prancheta.py"])
        valores = "\n".join(re.findall(r"^\s*(?:command|args):\s*(.+)$", bloco, re.M))
        self.assertNotIn("./hooks/", valores)
        self.assertNotIn("CLAUDE_SKILL_DIR", valores)
        for script in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/hooks/([\w.-]+)", valores):
            self.assertTrue((RAIZ / "hooks" / script).is_file(), script)

    def test_matcher_cobre_db_e_edicao_e_deixa_o_bash_fora(self):
        _, bloco = bloco_hooks()
        matchers = re.findall(r'^\s*- matcher:\s*"([^"]+)"\s*$', bloco, re.M)
        self.assertEqual(len(matchers), 1)
        self.assertEqual(set(matchers[0].split("|")), {"ArtifactData"} | set(EDITORES))

    def test_compatibility_declara_so_claude_code(self):
        front, _ = bloco_hooks()
        linha = re.search(r"^compatibility:\s*(.+)$", front, re.M)
        self.assertTrue(linha and "Só Claude Code" in linha.group(1))


class TestCoerencia(unittest.TestCase):
    def test_lista_protegida_bate_com_o_template(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        usadas = set(re.findall(r"db\.(?:collection|doc)\(\s*['\"]([^'\"/]+)", html))
        self.assertIn("chat", usadas)
        self.assertEqual(set(carrega_hook().PROTEGIDAS), usadas - DO_CLAUDE)

    def test_skill_e_referencia_citam_a_trava(self):
        for doc in (SKILL, REFERENCIA):
            with self.subTest(doc=doc.name):
                self.assertTrue("hooks/trava_prancheta.py" in doc.read_text(encoding="utf-8"),
                                "{} não cita hooks/trava_prancheta.py".format(doc.name))


if __name__ == "__main__":
    unittest.main()
