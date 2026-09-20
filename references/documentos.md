# Guia consultivo e passo a passo

O guia vivo não é o único documento que esta skill produz, e tentar fazer um template servir
para tudo é o jeito mais rápido de perder o que torna o guia vivo confiável.

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
