#!/usr/bin/env python3
"""Monta a prancheta de aprovação de plano e lê de volta o que o Bera marcou nela.

A prancheta leva um plano que já existe para o Bera aprovar. O padrão é a recomendação: ele
marca só o que quer mudar (Manter, Ajustar ou Cortar em cada passo, Incluir ou Fora nas opções,
Ok ou Vetar nas premissas, antecipar ou adiar fase na linha do tempo) e aprova no próprio
quadro, com confirmação, data e hora. As marcas vivem no `db` do Artifact, e o Claude as traz
de volta pelo ArtifactData com `out_dir`. Anatomia, ciclo e leitura de volta em
references/prancheta.md.

Uso:
    prancheta.py --nome rodada-2 --dir ~/projetos/x --dry-run
    prancheta.py --nome rodada-2 --dir ~/projetos/x
    prancheta.py --nome rodada-2 --dir ~/projetos/x --estado docs/prancheta-rodada-2/lido --dry-run
    prancheta.py --nome rodada-2 --dir ~/projetos/x --estado docs/prancheta-rodada-2/lido

Sem --conteudo, lê docs/prancheta-<nome>/conteudo.json do projeto. Sai em
docs/prancheta-<nome>/prancheta-<nome>.html. Com --estado (a pasta que o ArtifactData gravou,
com marcas/, estado/ e chat/, ou um JSON com essas três chaves), confere o estado contra o
conteúdo, imprime o resumo em markdown para o registro do projeto e, sem --dry-run, escreve a
versão aprovada, que é só leitura.

Saída: 0 gerou ou validou; 2 conteúdo ou estado reprovado, nada escrito; 3 estado válido mas
sem aprovação em dia (pendente, desfeita ou com marca posterior), resumo impresso, nada escrito.

O formato do JSON de conteúdo está em references/prancheta.md e na tabela FORMA abaixo.
"""
# O python3 do macOS (/usr/bin) é 3.9: a anotação vira string e nunca é avaliada.
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
GUIA_DIR = SKILL / "assets" / "guia"
TEMPLATE = GUIA_DIR / "prancheta.template.html"
LIMITE_MB = 16

ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
NOME = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL = re.compile(r"^https?://[^\s<>\"']+$")

STATUS_FATO = ("documentado", "alegado", "nao_confirmado", "misto")
SEVERIDADE = ("alto", "medio", "baixo")
ESFORCO = ("baixo", "medio", "alto")
QUEM = ("claude", "voce")
VALORES = {"passo": ("manter", "ajustar", "cortar"),
           "opcao": ("incluir", "fora"),
           "premissa": ("ok", "vetar")}
ROTULO = {"manter": "Manter", "ajustar": "Ajustar", "cortar": "Cortar", "incluir": "Incluir",
          "fora": "Fora", "ok": "Ok", "vetar": "Vetar"}
ATALHOS_PADRAO = {"ajustar": ["Mais fundo", "Mais enxuto", "Outra data", "Outro lugar",
                              "Outra ferramenta"],
                  "cortar": ["Não preciso", "Fica para depois", "Fora do escopo"]}
LIMITE_MARCO = 30      # dias que uma fase anda por marca própria, para frente ou para trás
MAX_PERGUNTAS = 4      # o AskUserQuestion aceita até quatro perguntas por chamada
MAX_DIAS = 180         # acima disso a escala de dias deixa de ser legível
MAX_NOTA = 2000
MAX_NOTA_GERAL = 4000

# (obrigatórias, opcionais) por nível. Chave fora das duas reprova, com a parecida como dica.
# Até 21/09/2026 o documento.py lia tudo com valor padrão vazio e um JSON improvisado saía como
# HTML bonito e vazio. A prancheta nasce com o gate fechado pelo mesmo motivo.
FORMA = {
    "raiz": (("titulo", "projeto", "lede", "fases"),
             ("titulo_curto", "tarja", "eyebrow", "pedidos", "fatos", "pistas", "linha_do_tempo", "casas",
              "fluxos", "opcoes", "premissas", "riscos", "acessos", "perguntas", "fontes",
              "atalhos")),
    "pedido": (("texto", "fases"), ()),
    "fato": (("status", "titulo", "texto", "fonte"), ("falta", "selo")),
    "linha_do_tempo": ((), ("datas_fixas", "nota")),
    "data_fixa": (("id", "data", "rotulo"), ()),
    "fase": (("id", "titulo", "passos"), ("rotulo", "quem", "quando", "pausa", "agenda")),
    "agenda": (("inicio", "segmentos"), ("depois_de", "prazo", "resumo")),
    "segmento": (("quem", "dias"), ()),
    "passo": (("id", "titulo", "muda", "pronto"), ("onde", "quem", "skills")),
    "casa": (("titulo",), ("caminho", "papel", "pecas")),
    "peca": (("nome",), ("tag",)),
    "opcao": (("id", "titulo", "texto", "recomendada"), ("onde", "esforco", "porque_fora")),
    "premissa": (("id", "texto"), ()),
    "risco": (("severidade", "risco", "mitigacao"), ()),
    "acesso": (("tipo", "detalhe"), ()),
    "pergunta": (("titulo", "recomendacao"), ("contexto",)),
    "fonte": (("rotulo",), ("url",)),
    "atalhos": ((), ("ajustar", "cortar")),
}
# O porquê das regras que mais reprovam, dito na própria mensagem de erro.
PORQUE = {
    ("fato", "fonte"): "fato sem fonte é opinião, e a prancheta separa o verificado do resto",
    ("passo", "pronto"): "passo sem 'pronto quando' não tem como ser aprovado nem conferido",
    ("pergunta", "recomendacao"): "pergunta sem recomendação obriga o Bera a decidir sem a sua leitura",
    ("risco", "mitigacao"): "risco sem mitigação é só preocupação",
}
LISTAS = {"pedidos": "pedido", "fatos": "fato", "casas": "casa", "opcoes": "opcao",
          "premissas": "premissa", "riscos": "risco", "acessos": "acesso",
          "perguntas": "pergunta", "fontes": "fonte"}


