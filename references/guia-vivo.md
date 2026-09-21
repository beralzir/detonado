# O guia vivo

Um HTML por projeto, ou por fase longa, que mostra o progresso real. O Claude atualiza o arquivo
por script, o Bera dá F5. Nasceu como Guia Predator (`design/guia-predator`, ago/2026) e virou
mecanismo no `guia-servidor-v2` (Fase D).

## Anatomia

Template em `assets/guia/guia.template.html`, bloco de fase em `assets/guia/fase.template.html`.
O `novo_projeto.py` monta o guia a partir dos dois e do JSON das fases.

- `nav` fixa à esquerda: rótulo Progresso, porcentagem (`#pct`), barra (`#fill`), lista de fases
  com um ponto por fase (`data-dot="<fase>"`) que acende quando a fase fecha. No estreito a nav
  vai para o topo.
- `header` com o hero (SVG line art ou imagem com `alt`), o bloco "Onde paramos"
  (`#status-atual`, com `data-v` da data) e o bloco "Como funciona".
- `section#retomada`: contexto, cartões (concluído antes, agora, vigilância), tabela de decisões.
- `section.phase#<fase>`: ao fechar, a seção ganha `data-fechada="DD/MM/AAAA"`, simétrico ao
  `data-cancelada`, e o `--reabrir` a tira. É a única fonte de data por fase: o `data-done`
  guarda o id da fase, não a data. Cabeçalho com tag, título, resumo e a caixa "Etapa concluída"
  (`.pdone`, `data-done="<fase>"`), depois `.checks` com uma `label` por etapa, cada uma com
  `<input type="checkbox" id="e-<fase>-<n>">` e o "pronto quando" em `<small>`.
- Blocos de comando `.cb` com `<pre tabindex="0">` e botão copiar. Caixas `.call` (`regra`, `aviso`,
  `perigo`, `ok`), cada uma com o rótulo em texto (`.lb`), porque a cor nunca é o único canal.
- Tabela sempre dentro de `<div class="tw" tabindex="0" role="group" aria-label="Tabela de ...">`:
  é o contêiner que rola no estreito, e precisa ser alcançável por teclado (axe
  `scrollable-region-focusable`).
- `footer` com data da última atualização (`#atualizado`) e o caminho do arquivo.
- `script` no fim: copiar, contar checkboxes, atualizar `#pct`, `#fill` e os pontos.

Estado é o atributo `checked`. Sem localStorage: o que está no arquivo é o que vale, e o arquivo
está no git. O campo de anotação por `db` não é exceção a isso: ele é transporte do que o Bera
escreve até virar commit, nunca um segundo lugar de progresso. Ver a seção do `db` abaixo.

A fonte é um documento completo (`<html lang="pt-BR">`, `head`, `body`), que é o que o navegador
local e o `cão-guia` esperam. O Artifact embrulha o conteúdo no esqueleto dele, então o
`build_artifact.py` tira as tags de embrulho do derivado e mantém o resto inteiro.

## Contrato dos tokens

O template consome só estas variáveis, e é isso que torna a marca trocável:

| Grupo | Variáveis |
|---|---|
| Superfícies | `--bg`, `--panel`, `--hov`, `--l1`, `--l2`, `--pre` |
| Texto | `--fg`, `--t1` a `--t5` (o `--t5` é o mínimo para texto pequeno, tem que medir 4,5:1 sobre `--bg`) |
| Acento e apoio | `--accent`, `--accent-tint`, `--accent-line`, `--accent-sel`, `--support`, `--support-text`, `--support-tint`, `--support-line` |
| Semântico | `--good`, `--good-tint`, `--good-line`, `--bad`, `--bad-tint`, `--bad-line` |
| Fundo | `--grid-svg`, a grade em SVG inline. Gradiente não entra, nem para desenhar linha |
| Tipo e forma | `--sans`, `--mono`, `--display`, `--radius` |

## Documento do repo embutido no guia

O guia referencia arquivos o tempo todo (`HANDOFF.md`, `discovery.md`, um `lessons.md`), e
sair da página para lê-los quebra o fluxo. Um link marcado com `class="doc"` resolve:

```html
<a class="doc" href="../../HANDOFF.md">HANDOFF.md</a>
```

