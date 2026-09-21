# Guia consultivo e passo a passo

O guia vivo não é o único documento que esta skill produz, e tentar fazer um template servir
para tudo é o jeito mais rápido de perder o que torna o guia vivo confiável.

## Rodar

```bash
python3 ~/.claude/skills/detonado/scripts/documento.py \
  --tipo consultivo --nome comparar-distro --conteudo c.json --dry-run
python3 ~/.claude/skills/detonado/scripts/documento.py \
  --tipo passo --nome restaurar-backup --conteudo p.json --dir ~/projetos/x
```

Sai em `docs/<tipo>-<nome>/<tipo>-<nome>.html`. **O `--dir` é obrigatório na prática**: sem
ele o script escreve no diretório onde a sessão estiver, que quase nunca é o destino
pretendido. Este é o único artefato da skill que não é de projeto, então o destino se
pergunta antes, nunca se assume.

### O JSON, consultivo

```json
{"titulo": "...", "subtitulo": "...", "problema": "...",
 "evidencia": [{"afirmacao": "...", "fonte": "..."}],
 "opcoes": [{"titulo": "...", "corpo": "...", "custo": "..."}],
 "recomendacao": "...", "viraria": ["..."]}
```

Obrigatórias: `titulo`, `problema`, `evidencia`, `opcoes`, `recomendacao`. **Toda evidência
precisa de `fonte`**, e o script recusa sem ela, porque recomendação sem o que a sustenta é
opinião com tipografia boa.

### O JSON, passo a passo

```json
{"titulo": "...", "subtitulo": "...", "antes": ["..."],
 "passos": [{"texto": "...", "comando": "...", "esperado": "..."}],
 "errado": [{"sintoma": "...", "saida": "..."}]}
```

Obrigatórias: `titulo` e `passos`. **Passo com `comando` precisa de `esperado`**, e o script
recusa sem ele, pela mesma regra do HANDOFF: quem segue receita precisa saber se deu certo
antes de ir para o próximo.

### O gate, e por que ele existe

Até 21/09/2026 todo campo era lido com valor padrão vazio, então **um JSON com chaves
improvisadas produzia um HTML bem formatado, com cabeçalho e rodapé datado, seções vazias, e
saída 0**. Documento vazio entregue como pronto é o mesmo defeito que o guia vivo combate com
"caixa marcada é prova, não intenção", na família que não tem caixa. Agora chave desconhecida,
seção obrigatória vazia e as duas regras acima reprovam com saída 2, e nada é escrito. Rode com
`--dry-run` primeiro e confira o tamanho em bytes antes de aceitar.

## A regra que separa as famílias

**Só o guia vivo tem estado.** Caixa marcada ali é prova, mora no arquivo, está em git e só o
`progresso.py` a move. Essa é a propriedade inteira da skill.

Documento que ensina não tem o que provar. Não existe "evidência" de ter lido um parágrafo. Se
um consultivo ganhar uma caixa que parece progresso, em um mês ninguém mais sabe qual caixa
vale e qual não vale, e aí o guia vivo deixa de significar alguma coisa.

| Artefato | Estado | Onde mora o estado | Quem mexe |
|---|---|---|---|
| Guia vivo | progresso provado | atributo `checked`, em git | só `progresso.py` |
| Guia consultivo | nenhum | não existe | ninguém |
| Passo a passo | marca efêmera de quem lê | `localStorage` do navegador daquela pessoa | quem está lendo |
| Mapa | nenhum, só lê | não existe | ninguém |

## Guia consultivo

Explica e recomenda. Serve para decidir, não para acompanhar. Exemplos: comparar duas
abordagens, apresentar um diagnóstico, defender uma escolha de arquitetura.

Não tem caixa, não tem barra de progresso, não tem `progresso.py`. Tem tese, evidência,
trade-off e recomendação, e diz de onde veio cada afirmação. Uma recomendação sem o que a
sustenta é opinião com tipografia boa.

Estrutura: cabeçalho datado, o problema em uma frase, o que se sabe e como se sabe, as opções
com o custo de cada uma, a recomendação, e o que mudaria a recomendação. Esse último bloco é o
que separa consultoria de palpite.

## Passo a passo

Um procedimento que se repete, e que não é de projeto nenhum: "como subir um container com
Quadlet", "como restaurar o backup". É seguido muitas vezes, por vezes por outra pessoa.

A diferença para o guia vivo é essa: o guia vivo acompanha **um** projeto e o progresso dele é
fato registrado; o passo a passo é receita, e quem segue quer só não perder o lugar.

Por isso a marca dele é **efêmera e local**:

- Vive no `localStorage` do navegador de quem está lendo, e nunca sai dali.
- Não vai para o git, não é lida por script nenhum, não aparece em mapa nem em HANDOFF.
- A página diz isso em texto, perto das marcas, para ninguém confundir com progresso.
- Se o `localStorage` falhar, estiver bloqueado ou vier vazio, a página funciona igual e a
  marca simplesmente não persiste. Nada de erro, nada de fingir que salvou.

Cada passo tem o comando e o **esperado logo abaixo**, a mesma regra do HANDOFF, porque quem
segue receita precisa saber se deu certo antes de ir para o próximo.

## O que nenhum dos dois tem

Barra de progresso, percentual, `data-done`, `data-fechada`, contagem de caixas. Tudo isso é
vocabulário de estado provado, e estado provado é do guia vivo. Um consultivo com barra de
progresso está dizendo que 40% de um argumento está pronto, o que não quer dizer nada.

## Visual

Os três compartilham os tokens e o CSS do `guia.template.html`, injetado e não copiado, pelo
mesmo motivo do mapa: cópia diverge. Direção visual nova é decisão da `risca-de-giz`, não
desta skill, e vale o princípio 8.

## Publicar

Igual ao guia vivo e ao mapa: o derivado sai pelo `build_artifact.py`, a primeira publicação
registra a URL onde o documento for citado, e republicar passa a mesma URL. Publicar é ação
externa, só com ok do Bera.

Os portões de saída são os mesmos, os dois manual-only: anti-slop e `cão-guia`. Consultivo e
passo a passo são HTML para leitura humana como qualquer outro desta skill, então nomeie os
dois e espere o Bera chamar.
