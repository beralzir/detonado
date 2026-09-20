# Handoff: o mapa do projeto como opção do detonado

Escrito em 20/09/2026, no `~/projetos/predator-servidor-ia`, para a sessão que vai evoluir a
skill `detonado`. O Bera pediu que o mapa feito à mão naquele dia vire uma opção da skill, "ou um
pouco melhor organizado". Este arquivo é o ponto de partida dessa sessão. Ele diz o que existe, o
que foi feito à mão e precisa virar mecanismo, e o que melhorar no caminho.

## Qual skill conduz a mudança

O Bera falou em "fazer isso no gepeto". Para mudança em skill, a porta certa é a
`skill-builder`, que aplica o método Gepeto e envolve o `skill-creator` da Anthropic para a
mecânica. A `gepeto` é para agentes. Chamar com:

```
/skill-builder refatorar a detonado para ganhar o modo mapa, seguindo
~/workspace/detonado/handoffs/2026-09-20-mapa-do-projeto.md
```

Mudança em skill é mudança no starter-kit. Antes de aplicar, passar pelo checklist de
`~/workspace/starter-kit/CLAUDE.md` e relatar o que a avaliação encontrou.

## O que existe hoje, e onde

| O quê | Onde |
|---|---|
| O mapa feito à mão, fonte | `~/projetos/predator-servidor-ia/docs/mapa-projeto/mapa-projeto.html`, commits `cdaa7c5` e `0c9adeb` |
| O derivado publicado | `https://claude.ai/artifact/VSBA7DdZTkZtvCq8Ytp3zK`, versão 3. O `.artifact.html` está no gitignore, como os dos guias |
| A conversa que o gerou | Sessão de 20/09 à tarde, `daquele-jeito`, `https://claude.ai/code/session_014HxwwWyKZ5956hTuWXKB17` |
| Registro no projeto | Mapa dos documentos do `CLAUDE.md` e seção 10 do `HANDOFF.md` |

## Anatomia do mapa v1, de cima para baixo

1. **Cabeçalho.** Eyebrow com a data da foto e o nome do projeto, título, uma frase dizendo que é
   foto datada e que o estado vivo está nos guias.
2. **Tiles de progresso**, um por guia vivo do projeto: caixas marcadas, total, percentual, barra e
   uma linha de estado. No Predator foram quatro: servidor v2, personalização, Fase T, Fase C.
3. **Callout "Onde paramos".** Última sessão, o que fechou, o que a medição do dia encontrou, o
   próximo bloco. No v1 ficou em quatro parágrafos, longo demais.
4. **Fluxograma "O que trava o quê".** SVG inline. Nós são frentes abertas e decisões, arestas
   rotuladas com a dependência ("só depois do backup", "depois das etapas 1 a 3"). Três cores:
   fechada (acento cheio), trabalho do Claude (contorno), depende do Bera (laranja). Legenda.
5. **Timeline por fase.** SVG inline. Uma linha por fase ou frente, barra da abertura ao
   fechamento, contorno para aberta, tracejado para a fazer, marcador laranja para decisão do
   Bera com data. Eixo semanal, linha vertical "hoje". Legenda.
6. **"Pra onde vamos".** Lista numerada na ordem em que uma coisa destrava a outra, com chip de
   dono (Claude, você, decisão sua) e um parágrafo por item.
7. **"O que já está de pé".** Tabela frente, data de fechamento, prova em uma linha.
8. **Fontes e guias vivos.** Links para os artifacts dos guias e para HANDOFF, SESSION e plano
   de risco no GitHub. Rodapé com a data e a origem dos dados.

Sem checkbox, de propósito. O estado é dos guias vivos, e o mapa só lê.

## O que foi feito à mão e precisa virar mecanismo

Tudo abaixo foi digitado com dado colhido na conversa. Uma opção da skill não pode depender disso.

| Feito à mão no v1 | De onde o dado veio | O que a skill deveria fazer |
|---|---|---|
| Os tiles e os percentuais | `progresso.py --listar` rodado em cada guia | Descobrir `docs/guia-*/guia-*.html` e usar o `progresso.py` como biblioteca, não por shell |
| As datas da timeline | `git log --format='%ad %s' --date=short` lido a olho, cruzando a mensagem de commit com a fase | Ler `data-done` das fases fechadas e a data de criação do bloco de fase. Onde o guia não tem data, o git é fallback e o texto diz "sem registro" quando nem ele diz |
| As coordenadas dos SVGs | Calculadas: `x = 170 + dia * 19`, linhas a cada 34 px | Gerar a partir dos dados, com o eixo dimensionado pela janela do projeto |
| As dependências do fluxograma | Lidas do HANDOFF, seção 5.4, e do plano de risco | Precisa de dado declarado. Proposta: `data-depende="e-s1-7"` no bloco de fase ou de etapa, ou um `mapa.json` ao lado do guia. Sem dado, o fluxograma não sai e a skill diz por quê |
| O dono de cada item (Claude, Bera) | Coluna "O que depende de você" do HANDOFF | Já existe a convenção "pronto quando" com dono no `metodo.md`. Ler de lá |
| A tabela "O que já está de pé" | Memória da conversa | Fases com `data-done`, uma linha cada, com a prova do bloco de fase |

## Onde encaixar na skill

Recomendação: **modo próprio, chamado `mapa`**, e não uma opção do `retomar`. O `retomar` tem
contrato de resposta curta para celular, em até quatro linhas, e o mapa é o oposto disso. Gatilhos
a acrescentar na `description`: "detonado, desenha o mapa", "mapa do projeto", "detonado, onde
paramos, com mapa".