class Gate:
    """Junta os problemas do conteúdo. Reprovar cedo, dizendo onde e por quê."""

    def __init__(self):
        self.erros: list = []
        self.avisos: list = []

    def erro(self, onde, msg):
        self.erros.append(f"{onde}: {msg}" if onde else msg)

    def aviso(self, onde, msg):
        self.avisos.append(f"{onde}: {msg}" if onde else msg)

    def objeto(self, obj, forma, onde) -> bool:
        if not isinstance(obj, dict):
            self.erro(onde, f"precisa ser um objeto, veio {type(obj).__name__}")
            return False
        obrig, opc = FORMA[forma]
        esperadas = obrig + opc
        for k in sorted(set(obj) - set(esperadas)):
            dica = difflib.get_close_matches(k, esperadas, n=1, cutoff=0.6)
            self.erro(onde, f"chave desconhecida `{k}`" + (f", talvez `{dica[0]}`" if dica else ""))
        for k in obrig:
            porque = PORQUE.get((forma, k))
            sufixo = f": {porque}" if porque else ""
            v = obj.get(k)
            if k not in obj:
                self.erro(onde, f"falta `{k}`{sufixo}")
            elif (v is None or (isinstance(v, str) and not v.strip())
                  or (isinstance(v, (list, dict)) and not v)):
                self.erro(onde, f"`{k}` está vazia{sufixo}")
        return True

    def texto(self, obj, chaves, onde):
        for k in chaves:
            if k in obj and obj[k] is not None and not isinstance(obj[k], str):
                self.erro(onde, f"`{k}` precisa ser texto, veio {type(obj[k]).__name__}")

    def lista(self, obj, chave, onde) -> list:
        v = obj.get(chave)
        if v is None:
            return []
        if not isinstance(v, list):
            self.erro(onde, f"`{chave}` precisa ser lista, veio {type(v).__name__}")
            return []
        return v


def _data(txt):
    if not isinstance(txt, str) or not DATA.match(txt):
        return None
    try:
        return date.fromisoformat(txt)
    except ValueError:
        return None


# ------------------------------------------------------------------------- cronograma (cascata)
# A mesma conta mora no template, em JS, entre os marcadores <cronograma>. Os testes comparam
# as duas sobre o mesmo vetor: conta duplicada que diverge é o defeito que o detonado combate.
#
# Cascata rígida: o deslocamento efetivo de uma fase é o próprio mais o maior efetivo entre as
# fases de que ela depende. Uma fase adiada empurra as seguintes pelo mesmo tanto, uma
# antecipada puxa, e com mais de uma dependência vale a que mais andou.

def cronograma(linhas, marcos):
    """linhas: [{id, ini, dur, deps}] em ordem, ini em dias desde a origem. marcos: {id: dias}.
    Devolve {id: {proprio, efetivo, ini, fim, causa}}, com causa = dependência que mais andou."""
    out = {}
    for ln in linhas:
        proprio = int(marcos.get(ln["id"], 0) or 0)
        herdado, causa = 0, None
        for dep in ln["deps"]:
            if dep in out and (causa is None or out[dep]["efetivo"] > herdado):
                herdado, causa = out[dep]["efetivo"], dep
        if causa is not None and herdado == 0:
            causa = None
        efetivo = proprio + herdado
        out[ln["id"]] = {"proprio": proprio, "efetivo": efetivo, "ini": ln["ini"] + efetivo,
                         "fim": ln["ini"] + efetivo + ln["dur"], "causa": causa}
    return out


def linhas_da_agenda(fases):
    """Converte as agendas em linhas do cronograma, com a origem no menor início."""
    com = [f for f in fases if f.get("agenda")]
    if not com:
        return None, []
    origem = min(_data(f["agenda"]["inicio"]) for f in com)
    linhas, anterior = [], None
    for f in com:
        ag = f["agenda"]
        deps = ag["depois_de"] if "depois_de" in ag else ([anterior] if anterior else [])
        linhas.append({"id": f["id"], "ini": (_data(ag["inicio"]) - origem).days,
                       "dur": float(sum(s["dias"] for s in ag["segmentos"])), "deps": deps})
        anterior = f["id"]
    return origem, linhas


def dia_txt(origem, pos):
    return (origem + timedelta(days=pos)).strftime("%d/%m")


def periodo_txt(origem, ini, fim):
    """Período de dias inteiros coberto por [ini, fim), como a prancheta escreve."""
    a = origem + timedelta(days=math.floor(ini + 1e-9))
    b = origem + timedelta(days=max(math.ceil(fim - 1e-9) - 1, math.floor(ini + 1e-9)))
    if a == b:
        return a.strftime("%d/%m")
    if a.month == b.month and a.year == b.year:
        return f"{a.day:02d} a {b.strftime('%d/%m')}"
    return f"{a.strftime('%d/%m')} a {b.strftime('%d/%m')}"


# ------------------------------------------------------------------------------ conteúdo