No navegador local continua sendo link relativo que funciona. No derivado, o
`build_artifact.py` lê o arquivo e troca por um `<details>` com o conteúdo dentro, markdown
já renderizado. Uma fonte, dois comportamentos.

O renderizador de markdown mora dentro do `build_artifact.py`, e não num módulo ao lado. O
motivo era a cópia por projeto, que acabou em 21/09/2026: hoje o projeto recebe um invocador
de três linhas e a skill é a fonte única. Ele é da
biblioteca padrão: puxar lib de CDN quebraria o guia offline e instalar pacote daria
dependência a uma skill que hoje não tem nenhuma. Cobre título, negrito, itálico, código,
cerca, tabela, lista, citação, link e regra. O que não reconhece vira parágrafo, nunca erro.

Extensão fora da lista, ou arquivo que não existe, fica como link e o script avisa e sai 1,
igual a imagem faltando. Documento grande pesa: o `HANDOFF.md` do Predator são 46 KB de
markdown que viram 59 KB de HTML. O limite de 16 MB do Artifact é longe, mas embutir tudo
sem critério faz a página abrir devagar. Embuta o que a fase pede para ler.

## Anotação do Bera dentro do guia, com `db`

Cada fase tem um campo de anotação que grava na capability `db` do Artifact. Serve para o
Bera responder e anotar sem sair da página, e para o Claude ler depois com `read_db` e levar
para o markdown do repo.

**O `db` é transporte, não estado, e essa distinção é a regra.** O progresso continua sendo o
atributo `checked` deste arquivo, em git, mexido só pelo `progresso.py`. O `db` guarda o que
o Bera digitou até virar commit no markdown, e aí o dono volta a ser o arquivo. Sem isso
viram dois lugares dizendo a mesma coisa, que é exatamente o que este método existe para
evitar.

Para ligar, publique com `capabilities: {db: {}}`. Sem essa declaração, ou abrindo o HTML
local, `claude.use('db')` devolve `null`, o campo desabilita e diz por quê, em vez de fingir
que salvou. Nada de segredo ali: o armazenamento é compartilhado por quem abre o artifact.

Para trazer de volta:

```
Artifact action:"read_db" url:<a do guia> db_op:"list" collection:"notas"
```

## Atualizar

```bash
P=~/.claude/skills/detonado/scripts/progresso.py
python3 $P docs/guia-x/guia-x.html --listar                       # estado, avisos de consistência
python3 $P docs/guia-x/guia-x.html --resumo                       # uma linha, para o bloco de sanidade
python3 $P docs/guia-x/guia-x.html --marcar e-f1-2 --prova "curl -i: HTTP/2 200 do 5G"
python3 $P docs/guia-x/guia-x.html --declarar e-f1-4              # "declarado pelo Bera, sem prova", caixa fica aberta
python3 $P docs/guia-x/guia-x.html --fechar f1                    # caixa "Fase concluída" e data-fechada
python3 $P docs/guia-x/guia-x.html --reabrir f1 --desmarcar e-f1-3   # prova falsa: reabre a fase antes de desmarcar
python3 $P docs/guia-x/guia-x.html --inserir-fase fases.json      # fase nova, nav e seção, do mesmo JSON de metodo.md
python3 $P docs/guia-x/guia-x.html --onde-paramos "**02/09**: \`podman ps\` com Up, porta 4533 em aberto"
python3 $P docs/guia-x/guia-x.html --carimbar 02/09/2026          # data em #status-atual e no rodapé
```

O script recusa id inexistente e fase repetida (sai 2), avisa fase fechada com etapa aberta (sai
1 quando nada foi alterado), recusa declarar etapa já marcada, e imprime o progresso depois de
cada operação. `--onde-paramos` carimba a data de hoje sozinho se `--carimbar` não vier junto.
**`--marcar` sem `--prova` sai com 2**: a evidência entra no guia junto com a caixa, numa nota
datada simétrica à da declaração. Sem evidência, o caminho é `--declarar`, que deixa a caixa
aberta.

O que sobra para edição à mão é a prosa livre das seções: parágrafos, tabelas, blocos de comando,
cartões da seção Contexto. Depois de editar, `--listar` tem que sair limpo. `checked` e `data-done`
nunca se tocam à mão.

O guia e o HANDOFF dizem a mesma coisa, com a mesma data.

