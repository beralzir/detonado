# detonado

> Skill do Claude Code (manual-only) que dá forma a um projeto de execução: fases que só fecham
> com prova, `HANDOFF.md` para retomar do celular, `SESSION.md` como checkpoint que sobrevive à
> queda de contexto, `tasks/lessons.md` e um guia vivo em HTML com checkboxes e barra de
> progresso que o Claude atualiza por script a cada etapa provada. Invocação: `/detonado`.

*Por **[Renato Beralzir](https://github.com/beralzir)**, autoria independente.*
*Claude Code skill (Portuguese): phases with proof, a phone-readable handoff, a context-proof checkpoint, a lessons file and a living HTML guide whose progress bar shows what was proven, not what was promised.*

## O nome

**Detonado** é como se chama, no Brasil, o guia que leva o jogador do começo ao fim do jogo sem
perder o save. É isso que a skill faz com um projeto: um percurso em fases, cada uma com a prova
que a fecha, e um ponto de retomada que funciona dias depois, em outra máquina, ou depois que o
contexto da sessão caiu.

## Por que existe

O método nasceu num projeto real, a migração de um PC para servidor pessoal de IA
(`predator-servidor-ia`, ago/2026), e três coisas custaram caro lá:

- **Estado copiado envelhece em dias.** Um arquivo de estado duplicado ficou dez dias atrás do
  repositório que era a fonte da verdade. Regra: o estado tem um dono, os outros apontam.
- **Sensação de feito não é prova.** `systemctl is-active` dizia `active` com o serviço rodando
  em CPU a 8 tokens/s. Regra: a fase fecha com evidência citada, nunca com "abriu sem erro".
- **Contexto longo esquece o formato.** Perguntas que deviam ser clicáveis viravam texto,
  checkpoints deixavam de ser escritos. Regra: o checkpoint reafirma os formatos âncora e vive
  fora da janela de contexto.

## O que a skill faz

| Modo | Pedido típico | Resultado |
|---|---|---|
| **abrir** | "abre o detonado do homelab" | Projeto novo com os cinco artefatos e as fases validadas |
| **adotar** | "manda o detonado adotar esse repo" | Projeto existente ganha só o que falta, sem sobrescrever |
| **guia** | "marca a etapa 2 da fase 1" | Guia vivo atualizado por script, com a prova citada |
| **fechar** | "detonado, fecha a sessão" | `SESSION.md`, guia, `HANDOFF.md` se mudou, commit |
| **retomar** | "chama o detonado, onde paramos?" | Lê o registro, roda a sanidade, responde curto |
| **lição** | "detonado, registra essa lição" | `tasks/lessons.md`, marcada "a confirmar" |

Os cinco artefatos de um projeto: `CLAUDE.md`, `HANDOFF.md`, `SESSION.md`, `tasks/lessons.md`
e `docs/guia-<projeto>/`. O que vai em cada um está em `references/artefatos.md`.

## O guia vivo

Um HTML por projeto, com navegação lateral, barra de progresso, uma caixa por etapa com o
"pronto quando", blocos de comando com botão de copiar e o bloco "Onde paramos" sincronizado com
o `HANDOFF.md`. O estado é o atributo `checked`, versionado no git. Marcar, desmarcar e fechar
fase é trabalho do `scripts/progresso.py`, nunca de edição à mão. O `build_artifact.py` deriva a
versão publicável com as imagens em base64.

Os tokens visuais ficam em `assets/guia/tokens/`: `bera.css` traz a marca do autor, `neutro.css`
é o fallback sem marca. Trocar de marca é trocar o arquivo. O template passou pelo detector
anti-slop da `impeccable` e pela auditoria de acessibilidade do `cão-guia` (axe-core, contraste e
daltonismo medidos) antes de entrar aqui.

## Com as outras skills

- [`daquele-jeito`](https://github.com/beralzir/daquele-jeito) planeja e audita. O "pronto
  quando" de cada etapa é o critério de done do plano dela.
- [`portas-em-automatico`](https://github.com/beralzir/portas-em-automatico) executa com
  cross-checks e reescreve o `SESSION.md` a cada cinco passos. O formato é daqui, a cadência é
  de lá.
- `risca-de-giz` decide direção visual. `cão-guia` audita acessibilidade. O detonado não faz
  nenhuma das duas, só sugere em texto.

## Invocação

Manual-only, por decisão do autor. Dispara só quando nomeada: `/detonado`, "usa o detonado",
"chama o detonado", "abre o detonado do <projeto>", "detonado, fecha a sessão". Pedido genérico
de guia, handoff, checklist ou "onde paramos" não dispara.

## Instalação

```bash
git clone https://github.com/beralzir/detonado ~/workspace/detonado
ln -s ~/workspace/detonado ~/.claude/skills/detonado
```

Sem dependência além do Python 3 da máquina. Os scripts rodam com a biblioteca padrão. O botão
de copiar do guia usa a API de clipboard do navegador, com fallback para `execCommand`.

## Arquivos

| Caminho | O que é |
|---|---|
| `SKILL.md` | A instrução: modos, princípios, fluxo de abrir, regras default, fora de escopo |
| `references/metodo.md` | Fases com prova: fatiamento, o que vale como prova, testes que mentem, JSON das fases |
| `references/artefatos.md` | Os cinco artefatos, quando atualizar cada um, estado com dono |
| `references/guia-vivo.md` | Anatomia do guia, contrato dos tokens, atualização, publicação, acessibilidade, portões |
| `references/retomada.md` | Rituais de fechar e retomar, mensagem para colar no celular |
| `assets/templates/` | Templates de `CLAUDE.md`, `HANDOFF.md`, `SESSION.md` e `lessons.md` |
| `assets/guia/` | Template do guia, bloco de fase, tokens `bera` e `neutro` |
| `scripts/novo_projeto.py` | Cria ou adota um projeto a partir dos templates, sem sobrescrever |
| `scripts/progresso.py` | Lista, marca, desmarca, fecha fase, carimba data, valida consistência |
| `scripts/build_artifact.py` | Deriva o HTML publicável com imagens em base64, limite de 16 MB |
| `evals/` | Casos de teste da skill e o projeto de exemplo `radio-pirata` |

## Licença

MIT. Ver `LICENSE`.
