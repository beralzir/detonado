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
- Blocos de comando `.cb` com `<pre>` e botão copiar. Caixas `.call` (gold, org, red, grn) para
  regra, aviso, perigo e resultado.
- `footer` com data da última atualização (`#atualizado`) e o caminho do arquivo.
- `script` no fim: copiar, contar checkboxes, atualizar `#pct`, `#fill` e os pontos.

Estado é o atributo `checked`. Sem localStorage: o que está no arquivo é o que vale, e o arquivo
está no git.

## Atualizar

```bash
python3 ~/.claude/skills/detonado/scripts/progresso.py docs/guia-x/guia-x.html --listar
python3 ~/.claude/skills/detonado/scripts/progresso.py docs/guia-x/guia-x.html --marcar e-f1-2 e-f1-3
python3 ~/.claude/skills/detonado/scripts/progresso.py docs/guia-x/guia-x.html --fechar f1
python3 ~/.claude/skills/detonado/scripts/progresso.py docs/guia-x/guia-x.html --desmarcar e-f1-3
python3 ~/.claude/skills/detonado/scripts/progresso.py docs/guia-x/guia-x.html --carimbar 02/09/2026
```

O script recusa id inexistente (sai 2), avisa fase fechada com etapa aberta (sai 1 quando nada
foi alterado), e imprime o progresso depois de cada operação. Marque só com a prova citada na
conversa. Declaração sem prova não marca: acrescente no texto da etapa "declarado pelo Bera em
<data>, sem prova".

Depois de marcar, atualize o bloco "Onde paramos" (`#status-atual`) e carimbe a data. O guia e o
HANDOFF dizem a mesma coisa, com a mesma data.

## Publicar

```bash
python3 docs/guia-x/build_artifact.py
```

Gera `guia-x.artifact.html` com as imagens em base64, e recusa acima de 16 MB. O CSP dos
Artifacts bloqueia host externo e caminho relativo, e libera fontes só do Google Fonts. A display
Cabinet Grotesk (Fontshare) cai para Inter, que já é o fallback do token. Publique o derivado com
a ferramenta Artifact, título curto e estável, favicon fixo (o mesmo em toda republicação),
descrição de uma frase. Registre a URL no HANDOFF e no SESSION.

## Tokens e marca

`assets/guia/tokens/bera.css` traz os tokens do schema `bera` (v2.1.1, Atelier Técnico):
`#0A0A0A` de fundo, dourado `#E5B748` liderando no escuro, terracota `#D97757` apoiando, raio
zero, sem sombra, sem gradiente, Inter e JetBrains Mono. `neutro.css` é o fallback sem marca.
O `novo_projeto.py` inclui o escolhido inline (`--tokens bera|neutro`).

Trocar cor, tipo ou direção não é decisão desta skill. Direção nova passa pela `risca-de-giz`,
que carrega o schema em `~/workspace/design-schemas/` e roda o gate dele. Calibragem aprovada
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

1. Anti-slop: `npx impeccable detect <guia.html>`, determinístico, roda local.
2. `cão-guia`: acessibilidade, contraste, `alt`.

Nomeie os dois em texto e espere o Bera chamar. Portão dispensado se registra na entrega, não se
omite. Atualização de checkbox e texto de status não reabre os portões.
