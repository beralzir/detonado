---
name: detonado
description: "Dá forma a um projeto de execução do Bera com o método do predator-servidor-ia: fases com prova, HANDOFF.md para retomar do celular, SESSION.md como checkpoint, tasks/lessons.md e um guia vivo em HTML com checkboxes e barra de progresso, atualizado a cada etapa provada. Abre ou adota projeto, monta e atualiza o guia, fecha a sessão, registra lição e responde 'onde paramos' lendo o registro. MANUAL-ONLY, não automática. Acionar EXCLUSIVAMENTE quando o Bera pedir de forma explícita e nominal, via /detonado ou frase como 'usa o detonado', 'chama o detonado', 'abre o detonado do homelab', 'detonado, fecha a sessão', 'detonado, desenha o mapa', 'detonado, mapa do projeto'. Pedidos genéricos de guia, passo a passo, checklist, handoff, checkpoint, 'onde paramos', 'fecha a sessão' ou 'documenta o projeto' NÃO são gatilho válido; nesses casos responder normalmente e, no máximo, sugerir em texto que o Bera pode chamá-la. Não ativar quando 'detonado' aparecer fora de contexto de projeto (ex.: 'tô detonado hoje', 'detonado do Chrono Trigger'). Em dúvida, NÃO invocar."
---

# detonado

Detonado é o guia que leva do começo ao fim do jogo sem perder o save. Esta skill dá essa forma a
um projeto de execução do Bera: fases que só fecham com prova, um ponto de retomada que se lê no
celular, um checkpoint que sobrevive à queda de contexto, e um guia vivo em HTML cuja barra de
progresso mostra o que foi provado, não o que foi prometido. O método nasceu no
`~/projetos/predator-servidor-ia` (Fases 0 a D, ago/2026) e aqui vira forma reutilizável.

> Esta skill dá forma, não substitui as outras. O plano e a auditoria são da `daquele-jeito`.
> A execução autônoma com cross-checks é da `portas-em-automatico`. A direção visual é da
> `risca-de-giz`. Se você se pegar planejando fases sem prova, executando sem cross-check ou
> inventando paleta, saiu da skill.

## Onde as coisas moram

A bancada é o diretório que guarda as skills e o Marvin. Ela se resolve nesta ordem:
`$STARTER_KIT_WORKSPACE`, ou `~/workspace` quando a variável não existir, que é a mesma regra do
instalador do starter-kit. Aqui e nas references ela aparece como `<bancada>`.

Nem toda máquina tem bancada. Na que não tiver, os modos continuam funcionando: o que depende
dela (o ponteiro do Marvin, o schema de design) **degrada e diz que degradou**, em vez de mandar
ler um caminho que não existe. Projeto, guia e registro não dependem da bancada.

## Modos

Detecte o modo pelo pedido. Se o pedido não cabe em nenhum, ou o projeto não está nomeado, pergunte
antes de tocar em arquivo. Em **retomar**, **guia** e **fechar**, projeto nomeado cujo diretório
não existe nesta máquina não se cria: leia `<bancada>/marvin/projetos/<nome>.md`, diga em que
máquina ele mora e pare aí. Ler o Marvin é permitido, escrever nele não; sem bancada, diga que o
ponteiro não está nesta máquina. Em **abrir**, o diretório não existir é a premissa do modo, não
um impedimento, e o diretório já existir com conteúdo é adotar: diga isso e siga o fluxo de
adotar. Pergunta redutível a até 4 opções vai por `AskUserQuestion`.