def valida_conteudo(d):
    """Devolve (gate, conteúdo normalizado ou None)."""
    g = Gate()
    if not g.objeto(d, "raiz", "conteúdo"):
        return g, None
    g.texto(d, ("titulo", "titulo_curto", "projeto", "lede", "tarja", "eyebrow", "pistas"), "conteúdo")
    if isinstance(d.get("titulo_curto"), str) and len(d["titulo_curto"].split()) > 4:
        g.erro("titulo_curto", "até quatro palavras: é o nome da aba e da galeria do Artifact")
    if isinstance(d.get("tarja"), str) and len(d["tarja"]) > 24:
        g.erro("tarja", "até 24 caracteres: é rótulo de barra, não frase")
    if isinstance(d.get("lede"), str) and len(d["lede"]) > 700:
        g.aviso("lede", f"{len(d['lede'])} caracteres: a capa é para ler em segundos")

    ids = {}

    def registra(i, onde):
        if i is None:  # a falta do id já foi dita pelo objeto()
            return False
        if not isinstance(i, str) or not ID.match(i):
            g.erro(onde, f"id `{i}` fora do formato (minúsculas, dígitos, - e _, até 48)")
            return False
        if i in ids:
            g.erro(onde, f"id `{i}` repetido, já usado em {ids[i]}: a marca do db é por id")
            return False
        ids[i] = onde
        return True

    for chave, forma in LISTAS.items():
        for n, item in enumerate(g.lista(d, chave, "conteúdo")):
            onde = f"{chave}[{n}]"
            if not g.objeto(item, forma, onde):
                continue
            if forma == "pedido":
                g.texto(item, ("texto", "fases"), onde)
            elif forma == "fato":
                g.texto(item, ("titulo", "texto", "fonte", "falta", "selo"), onde)
                if item.get("status") not in STATUS_FATO:
                    g.erro(onde, "`status` precisa ser " + ", ".join(STATUS_FATO))
            elif forma == "casa":
                g.texto(item, ("titulo", "caminho", "papel"), onde)
                for m, pc in enumerate(g.lista(item, "pecas", onde)):
                    if g.objeto(pc, "peca", f"{onde}.pecas[{m}]"):
                        g.texto(pc, ("nome", "tag"), f"{onde}.pecas[{m}]")
            elif forma == "opcao":
                g.texto(item, ("titulo", "texto", "onde", "porque_fora"), onde)
                registra(item.get("id"), onde)
                if not isinstance(item.get("recomendada"), bool):
                    g.erro(onde, "`recomendada` precisa ser true ou false")
                elif not item["recomendada"] and not str(item.get("porque_fora") or "").strip():
                    g.erro(onde, "opção fora da recomendação precisa de `porque_fora`: o Bera "
                                 "decide melhor sabendo por que ela ficou de fora")
                if "esforco" in item and item["esforco"] not in ESFORCO:
                    g.erro(onde, "`esforco` precisa ser " + ", ".join(ESFORCO))
            elif forma == "premissa":
                g.texto(item, ("texto",), onde)
                registra(item.get("id"), onde)
            elif forma == "risco":
                g.texto(item, ("risco", "mitigacao"), onde)
                if item.get("severidade") not in SEVERIDADE:
                    g.erro(onde, "`severidade` precisa ser " + ", ".join(SEVERIDADE))
            elif forma == "acesso":
                g.texto(item, ("tipo", "detalhe"), onde)
            elif forma == "pergunta":
                g.texto(item, ("titulo", "recomendacao", "contexto"), onde)
            elif forma == "fonte":
                g.texto(item, ("rotulo", "url"), onde)
                if item.get("url") and not URL.match(str(item["url"])):
                    g.erro(onde, "`url` precisa começar com http:// ou https://")

    perguntas = d.get("perguntas") if isinstance(d.get("perguntas"), list) else []
    if len(perguntas) > MAX_PERGUNTAS:
        g.erro("perguntas", f"{len(perguntas)} perguntas: o chat leva até {MAX_PERGUNTAS} por "
                            "vez, e a aprovação em si é na prancheta, não pergunta")
    fluxos = g.lista(d, "fluxos", "conteúdo")
    if any(not isinstance(x, str) or not x.strip() for x in fluxos):
        g.erro("fluxos", "cada fluxo é uma frase de texto")

    atalhos = d.get("atalhos")
    if atalhos is not None and g.objeto(atalhos, "atalhos", "atalhos"):
        for k in ("ajustar", "cortar"):
            v = atalhos.get(k)
            if v is not None and (not isinstance(v, list) or not v
                                  or any(not isinstance(x, str) or not x.strip() for x in v)
                                  or len(set(v)) != len(v) or len(v) > 8):
                g.erro(f"atalhos.{k}", "lista de 1 a 8 rótulos de texto, sem repetição")

    # linha do tempo: datas fixas
    fixas = {}
    ldt = d.get("linha_do_tempo")
    if ldt is not None and g.objeto(ldt, "linha_do_tempo", "linha_do_tempo"):
        g.texto(ldt, ("nota",), "linha_do_tempo")
        for n, df in enumerate(g.lista(ldt, "datas_fixas", "linha_do_tempo")):
            onde = f"linha_do_tempo.datas_fixas[{n}]"
            if not g.objeto(df, "data_fixa", onde):
                continue
            g.texto(df, ("rotulo",), onde)
            if not isinstance(df.get("id"), str) or not ID.match(df["id"]):
                g.erro(onde, f"id `{df.get('id')}` fora do formato")
            elif df["id"] in fixas:
                g.erro(onde, f"data fixa `{df['id']}` repetida")
            elif _data(df.get("data")) is None:
                g.erro(onde, "`data` precisa ser AAAA-MM-DD")
            else:
                fixas[df["id"]] = _data(df["data"])

    # fases, passos e agenda
    fases = d.get("fases") if isinstance(d.get("fases"), list) else []
    if "fases" in d and not isinstance(d.get("fases"), list):
        g.erro("fases", "precisa ser lista")
    com_agenda = []
    for n, f in enumerate(fases):
        onde = f"fases[{n}]"
        if not g.objeto(f, "fase", onde):
            continue
        g.texto(f, ("titulo", "rotulo", "quem", "quando", "pausa"), onde)
        registra(f.get("id"), onde)
        passos = g.lista(f, "passos", onde)
        if len(passos) > 7:
            g.aviso(onde, f"{len(passos)} passos: fase com mais de sete costuma ser duas")
        for m, p in enumerate(passos):
            op = f"{onde}.passos[{m}]"
            if g.objeto(p, "passo", op):
                g.texto(p, ("titulo", "muda", "pronto", "onde", "quem", "skills"), op)
                registra(p.get("id"), op)
        ag = f.get("agenda")
        if ag is None:
            continue
        oa = f"{onde}.agenda"
        if not g.objeto(ag, "agenda", oa):
            continue
        if "quando" in f:
            g.erro(onde, "com `agenda` o período é calculado e acompanha os marcos: tire o "
                         "`quando`, senão a prancheta mostra duas datas que podem divergir")
        if _data(ag.get("inicio")) is None:
            g.erro(oa, "`inicio` precisa ser AAAA-MM-DD")
        segs = g.lista(ag, "segmentos", oa)
        for m, s in enumerate(segs):
            os_ = f"{oa}.segmentos[{m}]"
            if not g.objeto(s, "segmento", os_):
                continue
            if s.get("quem") not in QUEM:
                g.erro(os_, "`quem` precisa ser claude ou voce")
            dias = s.get("dias")
            if isinstance(dias, bool) or not isinstance(dias, (int, float)) or not 0 < dias <= 60:
                g.erro(os_, "`dias` precisa ser número maior que 0 e até 60")
        deps = ag.get("depois_de")
        if deps is not None:
            if not isinstance(deps, list) or any(not isinstance(x, str) for x in deps):
                g.erro(oa, "`depois_de` é lista de ids de fase")
            else:
                for x in deps:
                    if x not in com_agenda:
                        g.erro(oa, f"`depois_de` cita `{x}`, que não é fase anterior com agenda: "
                                   "a cascata só anda para a frente na lista")
        if "prazo" in ag and ag["prazo"] not in fixas:
            g.erro(oa, f"`prazo` cita `{ag['prazo']}`, que não está em linha_do_tempo.datas_fixas")
        g.texto(ag, ("resumo",), oa)
        if isinstance(f.get("id"), str):
            com_agenda.append(f["id"])

    for fid in com_agenda:
        if f"m-{fid}" in ids:
            g.erro("ids", f"`m-{fid}` é o id do marco da fase `{fid}` e não pode ser usado em outro item")

    if g.erros:
        return g, None

    # normaliza: rótulo de fase, atalhos padrão
    c = json.loads(json.dumps(d))
    for n, f in enumerate(c["fases"]):
        f.setdefault("rotulo", f"F{n}")
    c["atalhos"] = {k: (c.get("atalhos") or {}).get(k) or v for k, v in ATALHOS_PADRAO.items()}

    # cronograma da recomendação: tamanho da escala e prazo já estourado
    origem, linhas = linhas_da_agenda(c["fases"])
    if linhas:
        rec = cronograma(linhas, {})
        fim = max(x["fim"] for x in rec.values())
        posicoes = [(dt - origem).days for dt in fixas.values()]
        span = max([fim] + [p + 1 for p in posicoes]) - min([0] + posicoes)
        if span > MAX_DIAS:
            g.erro("linha_do_tempo", f"{span:.0f} dias na escala: acima de {MAX_DIAS} a linha "
                                     "do tempo deixa de ser legível, fatie o plano")
        for f in c["fases"]:
            ag = f.get("agenda")
            if ag and ag.get("prazo"):
                limite = (fixas[ag["prazo"]] - origem).days
                if rec[f["id"]]["fim"] > limite + 1e-9:
                    g.erro(f"fases {f['id']}", "na própria recomendação a fase já termina depois "
                                               f"do prazo `{ag['prazo']}`: corrija a agenda antes "
                                               "de pedir aprovação")
    if g.erros:
        return g, None
    return g, c