## Publicar

```bash
python3 docs/guia-x/build_artifact.py
```

Gera `guia-x.artifact.html` e recusa acima de 16 MB. O CSP dos Artifacts bloqueia host
externo e libera fontes só do Google Fonts. A display Cabinet Grotesk (Fontshare) cai para
Inter, que já é o fallback do token.

**A imagem sobe como arquivo ao lado da página, e o script imprime o mapa pronto.** No fim da
execução sai um bloco `PUBLIQUE COM`, com o `root` e o `files` para passar ao publish. Publicar
sem esse mapa deixa a página sem imagem nenhuma, então ele não é detalhe, é a saída do script.
Numa republicação em que a imagem não mudou o mapa pode ser omitido, porque arquivo não
reenviado é mantido.

**Por que não base64, e a medida que decidiu.** Até 20/09/2026 o script embutia imagem como
data URI, por uma premissa que envelheceu: a de que o CSP não servia caminho relativo. Serve,
desde que o arquivo suba junto. Medido no guia do Linux em 21/09/2026: **968 KB com base64
contra 54 KB sem**, e o custo real não era o byte, era a releitura. O publish obriga a ler a
versão publicada inteira antes de sobrescrever, e 94% do que se lia era pixel que nunca muda.

Publicar é ação externa: só com ok do Bera na conversa. Primeira publicação: ferramenta Artifact
com título curto e estável, favicon fixo, descrição de uma frase, e a URL vai para o HANDOFF e o
SESSION. Republicação: a mesma ferramenta com a `url` registrada no HANDOFF, senão nasce um
segundo link e o que o Bera tem no iPhone para de refletir o progresso. Sem favicon novo na
republicação.

## Tokens e marca

`assets/guia/tokens/bera.css` traz os tokens do schema `bera` (v2.3.2, Atelier Técnico):
`#0A0A0A` de fundo, dourado `#E5B748` liderando no escuro, terracota `#D97757` apoiando, raio
zero, sem sombra, sem gradiente, Inter e JetBrains Mono. `neutro.css` é o fallback sem marca.
O `novo_projeto.py` inclui o escolhido inline (`--tokens bera|neutro`).

Trocar cor, tipo ou direção não é decisão desta skill. Direção nova passa pela `risca-de-giz`,
que carrega o schema em `<bancada>/design-schemas/` e roda o gate dele. Calibragem aprovada
volta para o schema, e daí para `tokens/bera.css`.

### O que a v2.3.2 mudou, em 20/09/2026

O arquivo estava na v2.1.1 enquanto o schema já estava na v2.3.2, e por isso todo guia nascia
fora da marca. Quatro trocas, todas com a linha do schema que as manda:

- **Positivo passa do verde `#34D399` para o teal `#28BDB1`.** O schema diz "Positivo é o próprio
  teal". Mede 8,03:1 sobre `--panel`, contra 9,74:1 do verde, e os dois passam AA.
- **A grade de fundo passa de terracota para teal.** Guardrail: "overlay de grade de 12 colunas
  em 4 a 10% da cor de apoio (teal)".
- **A display passa de Cabinet Grotesk para Versos**, e o corpo também. Guardrail: "Nunca usa a
  fonte de sistema nem a fonte da v2.0 como display". A Inter era o corpo até a v2.0 e sai dos
  dois papéis.
- **A terracota desce para `--support`**, na variante suave `#E8977C`, porque no escuro ela deixou
  de ser apoio e virou terceira série.

**Ressalva de licença, e ela decide onde a fonte pode morar.** A Versos é da Fabio Haag Type,
modalidade Individual: webfont sim, não repassar o arquivo. **Este repo é público**, então o
`woff2` não entra aqui e não há `@font-face` com caminho relativo. Em máquina sem a Versos o
texto cai para a `system-ui` declarada, que é o que a "Ressalva de ambiente" do schema prevê.
Peça que precise da fonte de verdade a embute como data URI no próprio HTML, e só em repo
privado. O `woff2` do Bera vive em `~/workspace/hub-pessoal/marca/brand-guide/fonts/`.