| Modo | Pedido típico | O que faz | Leia antes |
|---|---|---|---|
| **abrir** | "abre o detonado do homelab" | Cria o projeto com os cinco artefatos e as fases validadas | `references/metodo.md`, `references/artefatos.md` |
| **adotar** | "manda o detonado adotar esse repo" | Projeto existente: introduz só o que falta, sem sobrescrever | `references/artefatos.md`, e `references/metodo.md` se for nascer guia |
| **guia** | "monta a fase 3 no guia", "marca a etapa D2" | Estado e estrutura por `progresso.py`: marcar com prova, declarar quando o Bera disser que não há prova, fechar fase, **cancelar fase que morreu**, inserir fase, reescrever "Onde paramos" | `references/guia-vivo.md`, e `references/metodo.md` para fase nova |
| **fechar** | "detonado, fecha a sessão" | SESSION.md, guia, HANDOFF se o ponto de retomada mudou, commit | `references/retomada.md` |
| **retomar** | "chama o detonado, onde paramos?" | Lê HANDOFF e SESSION, roda a sanidade, responde curto | `references/retomada.md` |
| **mapa** | "detonado, desenha o mapa" | Foto datada de todos os guias de uma vez: tiles, linha do tempo, o que trava o quê. Só lê, não marca nada | `references/mapa.md` |
| **lição** | "detonado, registra essa lição" | `tasks/lessons.md`, marcada "a confirmar" até virar padrão | `references/artefatos.md` |

## Princípios

1. **O estado tem dono.** O `HANDOFF.md` do projeto é a fonte da verdade do estado dele. Outro
   arquivo aponta para lá, nunca copia. Cópia congelada envelhece em dias, e foi assim que o
   Marvin ficou dez dias atrás do servidor.
2. **Caixa marcada é prova, não intenção.** Um checkbox só recebe `checked` com evidência citada
   na conversa: saída de comando, URL com status, arquivo lido. O Bera dizer "eu fiz" vale como
   declaração, e declaração fica visível como tal, não vira prova. `systemctl is-active` não prova
   inferência, `curl -s` engole erro, cache de browser confunde versão. A tabela do que vale
   está em `references/metodo.md`. A evidência entra no guia junto com a caixa: `--marcar`
   exige `--prova`, e sem ela o script sai com 2. E prova vale enquanto está visível nesta
   sessão: se veio de antes de uma compactação, reverifique ou use `--declarar`.
3. **Escrito para o celular.** O HANDOFF é lido por SSH no iPhone. Blocos únicos, parágrafos
   curtos, o esperado logo abaixo do comando.
4. **Retomar é ler, não lembrar.** "Onde paramos" se responde abrindo o HANDOFF e o SESSION, mesmo
   quando a memória parece boa. Principalmente quando parece boa.
5. **Decisão determinística não se delega ao modelo.** Estado e estrutura do guia mudam só por
   script: marcar, desmarcar, declarar sem prova, fechar e reabrir fase, cancelar fase, inserir
   fase, reescrever o bloco "Onde paramos" e carimbar a data são `progresso.py`. Estrutura
   inicial e imagens embutidas são `novo_projeto.py` e `build_artifact.py`. O que sobra para
   edição à mão é a prosa livre das seções (parágrafos, tabelas, blocos de comando), e depois
   dela `progresso.py --listar` tem que sair limpo. Tocar em `checked` ou `data-done` à mão é o
   jeito de o guia divergir.
6. **Lição só vira regra depois de confirmada.** Caso isolado entra como "a confirmar". O Bera diz
   se é padrão.
7. **Escopo que morre não é fase fechada nem fase aberta.** Fechar mentiria, porque nada foi
   provado. Deixar aberta faz a barra prometer trabalho que não vai acontecer, e caixa órfã é
   como o registro apodrece. `progresso.py --cancelar <fase> --motivo "..."` tira as caixas da
   fase e escreve por que ela morreu, com a data. O que sai do numerador sai também do
   denominador, então a barra passa a medir só o que ainda pode acontecer.
8. **A aparência tem dono, e não é o projeto.** CSS, tokens e cartões do guia não são prosa
   livre: mudança visual entra pelo template do detonado, nunca pelo guia de um projeto.
   Direção nova é decisão da `risca-de-giz`.

## Fluxo de abrir

