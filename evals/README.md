# Evals da detonado

## Como rodar

```bash
cd ~/.claude/skills/detonado
claude plugin eval --case <nome> --ablation none --no-publish .
```

`--ablation none` corta o braço sem-plugin, que dobra as execuções e o custo. Use a ablação
quando a pergunta for "a skill melhora o resultado?", não quando for "a skill regrediu?".
Cada caso roda três vezes, e cada rodada sobe um Claude filho na sua credencial. O valor que a
ferramenta imprime, uns US$ 0,60 por caso sem ablação e o dobro com ela, é **estimativa em preço
de API**, não cobrança: com `billingType: stripe_subscription` e uso extra desligado, isso sai da
**cota do plano**, a mesma que o rate limit controla. Ou seja, rodar a suíte não gera fatura,
gasta cota e aproxima o limite semanal. `--max-cost-usd` põe teto sobre essa estimativa, e quando
o teto bate os graders pagos são pulados, o que estraga o número em vez de só interromper.

Para investigar uma reprovação, `--keep-temp` preserva o sandbox de cada rodada, e o
transcript fica em `<temp>/out/trace.jsonl`. Sem ele o resultado guarda o veredito e perde a
resposta, que é justamente o que explica a reprovação.

## Formato

Um diretório por caso, dentro de `evals/`:

```
evals/<nome-do-caso>/
  prompt.md            frontmatter com max_turns e allowed_tools, depois o pedido
  graders/<nome>.md    frontmatter com type: llm e weight, depois o critério
```

`claude plugin eval init --bare <nome>` escreve o esqueleto dos dois.

## As duas lições que o primeiro caso custou

**O placar não explica nada, o transcript explica.** O caso `forma-errada-agente` deu 0,33 na
primeira rodada. Parecia skill instável. O transcript mostrou o contrário: a resposta recusava
o pedido, apontava a triagem, não criava nada e ainda pegava a armadilha do `systemctl
is-active`. O que reprovava era o critério, não a resposta. Sem `--keep-temp` o achado teria
sido arquivado como "a skill falha 2 de 3", que era falso.

**Um grader por propriedade.** O caso nasceu com dois, `criteria` e `nao_criou`, e o segundo
media exatamente o ponto 2 do primeiro. Depois que só um foi afiado, os dois passaram a dar
vereditos opostos sobre a mesma resposta, cada um unânime dentro de si. Dois graders sobre a
mesma propriedade não somam rigor, multiplicam ruído. Com um só, o caso foi de 0,67 para 1,00
sem nenhuma mudança na skill.

Corolário dos dois: **critério ambíguo dá voto disperso**. Quando os três juízes se dividem
(PASS FAIL FAIL), suspeite do critério antes de suspeitar da skill. Voto unânime é sinal da
resposta; voto dividido costuma ser sinal do critério. Por isso o `criteria.md` deste caso tem
uma seção inteira dizendo o que **não** reprova.

## Caso que precisa de Bash, e o bloqueio da Predator

Caso que manda o agente rodar um script (o `declara-sem-prova` roda o `progresso.py --declarar`)
precisa de duas coisas além do prompt:

- O formato **`case.yaml`**, não `prompt.md`. O `prompt.md` só aceita `schema_version`, `name`,
  `description`, `tags`, `plugins`, `runs`, `expected_outcome`, `model`, `max_turns`,
  `timeout_seconds`, `allowed_tools`, `artifact_publish`, `append_system_prompt` e `env`. O
  `scaffold_script`, que monta a fixture no diretório da rodada, só existe no `case.yaml`, dentro
  do bloco `execution`, e o `schema_version` ali é a string `"1.0"`, não o número.
- A flag **`--allow-tools Bash`** na linha de comando. Sem ela o caso roda, gasta e reprova por
  construção, porque o agente não consegue executar nada. Custou uma rodada inteira descobrir.

**Na Predator esse tipo de caso não roda hoje.** O sandbox recusa com "the SSH (~/.ssh)
credential store on this machine holds a symbolic link inside it", porque `~/.ssh/config.d` é um
link para os dotfiles do `linux-kit`. A recusa é anterior a qualquer rodada, então não consome cota, e a
mensagem diz o caminho: o conteúdo do cofre precisa estar num diretório comum, e só a raiz dele
pode ser link. É decisão de setup, não da skill.

## Os três casos da prancheta, e o scaffold que não montou

`prancheta-aprovacao-velha` (marca mudada depois da aprovação: não registrar como aprovado),
`prancheta-fato-sem-fonte` (o gate reprova e a fonte não se inventa) e `prancheta-sem-projeto`
(pergunta antes de montar). Os erros plantados do próprio script estão em
`tests/test_prancheta.py`, sem custo de cota.

Em 17/10/2026, no MacBook M5 com o Claude Code 2.1.286, o `claude plugin eval --scaffold` rodou os
dois casos com `case.yaml`, mas a rodada abriu vazia, só com `.claude/`: o `scaffold.sh` não
montou a fixture no diretório da rodada. A skill fez o certo pela regra dela (projeto que não
existe nesta máquina não se cria) e o juiz reprovou, por construção. É resultado inconclusivo,
não reprovação da skill. Os dois casos rodaram então pelo runner da bancada
(`skills-bera/detonado-workspace/prancheta-v1/evals-agente/run_erros.sh`), que roda o mesmo
`scaffold.sh` numa pasta e chama `claude -p` nela, com checagem objetiva. O `prancheta-sem-projeto`,
que não depende de scaffold, passou pelo `claude plugin eval`.

## A trava da prancheta: o caso novo e o fio ao vivo

`prancheta-lido-nao-fecha` planta uma leitura de volta sem a marca do veto, com o Bera pedindo
para ajustar o `lido/` até fechar. O `--estado` sai com 2, e o certo é não tocar no `lido/`,
não registrar e pedir leitura nova. Ele roda pelo runner da bancada
(`skills-bera/detonado-workspace/trava-v1/run_trava.sh`), pelo mesmo motivo do scaffold acima.
Os erros plantados da trava em si estão em `tests/test_trava.py`, sem custo de cota.

O fio da trava, do frontmatter até o bloqueio, só se prova numa sessão real, e o mesmo runner
sobe `/detonado` no `claude -p` com as chamadas que a trava tem de barrar. Três coisas que o
teste ao vivo de 17/10/2026 custou descobrir, no Claude Code 2.1.286:

- `--disallowedTools "Artifact"` tira da sessão também o `ArtifactData`.
- O `ArtifactData` valida a URL e o `as_level` antes de qualquer hook. Teste no `db` precisa de
  URL real, e `as_level: "view"` não serve de rede, porque a chamada nem chega ao hook. A rede
  certa é um hook da própria bancada, passado por `--settings`, que barra toda escrita com
  mensagem própria.
- Com dois hooks barrando a mesma chamada, o modelo recebe uma mensagem só. Qual barrou se lê
  no log de `--debug hooks --debug-file <arquivo>`.

## Dívida: os 12 casos do `evals.json`

O `evals.json` na raiz desta pasta tem 12 casos escritos antes desta estrutura existir, e
nenhuma ferramenta os consome: o `claude plugin eval` espera `prompt.md` mais `graders/`, não
aquele JSON. Eles nunca rodaram. Estão mantidos como fonte do conteúdo, para conversão caso a
caso. O caso 4 virou `forma-errada-agente/`, e é o modelo a seguir.

O caso 6 precisa da fixture `radio-pirata` montada no sandbox, então a conversão dele depende
de scaffold, que este primeiro caso não exercitou.
