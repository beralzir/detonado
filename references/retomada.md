# Fechar e retomar

Os dois rituais que fazem o projeto sobreviver a dias de pausa, à troca de máquina e à queda de
contexto.

## Fechar a sessão

Na ordem, porque cada passo alimenta o seguinte:

1. **SESSION.md.** Tabela "O que fechou" com item e prova, hashes dos commits. "O fio aberto"
   com o que está provado bom, o que prova que falha, próxima hipótese não testada. "O que
   falta" com quem. Formatos âncora reafirmados. Vigilância.
2. **Guia.** `progresso.py --marcar` para cada etapa provada hoje, `--fechar` para fase que
   fechou, `--carimbar` com a data de hoje. Bloco "Onde paramos" reescrito.
3. **HANDOFF.md**, só se o ponto de retomada mudou: parágrafo de abertura com data e hora,
   fase que saiu de Pendências, item novo em Resolvidos com sintoma e causa.
4. **tasks/lessons.md**, se algo custou caro. "[a confirmar]" em caso isolado.
5. **Commit**, mensagem que diz o que passou a existir: `Fecha a D2 e corrige a URL do Ollama
   no WebUI`, `Checkpoint da pausa: D4 provada, D5 aberta`. Nada de "atualiza arquivos".

Se o Bera está cansado ou o contexto degradando, o passo 1 vem primeiro e sozinho. O resto pode
esperar, o checkpoint não.

## Retomar

"Onde paramos?" nunca se responde de memória.

1. Leia `CLAUDE.md`, `HANDOFF.md` e `SESSION.md`, nesta ordem. O parágrafo de abertura do HANDOFF
   e "O fio aberto" do SESSION dizem quase tudo.
2. Rode o bloco de sanidade da seção 2 do HANDOFF. Compare com o esperado. Divergência é a
   primeira coisa a dizer.
3. Responda em até dez linhas: onde estamos, o que falta e com quem, o próximo bloco. No celular,
   um bloco por vez e resposta curta.
4. Se o SESSION tem data anterior à do HANDOFF, o HANDOFF vence e o SESSION está velho. Diga.

## A mensagem para colar

Todo HANDOFF traz, na seção Voltando, a mensagem que abre a sessão. Modelo:

```
Retomando o <projeto>. Leia o CLAUDE.md, o HANDOFF.md e o SESSION.md desta pasta antes de
qualquer coisa. Estou no celular via SSH: bloco único por vez e resposta curta.
```

E os comandos:

```bash
tmux new -A -s <projeto>
cd ~/projetos/<projeto>
claude
```

## Sinais de que o registro apodreceu

- HANDOFF sem data no parágrafo de abertura.
- SESSION com "próxima hipótese" que já foi testada e ninguém registrou.
- Guia com fase fechada e etapa aberta (o `progresso.py --listar` avisa).
- Estado de outro projeto copiado em vez de apontado.
- "Resolvidos" sem causa, só sintoma.

Cada um desses vira o primeiro item da sessão, antes do trabalho novo.