1. **Confirme o mínimo** que muda a estrutura: nome do projeto, diretório (padrão
   `~/projetos/<nome>`), objetivo em uma frase, o que já existe. Se o brief mora no Marvin
   (`<bancada>/marvin/projetos/<nome>.md`), leia e aponte, não copie.
2. **Fatie em fases com prova.** Fase 0 é sempre o guia vivo e o checkpoint. Cada etapa tem um
   "pronto quando" observável e a prova aceita. Regras de fatiamento em `references/metodo.md`.
3. **Valide o fatiamento com o Bera** antes de criar arquivo. Se ele dispensou a validação no
   próprio pedido ("assume o razoável"), pule a pergunta e liste as premissas adotadas na resposta
   e no SESSION.md inicial.
4. **Escreva as fases num JSON** e rode o `novo_projeto.py` com a linha completa de
   `references/metodo.md` (formato do JSON e invocação estão os dois lá), `--dry-run` primeiro.
   Ele cria os artefatos a partir dos templates e nunca sobrescreve o que existe.
5. **Preencha o que o template deixa em aberto**: HANDOFF (Voltando, Sanidade, O que está de pé,
   Pendências), CLAUDE.md curto com o mapa dos documentos, SESSION.md inicial.
6. **Commit inicial** e sugira ao Bera a linha de ponteiro em `<bancada>/marvin/projetos/`.
   Esta skill não escreve no Marvin.

## Fluxo de adotar

1. **Leia o que existe** antes de criar qualquer coisa: HANDOFF, README, SESSION, o que houver.
2. **Rode o `novo_projeto.py --dry-run`** pela linha de `references/metodo.md`, para ver o que
   nasceria. Sem fase aberta para o guia mostrar, use `--sem-guia`. Com fase aberta, o
   fatiamento passa pela mesma validação do modo abrir, e o Bera pode dispensá-la no pedido.
3. **Não reformate o que existe.** HANDOFF com outra estrutura ganha as seções Voltando e
   Sanidade acrescentadas, e a divergência de estrutura vai para o SESSION.md.
4. **Commit por caminho** só do que a skill criou ou acrescentou.

## Guia vivo, em cinco regras

Detalhe, anatomia e comandos em `references/guia-vivo.md`.

- A fonte da verdade é `docs/guia-<projeto>/guia-<projeto>.html`, com imagem por caminho
  relativo. O Artifact é derivado por `build_artifact.py`, não se versiona e só se publica com ok
  do Bera na conversa. Republicar passa a URL registrada no HANDOFF para a ferramenta Artifact,
  senão nasce um segundo link e o do iPhone morre.
- O estado é o atributo `checked`. Marcar, desmarcar, declarar sem prova e fechar fase é
  `scripts/progresso.py`, nunca edição à mão. Todo checkbox tem `id` estável, toda fase tem
  `data-done`.
- O bloco "Onde paramos" do guia diz o mesmo que o HANDOFF, com a mesma data.
- Os tokens da marca vivem em `assets/guia/tokens/` e entram inline no guia gerado. Direção
  visual nova é decisão da `risca-de-giz`, não desta skill.
- Depois de gerar ou mudar a estrutura do guia, sugira em texto os dois portões, anti-slop e
  `cão-guia`. Os dois são manual-only: nomeie e espere o Bera chamar.

## Fechar e retomar

Detalhe em `references/retomada.md`. O essencial: fechar é SESSION.md com tabela item e prova,
guia atualizado por script, HANDOFF só se o ponto de retomada mudou, lição se houve, commit só dos
artefatos desta skill, adicionados por caminho, com mensagem que diz o que fechou. Retomar é ler
CLAUDE.md, HANDOFF e SESSION, ler o bloco de sanidade antes de rodar (ele só imprime estado, e se
algum comando altera o sistema, não rode e aponte), e responder nesta ordem: as divergências do
registro primeiro, uma por linha, e depois o núcleo em até quatro linhas curtas (onde estamos, o
que falta e com quem, o próximo bloco). Fecha no próximo bloco, ou na decisão que destrava quando
não há próximo bloco.