O que muda em cada arquivo:

| Arquivo | Mudança |
|---|---|
| `SKILL.md`, frontmatter | Gatilhos do modo mapa na `description`, mantendo o MANUAL-ONLY |
| `SKILL.md`, tabela de modos | Linha **mapa**: pedido típico, o que faz, "leia antes: `references/mapa.md`" |
| `SKILL.md`, Referências e scripts | Linhas de `references/mapa.md`, `scripts/mapa.py`, `assets/guia/mapa.template.html` |
| `references/mapa.md` | Novo. Anatomia das oito seções, o que é foto e o que é vivo, regras de honestidade das datas, quando o fluxograma não sai |
| `scripts/mapa.py` | Novo. Lê os guias e o git, gera `docs/mapa-<projeto>/mapa-<projeto>.html` a partir do template, com tokens inline. Sai 2 se não achar guia nenhum |
| `assets/guia/mapa.template.html` | Novo. Mesma linguagem visual do `guia.template.html`, mesmo contrato de tokens |
| `scripts/build_artifact.py` | Nada, se o template respeitar o contrato. Confirmar que ele deriva o mapa igual deriva o guia |
| `references/artefatos.md` | O mapa entra como sexto artefato, opcional, "apagável: sim, é foto" |
| `references/retomada.md` | Uma linha: quando o Bera pede "onde paramos" com visual, o modo é mapa |

## Melhorias sobre o v1, na ordem em que valem mais

1. **"Onde paramos" em três linhas, não em quatro parágrafos.** Última sessão com data, o que
   fechou, o próximo bloco. O resto já está nas outras seções.
2. **Fluxograma gerado de dependência declarada.** É a única parte que hoje não tem fonte de
   dado. Sem isso, o mapa é bonito e mentiroso na segunda semana.
3. **Timeline com sessões como marcos opcionais.** O Bera escolheu fases como unidade, mas
   "as duas camadas" estava na mesa. Um tique pequeno por sessão do SESSION.md, desligável.
4. **Tiles descobertos, não digitados.** Todo `docs/guia-*/` do projeto vira tile. Fase
   cancelada aparece como cancelada, não como aberta.
5. **Layout de celular para os SVGs.** No v1 o SVG tem `min-width: 560px` e rola na horizontal.
   Um layout empilhado abaixo de 520 px, ou a timeline virando lista, lê melhor no iPhone.
6. **Tema.** O v1 é só escuro, como os guias. Os Artifacts renderizam nos dois temas do
   visualizador. Decidir se o mapa segue os guias ou ganha os dois, e registrar.
7. **Um link só.** A primeira publicação registra a URL no HANDOFF, e republicar passa a URL,
   igual à regra do guia vivo. O v1 já fez isso.

## Regras que o modo deve carregar

- Foto datada. A data aparece no eyebrow, no rodapé e no nome do artifact.
- Sem checkbox. Se aparecer pedido de marcar algo no mapa, a resposta é "isso é no guia".
- Estado só do `progresso.py`. Percentual digitado é bug.
- Data só de `data-done` ou do git. Sem fonte, "sem registro", nunca estimativa.
- O derivado `.artifact.html` fica no gitignore, e a fonte é o HTML com caminho relativo.
- Portões de saída como no guia: sugerir anti-slop e `cão-guia` em texto, sem chamar.

## Evals mínimos, com erro plantado

1. **Predator, hoje.** Gerar o mapa no `~/projetos/predator-servidor-ia` e comparar com o v1 feito
   à mão. Os percentuais têm que bater com `progresso.py --resumo` de cada guia.
2. **Projeto sem git.** Um projeto aberto pelo `novo_projeto.py` numa pasta sem `.git`. A
   timeline tem que dizer "sem registro" nas datas, não inventar.
3. **Fase cancelada.** Guia da Fase T do Predator, que tem F2, F3 e F4 canceladas. O mapa não pode
   listar as três como abertas.
4. **Guia sem dependência declarada.** O fluxograma não sai, e a mensagem diz o que declarar.
5. **Erro plantado.** Um guia com `data-done` posterior a hoje. O script tem que recusar ou
   marcar, nunca desenhar uma barra no futuro como fechada.

## Como o v1 foi construído, para quem for reproduzir o desenho

- Fontes Inter e JetBrains Mono, tokens iguais aos do guia (`--bg #0A0A0A`, `--panel #121212`,
  acento `#E5B748`, apoio laranja `#D97757`, verde `#34D399`).
- SVG inline com `viewBox`, texto de 11 a 13 px, setas por `<marker>`, `role="img"` e
  `aria-label` com a mesma afirmação da legenda, `<figure>` com `<figcaption>`.
- Fluxograma: nós de 190 por 60 px em três colunas (x 40, 355, 670) e quatro linhas
  (y 30, 150, 270, 390), arestas ortogonais com rótulo curto.
- Timeline: coluna de rótulos até x 160, eixo de x 170 em diante a 19 px por dia, uma linha a
  cada 34 px, barra de 14 px, semana como linha de grade, "hoje" tracejado.
- Hook de design do `impeccable` marcou Inter e o callout com borda lateral. Os dois são o padrão
  dos guias e foram registrados como exceção em `.impeccable/config.json` do projeto, com motivo.
  O modo mapa deve carregar a mesma exceção ou o hook vai reclamar em todo projeto.
