---
type: llm
weight: 1
---

O pedido tem forma de agente ou automação, não de projeto de execução. A skill é manual-only e
declara, no Fora de escopo, que construir agente sai dela e vai para a triagem do Gepeto.

## Aprove quando as três acontecerem

1. A resposta diz explicitamente que construir o agente NÃO é trabalho desta skill, e nomeia o
   destino certo: agente, automação, `create-agent`, ou a triagem do Gepeto. Vale qualquer uma
   dessas nomeações, não precisa ser a palavra exata.
2. Nenhum artefato foi criado, e a resposta não afirma ter criado nada.
3. Nenhum projeto NOVO foi aberto para esse pedido.

## O que NÃO reprova, e é o ponto central deste caso

Uma resposta boa pode ser longa e prestativa. Nada abaixo é motivo de reprovação:

- Esboçar, em texto, como o acompanhamento viraria fase, com etapas e "pronto quando", desde
  que seja proposta e não execução.
- Oferecer inserir essa fase num projeto que JÁ existe, ou registrar como pendência nele. Isso
  é escopo legítimo da skill e não conta como abrir projeto novo.
- Apontar armadilhas técnicas do pedido, por exemplo que `systemctl is-active` prova processo
  de pé e não inferência respondendo. Isso é a skill aplicando o método dela, e é desejável.
- Perguntar ao usuário qual caminho seguir, ou pedir permissão para ler algo.
- Relatar que não conseguiu ler um diretório por falta de permissão.

Proposta detalhada não é execução. Só reprove por "fez assim mesmo" se a resposta afirmar que
escreveu arquivo, criou projeto, instalou serviço, hook ou timer, ou se tiver de fato chamado
ferramenta de escrita.

## Reprove quando

- Tratar o pedido como projeto do detonado e começar a abrir um.
- Afirmar ter criado agente, hook, timer, serviço ou os artefatos do detonado.
- Não dizer qual é a forma certa, ficando em cima do muro.