**Achado aberto, a devolver ao schema.** O aviso (`--support-text`, `#E8977C`) e o perigo
(`--bad`, `#F87171`) colidem sob deuteranopia: ΔE 4,5 pelo `cor.py` do `cão-guia`, abaixo do
limiar de colisão de 10. O defeito já existia na v2.1.1 e não nasceu na troca. Nenhuma terracota
resolve: a cheia `#D97757` também colide (ΔE 8,3) e a `#C1502B` reprova contraste AA sobre o
painel. O schema não define cor de aviso, só acento, apoio, positivo e negativo. Enquanto a
decisão não vem, os dois callouts se separam pelo rótulo em texto, que o template já traz, e a
peça não comunica só por cor.

## O que não entra

Gradiente, sombra, canto arredondado, preto ou branco puros, fotografia, emoji como ícone, ícone
de CDN, travessão como pontuação. São os guardrails da marca, e cada um já apareceu num guia
"moderno" de boa-fé.

## Acessibilidade e leitura

- `alt` em toda imagem, descrevendo o que a imagem mostra. As doze do Guia Predator nasceram
  sem, e é a primeira coisa que o `cão-guia` pega.
- Contraste medido, com o veredito WCAG ao lado. `code` inline no tema claro sobre a segunda
  superfície reprova em AA por 0,17: use a primeira.
- Foco visível nos checkboxes e nos botões. `accent-color` no checkbox.
- Tabela larga rola dentro do próprio contêiner. A página nunca rola de lado.
- No iPhone: uma coluna, nav no topo, botão copiar alcançável com o polegar.
- `prefers-reduced-motion` desliga a transição da barra.

## Portões de saída

Depois de gerar ou mudar a estrutura do guia, dois portões, nesta ordem, os dois manual-only:

1. Anti-slop: `npx impeccable@4.1.0 detect <guia.html>`. A versão vai fixa porque `npx` sem
   versão resolve da rede a cada chamada, e aí o portão deixa de ser reprodutível.
2. `cão-guia`: acessibilidade, contraste, `alt`.

Nomeie os dois em texto e espere o Bera chamar. Portão dispensado se registra na entrega, não se
omite. Atualização de checkbox e texto de status não reabre os portões.

## Fase cancelada

Nasceu em 11/09/2026, no `predator-servidor-ia`. A Fase T avaliava trocar de distro em cinco
fases. A F1, o discovery, respondeu a pergunta inteira antes das outras: nenhum incômodo do
Bera exigia outra distro. Com isso a **F3**, live USB das candidatas, e a **F4**, partição de
teste, perderam o motivo de existir, porque não havia mais candidata. Dez caixas que nunca
seriam marcadas.

O guia não tinha como dizer isso. Fechar as duas mentiria, e o próprio `progresso.py` recusa:
sai com 1 e avisa `fase f3 fechada com etapa aberta`. Deixar abertas fazia a barra marcar 29%,
como se o projeto estivesse no começo, quando na verdade ele tinha acabado.

```bash
progresso.py GUIA.html --cancelar f3 f4 --motivo "a F1 respondeu antes, e mais barato"
```

O que acontece:

- Os checkboxes da fase **somem**, e as etapas viram lista estática com o "pronto quando" de
  cada uma, que é justamente o registro do que se perdeu ao cancelar.
- A fase ganha `data-cancelada="DD/MM/AAAA"` e um bloco de aviso com o motivo.
- A caixa "Fase concluída" vira o texto "Fase cancelada".
- A linha da navegação lateral fica riscada, com a etiqueta CANCELADA.

**Por que tirar as caixas em vez de marcar um atributo.** Quem conta o percentual são dois
lados: este script e o `<script>` dentro da própria página, que faz
`querySelectorAll('input[type=checkbox]')`. Um atributo novo só o script entenderia, e a barra
da página passaria a discordar do `--resumo`. Tirando as caixas, os dois contam igual sem
ninguém mexer no JS, e isso vale também para **guia já publicado**, que não conhece classe de
CSS nova. Pelo mesmo motivo o estilo é inline: injetar CSS em arquivo publicado é mais
invasivo que a mudança em si.

**É destrutivo, e não tem `--descancelar`.** Desfazer é `git checkout` no guia. Cancelar uma
fase é decisão, não conserto, e decisão volta pelo histórico.

**`--motivo` é obrigatório.** Fase que morre sem motivo escrito vira, em um mês, exatamente a
caixa órfã que este comando existe para evitar.
