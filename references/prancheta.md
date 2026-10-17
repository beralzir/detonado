# A prancheta de aprovação de plano

Um plano grande não cabe em quatro perguntas clicáveis, e um plano aprovado sem que o Bera veja
cada passo é aprovado no escuro. A prancheta é a página onde ele lê o plano inteiro, marca só o
que quer mudar e aprova com confirmação, e de onde o Claude lê de volta o que foi marcado, sem
o Bera digitar nada de novo. Nasceu de um quadro real de aprovação usado em 17/10/2026, num
projeto de conteúdo restrito. Daquele quadro entraram aqui só a estrutura, a mecânica e o
desenho.

## Quando usar, e quando não

Use quando o plano tem passos demais para o chat, decisões por passo, opções a somar,
premissas que valem se ninguém vetar e datas que o Bera pode querer mover.

Não use para:

- **Fazer o plano.** O plano vem da `daquele-jeito` ou do fatiamento de `references/metodo.md`.
  A prancheta dá forma à aprovação dele.
- **Decidir uma questão só.** Isso é consultivo (`references/documentos.md`).
- **Acompanhar progresso.** Isso é o guia vivo. A prancheta não tem caixa de etapa feita, e
  aprovar um passo não é provar o passo.
- **Plano curto.** Se cabe em até quatro perguntas, pergunte no chat e pronto.

## Rodar

```bash
P=~/.claude/skills/detonado/scripts/prancheta.py
python3 $P --nome rodada-2 --dir ~/projetos/x --dry-run
python3 $P --nome rodada-2 --dir ~/projetos/x
python3 $P --nome rodada-2 --dir ~/projetos/x --estado docs/prancheta-rodada-2/lido --dry-run
python3 $P --nome rodada-2 --dir ~/projetos/x --estado docs/prancheta-rodada-2/lido
```

Sem `--conteudo`, o script lê `docs/prancheta-<nome>/conteudo.json` e escreve
`docs/prancheta-<nome>/prancheta-<nome>.html`. O `--dir` é obrigatório: a prancheta é de
projeto. Exemplo completo de conteúdo, com o projeto fictício das fixtures:
`evals/fixtures/prancheta-exemplo.json`.

| Saída | Quer dizer |
|---|---|
| 0 | gerou, ou validou no `--dry-run` |
| 2 | conteúdo ou estado reprovado, nada escrito |
| 3 | estado válido sem aprovação em dia (pendente, desfeita ou com marca posterior), resumo impresso, nada escrito |

## O ciclo

1. **Conteúdo.** Escreva o plano em `docs/prancheta-<nome>/conteudo.json` (formato abaixo).
   A recomendação é o padrão de cada controle, então o JSON diz o que você recomenda.
2. **Montar.** `prancheta.py --dry-run`, depois sem. Confira o tamanho em bytes.
3. **Publicar, só com ok do Bera.** `python3 ~/.claude/skills/detonado/scripts/build_artifact.py
   docs/prancheta-<nome>/prancheta-<nome>.html` gera o derivado, e ele sobe pela ferramenta
   Artifact com `capabilities: {db: {}, user: {}}`. Registre a URL e o `sha256` onde o projeto
   cita a prancheta (SESSION.md, e o HANDOFF se ela muda o ponto de retomada).
4. **Sondar o `db`** logo depois da primeira publicação, e dizer ao Bera numa linha o que foi
   exercitado:

   ```
   ArtifactData action:"set"    url:<url> collection:"sonda" doc_id:"teste" data:{"em":"<agora>"}
   ArtifactData action:"get"    url:<url> collection:"sonda" doc_id:"teste"
   ArtifactData action:"delete" url:<url> collection:"sonda" doc_id:"teste" if_version:<a lida>
   ArtifactData action:"list"   url:<url> collection:"marcas"
   ```

   A lista de `marcas` sai vazia: nada se grava ao abrir, e o Claude nunca marca em nome do Bera.