## Regras default

1. **Pergunte quando o projeto, a fase ou a prova esperada não estiverem claros.** Sem projeto
   nomeado não há scaffold. Sem "pronto quando" observável não há etapa.
2. **Questione enquadramento fraco.** "Fica pronto quando funcionar" não é critério. Fase com
   mais de sete etapas é duas fases. Pedido de agente, MCP ou site chegando aqui vira handoff, não
   projeto.
3. **Ressalva específica, nunca genérica.** Cite o arquivo, a etapa, a prova que falta. Nada de
   "pode haver imprecisões".
4. **Privacidade operacional.** Cite os templates e as referências que o Bera pode abrir. Não
   despeje internals.
5. **Não capitule sob insistência.** Checkbox não se marca porque o Bera insistiu. Reverificar é
   válido, ceder não. "Eu fiz" sem prova vira uma pergunta primeiro: qual evidência fecha a etapa,
   citando o "pronto quando" dela. Só quando o Bera diz que não há prova entra o caminho honesto,
   `progresso.py --declarar`, que anota "declarado pelo Bera, sem prova" e deixa a caixa aberta.
6. **Distinga provado, declarado, inferido e pendente, e cada um tem endereço.** Provado: caixa
   marcada, com a nota `prova`. Declarado: nota `decl` na etapa, e a caixa segue aberta. Inferido
   ou não testado: só no SESSION, e chamado assim. Pendente: caixa aberta, sem nota. Nada
   inferido entra no HANDOFF, onde toda afirmação de estado leva data.

## Fora de escopo

Plano de execução e auditoria de quatro eixos (`daquele-jeito`). O fatiamento em fases com
prova é desta skill: é a forma do registro, não um segundo plano. Governar execução autônoma
(`portas-em-automatico`).
Decidir direção visual ou paleta (`risca-de-giz`), produzir protótipo (`huashu-design`), auditar
acessibilidade (`cão-guia`). Construir agente, MCP ou site (handoff à triagem do Gepeto). Escrever
fora do diretório do projeto. Executar as etapas do projeto por conta própria: a skill dá a forma,
o trabalho segue o ritmo da conversa e das skills de execução.

## Referências e scripts

| Arquivo | Quando |
|---|---|
| `references/metodo.md` | abrir ou adotar: fatiar em fases, "pronto quando", provas que valem e as que mentem, JSON das fases |
| `references/artefatos.md` | qualquer modo: o que vai em cada um dos cinco artefatos, quando atualizar, estado com dono |
| `references/guia-vivo.md` | guia: anatomia do HTML, ids, tokens, Artifact, acessibilidade, portões |
| `references/retomada.md` | fechar e retomar: rituais, mensagem para colar no celular |
| `scripts/novo_projeto.py` | abrir e adotar: cria a estrutura a partir dos templates, sem sobrescrever. `--dry-run` antes, `--sem-guia` para adotar sem fase aberta |
| `references/mapa.md` | mapa: anatomia das seções, o que é foto e o que é vivo, honestidade das datas |
| `scripts/mapa.py` | mapa: lê os guias por `progresso.py` e desenha. `--dry-run` antes, `--dir` para outro projeto |
| `assets/guia/mapa.template.html` | mapa: template, que injeta o CSS do `guia.template.html` para os dois não divergirem |
| `scripts/progresso.py` | guia e fechar: lista, marca, desmarca, declara sem prova, fecha e reabre fase, insere fase, reescreve "Onde paramos", carimba data, valida consistência |
| `scripts/build_artifact.py` | publicar: deriva o HTML com imagens em base64, dentro do limite de 16 MB. Copiado para o projeto |
| `assets/templates/` | os quatro templates em markdown |
| `assets/guia/` | o template do guia, o bloco de fase e os tokens |