def versao_conteudo(c):
    """Impressão digital do conteúdo normalizado. A página grava na aprovação, e o --estado só
    diz aprovada se ela bater com o conteúdo local: a aprovação vale para o plano que o Bera viu,
    não para o que o conteúdo virou depois. Achado da auditoria de prompt de 17/10/2026."""
    bruto = json.dumps(c, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:16]


def contagens(c, marcas):
    """O mesmo resumo que a página grava ao aprovar, recalculado das marcas lidas de volta."""
    reg = marcaveis(c)
    k = {"ajustes": 0, "cortes": 0, "vetos": 0, "opcoes_incluidas": 0,
         "opcoes_total": len(c.get("opcoes", [])), "datas_movidas": 0, "conflitos": 0}
    for i, r in reg.items():
        v = marcas[i]["valor"] if i in marcas else r["padrao"]
        k["ajustes"] += r["tipo"] == "passo" and v == "ajustar"
        k["cortes"] += r["tipo"] == "passo" and v == "cortar"
        k["vetos"] += r["tipo"] == "premissa" and v == "vetar"
        k["opcoes_incluidas"] += r["tipo"] == "opcao" and v == "incluir"
        k["datas_movidas"] += r["tipo"] == "marco" and v != 0
    origem, lns = linhas_da_agenda(c["fases"])
    if lns:
        fixas = {df["id"]: _data(df["data"]) for df in (c.get("linha_do_tempo") or {}).get("datas_fixas", [])}
        efe = cronograma(lns, {i[2:]: m["valor"] for i, m in marcas.items() if m["tipo"] == "marco"})
        for f in c["fases"]:
            pz = (f.get("agenda") or {}).get("prazo")
            if pz and efe[f["id"]]["fim"] > (fixas[pz] - origem).days + 1e-9:
                k["conflitos"] += 1
    return k