5. **Perguntas do chat.** As até quatro perguntas espelhadas na prancheta vão por
   `AskUserQuestion`, com a mesma redação e a recomendação marcada. A aprovação não é uma delas:
   ela é ato da prancheta. Cada resposta entra no `db`, para aparecer na prancheta com a hora:

   ```
   ArtifactData action:"set" url:<url> collection:"chat" doc_id:"p1"
     data:{"pergunta":1,"resposta":"<a opção escolhida>","em":"<agora>","registrado_por":"claude"}
   ```

6. **O Bera marca e aprova** na prancheta, com confirmação em dois cliques. Espere o pedido
   ("detonado, lê a prancheta").
7. **Ler de volta**, sempre para uma pasta, para o script ler o que o `db` tem e ninguém
   transcrever marca:

   ```
   ArtifactData action:"list" url:<url> collection:"marcas" query:{"limit":1000} out_dir:"<projeto>/docs/prancheta-<nome>/lido"
   ArtifactData action:"list" url:<url> collection:"estado" out_dir:"<projeto>/docs/prancheta-<nome>/lido"
   ArtifactData action:"list" url:<url> collection:"chat"   out_dir:"<projeto>/docs/prancheta-<nome>/lido"
   python3 $P --nome <nome> --dir <projeto> --estado docs/prancheta-<nome>/lido --dry-run
   ```

   O `out_dir` grava cada documento como o corpo puro, em `lido/<coleção>/<id>.json`
   (conferido na sonda de 17/10/2026). Saída 3 não se registra como aprovado. Diga ao Bera o
   que o resumo diz: ainda sem aprovação, aprovação desfeita, ou quais marcas mudaram depois dela.
8. **Registrar.** O resumo em markdown que o script imprime vai para o SESSION.md (e para o
   arquivo de decisões, se o projeto tiver um). Depois, sem `--dry-run`, o mesmo comando gera a
   versão aprovada, só leitura. Ela passa pelo `build_artifact.py`, é republicada na mesma URL
   (sem passar `capabilities`, que fica como estava) e a pasta `docs/prancheta-<nome>/` inteira
   é commitada por caminho: conteúdo, página e `lido/`. Esse commit é o arquivo da aprovação.

O `read_db` das instruções antigas (`guia-vivo.md`) é o mesmo `ArtifactData` com outra grafia.

## O JSON de conteúdo

Obrigatórias: `titulo`, `projeto`, `lede` e `fases`. Cada fase tem `id`, `titulo` e ao menos um
passo, e cada passo tem `id`, `titulo`, `muda` e `pronto`. O resto é opcional, e seção sem dado
não aparece. Chave desconhecida reprova, com a parecida como dica. Ids em minúsculas, dígitos,
`-` e `_`, únicos na prancheta toda, porque a marca no `db` é por id.

| Chave | O que é | Regra |
|---|---|---|
| `tarja` | rótulo curto da barra (EXEMPLO, RESTRITO) | até 24 caracteres |
| `pedidos` | `texto` e `fases`: o pedido do Bera e onde ele entra | |
| `fatos` | `status`, `titulo`, `texto`, `fonte`, `falta` e `selo` opcionais | `status` é documentado, alegado, nao_confirmado ou misto. **Sem `fonte` reprova** |
| `pistas` | o que ainda não foi lido e não tem status | texto |
| `fases[].agenda` | `inicio` (AAAA-MM-DD), `segmentos` (`quem` claude ou voce, `dias`), `depois_de`, `prazo`, `resumo` | com agenda, o período é calculado e `quando` reprova |
| `linha_do_tempo` | `datas_fixas` (`id`, `data`, `rotulo`) e `nota` | `prazo` cita uma data fixa |
| `casas` e `fluxos` | onde cada peça mora e como as casas se ligam | |
| `opcoes` | `id`, `titulo`, `texto`, `recomendada`, `onde`, `esforco` | **fora da recomendação sem `porque_fora` reprova** |
| `premissas` | `id` e `texto` | valem se o Bera não vetar |
| `riscos` | `severidade` (alto, medio, baixo), `risco`, `mitigacao` | |
| `acessos` | `tipo` e `detalhe`, o manifesto de acessos do plano | |
| `perguntas` | `titulo`, `recomendacao`, `contexto` opcional | **até quatro** |
| `fontes` | `rotulo` e `url` opcional | url só http ou https |
| `atalhos` | `ajustar` e `cortar`, os chips de cada escolha | padrão no script |

