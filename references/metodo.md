# Fases com prova

Como fatiar um projeto para que cada pedaço feche com evidência, e não com sensação de feito.

## Anatomia

Projeto, fases, etapas. A fase é a unidade que o Bera percebe ("a URL está no ar", "o Ollama
roda na GPU"). A etapa é a unidade que fecha numa sessão e cabe num checkbox.

Cada etapa tem três campos, e os três vão para o guia:

- **O que fazer**, em uma frase.
- **Pronto quando**: condição observável por quem não estava na conversa.
- **Prova aceita**: qual evidência fecha a caixa.

## Fase 0 é sempre a mesma

Guia vivo criado e publicado, SESSION.md inicial commitado, HANDOFF com a seção Voltando
funcionando. Ela existe para que a queda de contexto na primeira sessão não perca o fio. No
Predator foi a D0, e o fato de nascer primeiro salvou a sessão de 31/08.

## Regras de fatiamento

- Uma fase fecha algo que se percebe de fora. "Configurar" não é fase, "acessível do iPhone
  pelo tailnet" é.
- Mais de sete etapas numa fase é sinal de duas fases.
- Etapa que depende só do Bera (clique em painel web, conta a criar, prova no iPhone) fica
  marcada "com você" e não bloqueia as outras. No Predator, a D2 inteira era assim.
- Ação destrutiva ou irreversível (formatar, apagar, expor à internet) é etapa própria, com
  aviso e reversão escritos antes do comando.
- Decisões travadas vão numa tabela ("Decisões desta fase"), no guia e no HANDOFF, para
  ninguém reabrir sem querer.
- A ordem respeita dependência real, não conforto: o que desbloqueia mais vem antes.

## O que vale como prova

| Prova | Vale quando | Como registrar |
|---|---|---|
| Saída de comando | citada literal, com o trecho que prova | bloco no SESSION.md, referência no guia |
| URL respondendo | com o status HTTP e de onde foi testada | `HTTP/2 302` do iPhone por 5G, por exemplo |
| Arquivo existindo | com conteúdo conferido, não só `ls` | `head` ou `grep` do valor esperado |
| Teste passando | com o nome do teste e o resultado | saída do runner |
| Screenshot | só para estado passageiro de tela (erro, diálogo) | arquivo em `docs/guia-<projeto>/img/`, com `alt` |
| Declaração do Bera | nunca como prova. Como declaração, visível | "declarado em 02/09, sem prova" no guia e no SESSION |

## Testes que mentem

Herdados de `~/projetos/predator-servidor-ia/tasks/lessons.md`, onde cada um custou uma sessão.

- `systemctl is-active` diz `active` e não diz funcionando. Serviço de inferência se prova pelo
  caminho quente: `ollama ps` com `100% GPU` e `library=CUDA` no journal.
- `curl -s` engole a mensagem de erro. Use `-sS` ou `-i`.
- Cache de browser encontra "algum" build e pula o certo. Rode o instalador idempotente.
- `df` mente logo depois de `btrfs subvolume delete`. `btrfs subvolume sync /` antes.
- "Abriu sem erro" não é prova de nada. A prova é o efeito esperado, observado.
- Firewall se prova comparando dois caminhos até a mesma máquina, não olhando a regra.

## Como uma fase fecha

1. Todas as etapas com prova, marcadas por `scripts/progresso.py --marcar`.
2. A caixa "Etapa concluída" da fase, por `scripts/progresso.py --fechar <fase>`.
3. SESSION.md com a tabela item e prova.
4. HANDOFF.md: a fase sai de Pendências e entra em O que está de pé, com data.
5. Commit: `Fecha a F3: <o que passou a existir>`.

## Reabrir

Prova falsa aparece (o `active` de 23/08 no Predator). `progresso.py --reabrir <fase> --desmarcar
<etapa>`, registre no SESSION o que se acreditava e o que se provou, e leve a lição para
`tasks/lessons.md`. Reabrir com registro vale mais que fingir que estava certo.

## O JSON das fases

Entrada do `scripts/novo_projeto.py` (projeto novo) e do `scripts/progresso.py --inserir-fase`
(fase nova em guia existente). Uma fase por objeto, `id` curto e estável (é o prefixo dos ids dos
checkboxes). Crase no texto vira `<code>`. Fase nova passa pela mesma validação com o Bera que o
fatiamento inicial.

```json
{
  "fases": [
    {
      "id": "f0",
      "tag": "FASE 0",
      "titulo": "Guia vivo e checkpoint",
      "resumo": "Nasce primeiro para a queda de contexto não perder o fio.",
      "etapas": [
        {"texto": "Guia criado em `docs/guia-<projeto>/` e publicado como Artifact", "pronto": "URL do Artifact registrada no HANDOFF"},
        {"texto": "`SESSION.md` inicial commitado", "pronto": "hash do commit"}
      ]
    }
  ]
}
```

`pronto` é o "pronto quando" da etapa, que já nomeia a prova aceita, e o guia o renderiza como
"Pronto quando: ...". `prova` é aceito como sinônimo. Etapa sem `pronto` volta como pergunta antes
de gerar. Etapa que depende do Bera leva `"quem": "Bera"`. Crase vira `code`, asterisco duplo
vira negrito.

## Rodar o `novo_projeto.py`

Os quatro argumentos são obrigatórios, e `--sem-guia` não dispensa nenhum deles: sem `--fases` o
script sai com `error: the following arguments are required: --fases`. Escreva o JSON primeiro,
rode com `--dry-run`, confira o que nasce, e só então rode de verdade.

```bash
D=~/.claude/skills/detonado/scripts/novo_projeto.py

cat > /tmp/fases-<projeto>.json <<JSON
{ "fases": [ { "id": "f0", "tag": "FASE 0", "titulo": "...", "resumo": "...",
               "etapas": [ {"texto": "...", "pronto": "..."} ] } ] }
JSON

python3 $D \
  --nome <projeto> \
  --titulo "<Título do projeto>" \
  --objetivo "<o objetivo em uma frase>" \
  --fases /tmp/fases-<projeto>.json \
  --dry-run
```

Conferido o que nasceria, repita sem `--dry-run`. Opcionais: `--dir <caminho>` muda o destino,
`--tokens bera|neutro` escolhe os tokens da marca, `--sem-guia` adota projeto sem fase aberta.

## Com as outras skills

- `daquele-jeito` traz o plano e a auditoria de quatro eixos. O "pronto quando" da etapa é o
  critério de done do plano dela. Não há dois planos: há um plano e um guia que o mostra.
- `portas-em-automatico` executa e reescreve o SESSION.md a cada cinco passos. O formato do
  SESSION.md é desta skill (`assets/templates/SESSION.md`), a cadência é dela.