def marcaveis(c):
    """Tudo o que o Bera pode marcar, com tipo, padrão (a recomendação) e rótulo para o resumo."""
    reg = {}
    for f in c["fases"]:
        for p in f["passos"]:
            reg[p["id"]] = {"tipo": "passo", "padrao": "manter",
                            "rotulo": f"{p['id'].upper()} · {p['titulo']}"}
        if f.get("agenda"):
            reg["m-" + f["id"]] = {"tipo": "marco", "padrao": 0,
                                   "rotulo": f"{f['rotulo']} · {f['titulo']}"}
    for o in c.get("opcoes", []):
        reg[o["id"]] = {"tipo": "opcao", "padrao": "incluir" if o["recomendada"] else "fora",
                        "rotulo": f"Opção · {o['titulo']}"}
    for p in c.get("premissas", []):
        txt = p["texto"] if len(p["texto"]) <= 90 else p["texto"][:89].rstrip() + "…"
        reg[p["id"]] = {"tipo": "premissa", "padrao": "ok", "rotulo": f"{p['id'].upper()} · {txt}"}
    return reg


# -------------------------------------------------------------------------------- estado

def _quando(txt):
    """ISO 8601 para datetime com fuso. O JS grava toISOString(), em UTC com Z, e o
    fromisoformat do 3.9 não aceita o Z."""
    if not isinstance(txt, str):
        return None
    try:
        dt = datetime.fromisoformat(txt.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def quando_txt(dt):
    local = dt.astimezone()
    return local.strftime("%d/%m/%Y às %Hh%M")


def _corpo(obj):
    """O ArtifactData com out_dir grava cada documento num arquivo, <pasta>/<coleção>/<id>.json,
    com o corpo puro: conferido em 17/10/2026 na sonda do exemplo publicado. O envelope (id,
    version e data) fica aceito por tolerância, caso a ferramenta mude de formato."""
    if (isinstance(obj, dict) and isinstance(obj.get("data"), dict)
            and ({"version", "id", "doc_id", "path"} & set(obj))):
        return obj["data"]
    return obj


def carrega_estado(caminho):
    est = {"marcas": {}, "estado": {}, "chat": {}}
    if caminho.is_dir():
        mtimes = []
        for col in est:
            pasta = caminho / col
            if pasta.is_dir():
                for arq in sorted(pasta.glob("*.json")):
                    est[col][arq.stem] = _corpo(json.loads(arq.read_text(encoding="utf-8")))
                    mtimes.append(arq.stat().st_mtime)
        lido = datetime.fromtimestamp(max(mtimes), tz=timezone.utc) if mtimes else None
    else:
        obj = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("o JSON de estado precisa ser um objeto com marcas, estado e chat")
        for col in est:
            v = obj.get(col) or {}
            if not isinstance(v, dict):
                raise ValueError(f"`{col}` precisa ser objeto de id para documento")
            est[col] = {k: _corpo(x) for k, x in v.items()}
        lido = _quando(obj.get("lido_em")) or datetime.fromtimestamp(caminho.stat().st_mtime,
                                                                       tz=timezone.utc)
    est["lido_em"] = lido.isoformat() if lido else None
    return est


def valida_estado(est, c, nome, versao):
    """Devolve (erros, avisos, snapshot limpo, situação da aprovação, ids posteriores)."""
    erros, avisos = [], []
    reg = marcaveis(c)
    marcas = {}
    for i, m in sorted(est["marcas"].items()):
        onde = f"marcas/{i}"
        if i not in reg:
            erros.append(f"{onde}: id que não existe nesta prancheta")
            continue
        if not isinstance(m, dict):
            erros.append(f"{onde}: documento precisa ser objeto")
            continue
        tipo = reg[i]["tipo"]
        if m.get("tipo") != tipo:
            erros.append(f"{onde}: `tipo` {m.get('tipo')!r}, e o item é {tipo}")
            continue
        v = m.get("valor")
        if tipo == "marco":
            if isinstance(v, bool) or not isinstance(v, int) or abs(v) > LIMITE_MARCO:
                erros.append(f"{onde}: `valor` de marco é inteiro de -{LIMITE_MARCO} a {LIMITE_MARCO}")
                continue
        elif v not in VALORES[tipo]:
            erros.append(f"{onde}: `valor` {v!r} inválido para {tipo}")
            continue
        at = m.get("atalhos", [])
        permitidos = c["atalhos"].get(v, []) if tipo == "passo" else []
        if not isinstance(at, list) or any(x not in permitidos for x in at):
            erros.append(f"{onde}: `atalhos` fora da lista de {v!r}")
            continue
        nota = m.get("nota", "")
        if not isinstance(nota, str) or len(nota) > MAX_NOTA:
            erros.append(f"{onde}: `nota` precisa ser texto de até {MAX_NOTA} caracteres")
            continue
        em = _quando(m.get("em"))
        if em is None:
            erros.append(f"{onde}: `em` não é data e hora ISO")
            continue
        marcas[i] = {"tipo": tipo, "valor": v, "atalhos": list(at), "nota": nota, "em": em.isoformat()}

    estado = est["estado"]
    geral = estado.get("geral")
    if geral is not None:
        if (not isinstance(geral, dict) or not isinstance(geral.get("nota", ""), str)
                or len(geral.get("nota", "")) > MAX_NOTA_GERAL):
            erros.append("estado/geral: precisa ser objeto com `nota` de texto")
            geral = None
        else:
            geral = {"nota": geral.get("nota", ""), "em": geral.get("em")}
    aprov = estado.get("aprovacao")
    situacao, posteriores = "pendente", []
    if aprov is not None:
        if not isinstance(aprov, dict) or not isinstance(aprov.get("aprovado"), bool) \
                or _quando(aprov.get("em")) is None:
            erros.append("estado/aprovacao: precisa ter `aprovado` (true ou false) e `em` ISO")
            aprov = None
        else:
            em_ap = _quando(aprov["em"])
            if not aprov["aprovado"]:
                situacao = "desfeita"
            elif aprov.get("conteudo") != versao or aprov.get("nome") != nome:
                situacao = "outra_versao"
            else:
                posteriores = sorted(i for i, m in marcas.items() if _quando(m["em"]) > em_ap)
                situacao = "desatualizada" if posteriores else "aprovada"
            if situacao == "aprovada":
                # A leitura tem de fechar com o que a página gravou ao aprovar. Coleção que não
                # veio, ou marca que sumiu, dava "aprovada" com "nada mudado" até 17/10/2026.
                gravado = aprov.get("resumo") if isinstance(aprov.get("resumo"), dict) else {}
                calc = contagens(c, marcas)
                dif = [f"{k} {gravado[k]} na aprovação e {calc[k]} nas marcas lidas"
                       for k in sorted(gravado) if k in calc and gravado[k] != calc[k]]
                ems = [_quando(m["em"]) for m in marcas.values()]
                ate = _quando(aprov.get("marcas_ate")) if aprov.get("marcas_ate") else None
                if (max(ems) if ems else None) != ate:
                    dif.append("a marca mais recente lida não é a que a aprovação registrou")
                if dif:
                    erros.append("a leitura não fecha com a aprovação (" + ", ".join(dif) + "). "
                                 "Leia de novo as coleções com o ArtifactData, sem editar lido/")
            aprov = {k: aprov.get(k) for k in ("aprovado", "em", "por", "marcas_ate", "resumo", "conteudo", "nome")}
    for k in sorted(set(estado) - {"geral", "aprovacao"}):
        avisos.append(f"estado/{k}: documento que a prancheta não conhece, ignorado")
    if geral and aprov and aprov.get("aprovado") and _quando(geral.get("em")) \
            and _quando(geral["em"]) > _quando(aprov["em"]):
        avisos.append("o comentário geral foi escrito depois da aprovação: leia antes de registrar")

    chat = {}
    n_perg = len(c.get("perguntas", []))
    for i, r in sorted(est["chat"].items()):
        onde = f"chat/{i}"
        if not isinstance(r, dict):
            erros.append(f"{onde}: documento precisa ser objeto")
            continue
        p = r.get("pergunta")
        if isinstance(p, bool) or not isinstance(p, int) or not 1 <= p <= n_perg:
            erros.append(f"{onde}: `pergunta` precisa ser de 1 a {n_perg}")
            continue
        if not isinstance(r.get("resposta"), str) or not r["resposta"].strip():
            erros.append(f"{onde}: `resposta` vazia")
            continue
        chat[f"p{p}"] = {"pergunta": p, "resposta": r["resposta"],
                         "em": r.get("em") if _quando(r.get("em")) else None}
    snapshot = {"marcas": marcas, "geral": geral, "aprovacao": aprov, "chat": chat,
                "lido_em": est.get("lido_em")}
    return erros, avisos, snapshot, situacao, posteriores


def resumo_md(c, snap, situacao, posteriores):
    """O registro da aprovação, para o SESSION.md ou o arquivo de decisões do projeto."""
    reg = marcaveis(c)
    linhas = [f"## Prancheta: {c['titulo']} ({c['projeto']})", ""]
    ap = snap["aprovacao"]
    if situacao == "aprovada":
        linhas.append(f"Aprovada em {quando_txt(_quando(ap['em']))}, na própria prancheta.")
    elif situacao == "desatualizada":
        mudaram = "1 marca mudou" if len(posteriores) == 1 else f"{len(posteriores)} marcas mudaram"
        linhas.append(f"APROVAÇÃO DESATUALIZADA: aprovada em {quando_txt(_quando(ap['em']))}, "
                      f"mas {mudaram} depois ({', '.join(posteriores)}). "
                      "Não registre como aprovada: peça ao Bera para aprovar de novo na prancheta.")
    elif situacao == "desfeita":
        linhas.append(f"Aprovação desfeita em {quando_txt(_quando(ap['em']))}. Não registre como aprovada.")
    elif situacao == "outra_versao":
        linhas.append(f"APROVAÇÃO DE OUTRA VERSÃO: a aprovação de {quando_txt(_quando(ap['em']))} foi "
                      f"feita sobre outro conteúdo ou outra prancheta ({ap.get('nome')}, versão "
                      f"{ap.get('conteudo')}), e não sobre esta ({versao_conteudo(c)}). Não registre como "
                      "aprovada: o plano mudou depois da aprovação, ou a URL é de outra rodada.")
    else:
        linhas.append("SEM APROVAÇÃO: a prancheta ainda não foi aprovada. Estas são as marcas até agora.")
    if snap.get("lido_em"):
        linhas.append(f"Lida de volta em {quando_txt(_quando(snap['lido_em']))}.")
    linhas += ["", "**O que mudou em relação à recomendação**", ""]
    mudou = []
    for i, m in snap["marcas"].items():
        r = reg[i]
        if m["tipo"] == "marco":
            if m["valor"]:
                sentido = "adiada" if m["valor"] > 0 else "antecipada"
                n = abs(m["valor"])
                det = f"Data · {r['rotulo']} {sentido} {n} dia{'s' if n > 1 else ''}"
                mudou.append(det + (f' · nota: "{m["nota"].strip()}"' if m["nota"].strip() else ""))
            continue
        if m["valor"] == r["padrao"] and not m["atalhos"] and not m["nota"].strip():
            continue
        det = f"{ROTULO[m['valor']]} · {r['rotulo']}"
        if m["valor"] == r["padrao"]:
            det = f"{ROTULO[m['valor']]} (como recomendado) · {r['rotulo']}"
        elif m["tipo"] == "opcao":
            det += " (era recomendada)" if r["padrao"] == "incluir" else " (fora da recomendação)"
        if m["atalhos"]:
            det += " · " + ", ".join(m["atalhos"])
        if m["nota"].strip():
            det += f' · nota: "{m["nota"].strip()}"'
        mudou.append(det)
    linhas += [f"- {x}" for x in mudou] or ["- Nada mudado: tudo segue como recomendado."]

    origem, lns = linhas_da_agenda(c["fases"])
    if lns:
        marcos = {i[2:]: m["valor"] for i, m in snap["marcas"].items() if m["tipo"] == "marco"}
        rec, efe = cronograma(lns, {}), cronograma(lns, marcos)
        fases = {f["id"]: f for f in c["fases"]}
        fixas = {df["id"]: df for df in (c.get("linha_do_tempo") or {}).get("datas_fixas", [])}
        andou = [i for i in efe if efe[i]["efetivo"]]
        if andou:
            linhas += ["", "**Cronograma depois das marcas**", ""]
            for i in andou:
                e, r = efe[i], rec[i]
                porque = "marca sua" if e["proprio"] else f"cascata de {fases[e['causa']]['rotulo']}"
                if e["proprio"] and e["causa"]:
                    porque = f"marca sua e cascata de {fases[e['causa']]['rotulo']}"
                linhas.append(f"- {fases[i]['rotulo']}: {periodo_txt(origem, e['ini'], e['fim'])} "
                              f"(era {periodo_txt(origem, r['ini'], r['fim'])}), {porque}")
        for i, e in efe.items():
            pz = fases[i]["agenda"].get("prazo")
            if pz:
                limite = (_data(fixas[pz]["data"]) - origem).days
                if e["fim"] > limite + 1e-9:
                    linhas.append(f"- Conflito: {fases[i]['rotulo']} termina depois da data fixa "
                                  f"\"{fixas[pz]['rotulo']}\" ({dia_txt(origem, limite)})")
    if c.get("perguntas"):
        linhas += ["", "**Respostas do chat**", ""]
        for n, p in enumerate(c["perguntas"], 1):
            r = snap["chat"].get(f"p{n}")
            if r:
                em = f" ({quando_txt(_quando(r['em']))})" if r.get("em") else ""
                if r.get("em") and ap and ap.get("aprovado") and _quando(r["em"]) > _quando(ap["em"]):
                    em += ", registrada depois da aprovação"
                linhas.append(f"- {n}. {p['titulo']}: {r['resposta']}{em}")
            else:
                linhas.append(f"- {n}. {p['titulo']}: sem resposta registrada")
    if snap.get("geral") and snap["geral"]["nota"].strip():
        linhas += ["", "**Comentário geral**", "", "> " + snap["geral"]["nota"].strip().replace("\n", "\n> ")]
    return "\n".join(linhas) + "\n"


# ------------------------------------------------------------------------------- montagem

def _corpo_root(css, arquivo):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    m = re.search(r":root\s*\{(.*?)\}", css, re.S)
    if not m:
        raise ValueError(f"{arquivo}: sem bloco :root")
    return m.group(1).strip()


def tokens_css(nome):
    """Claro em :root, escuro no prefers-color-scheme guardado e no data-theme, como o
    Artifact pede. Os dois temas precisam das séries, senão a linha do tempo sai sem cor."""
    claro_arq = GUIA_DIR / "tokens" / f"{nome}-claro.css"
    escuro_arq = GUIA_DIR / "tokens" / f"{nome}.css"
    claro = _corpo_root(claro_arq.read_text(encoding="utf-8"), claro_arq.name)
    escuro = _corpo_root(escuro_arq.read_text(encoding="utf-8"), escuro_arq.name)
    for corpo, arq in ((claro, claro_arq.name), (escuro, escuro_arq.name)):
        for var in ("--serie-1", "--serie-2"):
            if var not in corpo:
                raise ValueError(f"{arq}: falta {var}, que a linha do tempo usa (validada pela dataviz)")
    return (f":root{{{claro}}}\n"
            f"@media (prefers-color-scheme: dark){{:root:not([data-theme=\"light\"]){{{escuro}}}}}\n"
            f":root[data-theme=\"dark\"]{{{escuro}}}\n")


def json_no_html(obj):
    """JSON dentro de <script type="application/json">: nada que feche a tag ou vire marcação."""
    txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    for a, b in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"),
                 (" ", "\\u2028"), (" ", "\\u2029")):
        txt = txt.replace(a, b)
    return txt


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def main():
    ap = argparse.ArgumentParser(description="Monta a prancheta de aprovação de plano")
    ap.add_argument("--nome", required=True, help="slug da prancheta, minúsculas e hífens")
    # Sem default: a prancheta é de projeto, e o cwd da sessão quase nunca é o projeto.
    ap.add_argument("--dir", type=Path, required=True, help="raiz do projeto")
    ap.add_argument("--conteudo", type=Path,
                    help="JSON de conteúdo (padrão: docs/prancheta-<nome>/conteudo.json)")
    ap.add_argument("--estado", type=Path,
                    help="pasta do out_dir do ArtifactData, ou JSON com marcas, estado e chat")
    ap.add_argument("--tokens", choices=["neutro"], default="neutro",
                    help="só neutro na v1: é o único par claro e escuro com séries validadas")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not NOME.match(a.nome):
        print(f"ERRO: --nome `{a.nome}` fora do formato (minúsculas, dígitos e hífens)", file=sys.stderr)
        return 2
    raiz = a.dir.expanduser().resolve()
    pasta = raiz / "docs" / f"prancheta-{a.nome}"
    fonte = (a.conteudo.expanduser() if a.conteudo else pasta / "conteudo.json")
    if not fonte.is_absolute() and not fonte.exists():
        fonte = raiz / fonte
    try:
        bruto = json.loads(fonte.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"ERRO: conteúdo {fonte}: {e}", file=sys.stderr)
        return 2

    g, c = valida_conteudo(bruto)
    for av in g.avisos:
        print(f"AVISO: {av}", file=sys.stderr)
    if g.erros:
        print("ERRO de conteúdo, nada foi escrito:", file=sys.stderr)
        for e in g.erros:
            print("  " + e, file=sys.stderr)
        print("\nO formato está em references/prancheta.md e na tabela FORMA deste script.",
              file=sys.stderr)
        return 2

    modo, snap = "aberto", None
    if a.estado:
        est_path = a.estado.expanduser()
        if not est_path.is_absolute() and not est_path.exists():
            est_path = raiz / est_path
        try:
            est = carrega_estado(est_path)
        except (OSError, ValueError) as e:
            print(f"ERRO: estado {est_path}: {e}", file=sys.stderr)
            return 2
        erros, avisos, snap, situacao, posteriores = valida_estado(est, c, a.nome, versao_conteudo(c))
        for av in avisos:
            print(f"AVISO: {av}", file=sys.stderr)
        if erros:
            print("ERRO de estado, nada foi escrito:", file=sys.stderr)
            for e in erros:
                print("  " + e, file=sys.stderr)
            return 2
        print(resumo_md(c, snap, situacao, posteriores))
        if situacao != "aprovada":
            print(f"Situação: {situacao}. A versão aprovada não foi escrita.", file=sys.stderr)
            return 3
        modo = "aprovado"

    destino = pasta / f"prancheta-{a.nome}.html"
    if modo == "aberto" and destino.is_file() and '"modo":"aprovado"' in destino.read_text(encoding="utf-8"):
        print(f"ERRO: {destino.name} já é a versão aprovada, que é registro. Rodada nova é "
              "--nome novo, nunca reabrir esta.", file=sys.stderr)
        return 2

    try:
        tokens = tokens_css(a.tokens)
        tpl = TEMPLATE.read_text(encoding="utf-8")
    except (OSError, ValueError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    agora = datetime.now().astimezone()
    dados = {"versao": 1, "modo": modo, "nome": a.nome, "versao_conteudo": versao_conteudo(c),
             "gerado_em": agora.isoformat(timespec="seconds"),
             "chave_local": f"detonado:prancheta:{c['projeto']}:{a.nome}", "conteudo": c, "estado": snap}
    saida = (tpl.replace("{{TITULO}}", esc(c.get("titulo_curto") or c["titulo"]))
             .replace("{{TOKENS_CSS}}", tokens)
             .replace("{{DADOS}}", json_no_html(dados)))
    sobrou = re.findall(r"\{\{[A-Z_]+\}\}", saida)
    if sobrou:
        print(f"ERRO: placeholder sem valor: {', '.join(sorted(set(sobrou)))}", file=sys.stderr)
        return 2
    mb = len(saida.encode("utf-8")) / (1024 * 1024)
    if mb > LIMITE_MB:
        print(f"ERRO: {mb:.1f} MB passa do limite de {LIMITE_MB} MB do Artifact", file=sys.stderr)
        return 2

    if a.dry_run:
        print(f"[dry-run] prancheta {a.nome} ({modo}): {len(saida)} bytes, sairia em {destino}")
        return 0
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(saida, encoding="utf-8")
    rel = destino.relative_to(raiz) if destino.is_relative_to(raiz) else destino
    print(f"{rel} ({modo}): {len(saida)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