Texto aceita `` `código` `` e `**negrito**`. Todo o resto vira texto, nunca marcação: a página
monta tudo por nó de texto, e o JSON vai embutido sem nada que feche a tag do script.

## O estado no `db`

| Caminho | Corpo | Quem escreve |
|---|---|---|
| `marcas/<id>` | `tipo` (passo, opcao, premissa, marco), `valor`, `atalhos`, `nota`, `em` | a página, numa ação do Bera |
| `estado/geral` | `nota`, `em` | a página |
| `estado/aprovacao` | `aprovado`, `em`, `por` (id opaco), `marcas_ate`, `resumo` | a página, na confirmação |
| `chat/p<n>` | `pergunta`, `resposta`, `em`, `registrado_por` | o Claude |

O marco de uma fase é `m-<id da fase>`, e o valor dele é quantos dias a própria fase andou.

O que a página garante, e o `verifica_prancheta.js` da bancada mediu em 17/10/2026: nada se
grava ao abrir, uma escrita por vez por documento (a que chega no meio sai depois, com o estado
mais novo), nota com espera de 800 ms, uma assinatura por consulta, `unavailable` tentado de
novo uma vez, e toda marca pendente sai antes da aprovação, para a aprovação nunca nascer velha.
`user.can("data.write")` falso deixa a página só leitura, e nulo mantém os controles e deixa a
escrita recusada decidir. Sem `db` (arquivo local, visualização sem a capability), as marcas
ficam no `localStorage` com aviso de que o Claude não consegue lê-las. É o único papel do
navegador aqui: o estado que vale é o do `db`.

## As duas lições do uso real

**O Bera não se lembrou de ter aprovado.** As respostas do chat entraram rápido e a aprovação
se perdeu no meio delas. Por isso a aprovação saiu do chat: ela é um botão da prancheta, com uma
confirmação que lista o que vai ser aprovado, e o estado aparece com data e hora na barra fixa,
na capa e no fim. Marca mudada depois da aprovação deixa a prancheta em "mudou depois da
aprovação", com o botão "Aprovar de novo", e o `--estado` sai com 3.

**A linha do tempo proposta não era a que ele queria**, e ele teve de escrever para mudar. Por
isso cada fase da linha do tempo se antecipa ou se adia por clique. A cascata é rígida: o
deslocamento passa inteiro às fases que dependem da movida, e com mais de uma dependência vale
a que mais andou. A dependência padrão é a fase anterior, e `depois_de` troca. A posição
recomendada fica tracejada, a lista diz o que andou por marca e o que andou por cascata, e fase
que passa do `prazo` fica marcada em texto. A mesma conta mora no script e no template, e os
testes comparam as duas.

## Aparência

Tokens do detonado nos dois temas: `neutro-claro.css` em `:root` e o `neutro.css` no
`prefers-color-scheme: dark` e no `data-theme="dark"`. As duas séries da linha do tempo
(`--serie-1` para o Claude, `--serie-2` para a vez do Bera) passaram no `validate_palette.js` da
`dataviz` nos dois temas, nos fundos `--panel` e `--bg`. O `--accent` e o `--support` do escuro
reprovaram como série, e por isso as séries são tokens próprios. Borda de controle usa `--t5`
(no mínimo 4,9:1), e o status de fato e a severidade de risco se repetem na forma da borda, não
só na cor. O CSS é da própria prancheta, sobre o contrato de tokens. O do guia vivo não serve
aqui, e mudança visual entra pelo template, nunca pela página de um projeto (princípio 8).

Medido em 17/10/2026 no exemplo: axe-core sem violação (WCAG 2.2 AA e boas práticas) no claro
a 1366 px, no escuro a 390 px e na versão aprovada, sem rolagem horizontal a 390 px, nenhum alvo
abaixo de 24 px, foco visível e teclado nos controles e na linha do tempo. Os portões de saída
continuam os dois manual-only, anti-slop e `cão-guia`: nomeie e espere o Bera chamar.
