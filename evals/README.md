# Evals da detonado

## Como rodar

```bash
cd ~/.claude/skills/detonado
claude plugin eval --case <nome> --ablation none --no-publish .
```

`--ablation none` corta o braço sem-plugin, que dobra as execuções e o custo. Use a ablação
quando a pergunta for "a skill melhora o resultado?", não quando for "a skill regrediu?".
Cada caso roda três vezes, e cada rodada sobe um Claude filho na sua credencial, então a suíte
custa dinheiro real: um caso são uns US$ 0,60 sem ablação, o dobro com ela. `--max-cost-usd`
põe teto, e quando o teto bate os graders pagos são pulados, o que estraga o número em vez de
só interromper.

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

## Dívida: os 12 casos do `evals.json`

O `evals.json` na raiz desta pasta tem 12 casos escritos antes desta estrutura existir, e
nenhuma ferramenta os consome: o `claude plugin eval` espera `prompt.md` mais `graders/`, não
aquele JSON. Eles nunca rodaram. Estão mantidos como fonte do conteúdo, para conversão caso a
caso. O caso 4 virou `forma-errada-agente/`, e é o modelo a seguir.

O caso 6 precisa da fixture `radio-pirata` montada no sandbox, então a conversão dele depende
de scaffold, que este primeiro caso não exercitou.
