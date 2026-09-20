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
- `section.phase#<fase>`: cabeçalho com tag, título, resumo e a caixa "Etapa concluída"
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
já renderizado. Uma fonte, dois comportamentos, que é a mesma ideia das imagens em base64.

O renderizador de markdown mora dentro do `build_artifact.py`, e não num módulo ao lado,
porque o `novo_projeto.py` copia aquele arquivo sozinho para cada projeto. Ele é da
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
python3 $P docs/guia-x/guia-x.html --fechar f1                    # caixa "Fase concluída"
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

Gera `guia-x.artifact.html` com as imagens em base64, e recusa acima de 16 MB. O CSP dos
Artifacts bloqueia host externo e caminho relativo, e libera fontes só do Google Fonts. A display
Cabinet Grotesk (Fontshare) cai para Inter, que já é o fallback do token.

Publicar é ação externa: só com ok do Bera na conversa. Primeira publicação: ferramenta Artifact
com título curto e estável, favicon fixo, descrição de uma frase, e a URL vai para o HANDOFF e o
SESSION. Republicação: a mesma ferramenta com a `url` registrada no HANDOFF, senão nasce um
segundo link e o que o Bera tem no iPhone para de refletir o progresso. Sem favicon novo na
republicação.

## Tokens e marca

`assets/guia/tokens/bera.css` traz os tokens do schema `bera` (v2.1.1, Atelier Técnico):
`#0A0A0A` de fundo, dourado `#E5B748` liderando no escuro, terracota `#D97757` apoiando, raio
zero, sem sombra, sem gradiente, Inter e JetBrains Mono. `neutro.css` é o fallback sem marca.
O `novo_projeto.py` inclui o escolhido inline (`--tokens bera|neutro`).

Trocar cor, tipo ou direção não é decisão desta skill. Direção nova passa pela `risca-de-giz`,
que carrega o schema em `<bancada>/design-schemas/` e roda o gate dele. Calibragem aprovada
volta para o schema, e daí para `tokens/bera.css`.

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
