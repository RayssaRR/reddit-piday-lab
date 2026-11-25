# Uso de Inteligência Artificial

## 1. Prompts utilizados

Os prompts abaixo representam os principais pedidos utilizados como apoio durante o desenvolvimento e a análise do laboratório.

1. **Análise do incidente:** analisar o postmortem do Reddit, identificar o mecanismo da falha, organizar uma linha do tempo e relacionar o incidente aos conceitos estudados na disciplina.
2. **Planejamento da reprodução:** propor uma arquitetura com Docker Compose para simular a dependência entre os labels dos nós Kubernetes e os seletores utilizados pelo Calico.
3. **Implementação e execução:** auxiliar na criação dos serviços, Dockerfiles, redes e configurações necessárias para executar a simulação.
4. **Coleta de métricas:** desenvolver uma sonda para registrar requisições, falhas, percentual de erros, tempo até a falha e tempo de recuperação.
5. **Análise do projeto Manoa:** identificar uma possível falha de acoplamento na comunicação entre o backend e o serviço de recomendações e propor uma mitigação reproduzível em containers.

## 2. Decisões aceitas, modificadas e rejeitadas

### Decisões aceitas

- Utilizar Docker Compose para executar os serviços em containers separados.
- Separar os serviços de simulação, aplicação e monitoramento.
- Registrar os resultados em arquivos JSONL e JSON para permitir a análise posterior.
- Utilizar métricas de percentual de erros, tempo até a falha e tempo de recuperação.
- Utilizar o DNS interno do Docker para comunicação entre containers na reprodução do caso Manoa.

### Decisões modificadas

- A configuração inicial das redes foi modificada para permitir que a sonda acessasse os serviços necessários. O container de monitoramento não estava conectado à rede de controle, impossibilitando a comunicação com o serviço de simulação do Kubernetes.
- O cálculo das métricas foi corrigido para diferenciar o tempo total de indisponibilidade do tempo de propagação da recuperação após a intervenção.
- A reprodução do Manoa foi organizada em um laboratório separado, sem modificar o código original do marketplace.

### Decisões rejeitadas

- Não tratar a simulação como uma reprodução fiel de um cluster Kubernetes ou do funcionamento interno do Calico, pois os serviços implementados são simplificações.
- Não apresentar os resultados do laboratório como se fossem métricas reais do incidente do Reddit.
- Não considerar o uso de `localhost` como endereço adequado para comunicação entre containers diferentes na arquitetura simulada do Manoa.

## 3. Erros identificados durante o desenvolvimento com IA

### Erro 1 — Rede ausente no Docker Compose

**Problema:** a configuração inicial não conectava o container da sonda à rede `control-net`. Por isso, a sonda não conseguia acessar o serviço `k8s-sim`.

**Identificação:** durante a execução dos testes, a comunicação com o serviço de simulação falhou.

**Correção:** o container da sonda foi conectado também à rede `control-net`, permitindo o acesso aos endpoints necessários.

**Resultado:** a sonda passou a conseguir consultar os serviços e executar a coleta de métricas.

### Erro 2 — Interpretação incorreta do tempo de recuperação

**Problema:** uma versão inicial da análise tratava o intervalo entre a intervenção de recuperação e a primeira requisição bem-sucedida como se fosse o tempo total de recuperação do incidente.

**Identificação:** ao comparar os registros de tempo da sonda, foi observado que esse intervalo não representava todo o período de indisponibilidade.

**Correção:** as métricas foram separadas em:
- Tempo até a falha: intervalo entre o início da simulação e a primeira falha detectada.
- Tempo de recuperação: intervalo entre a primeira falha e a primeira requisição bem-sucedida.
- Propagação da recuperação: intervalo entre a intervenção manual e a primeira requisição bem-sucedida.

**Resultado:** a análise passou a distinguir o período total de indisponibilidade do tempo necessário para a recuperação produzir efeito.

## 4. Considerações finais

A inteligência artificial foi utilizada como ferramenta de apoio à análise, implementação e documentação. As sugestões não foram aceitas automaticamente: as configurações e os resultados foram conferidos por meio da execução dos containers, inspeção dos logs e testes de comunicação.

Os erros identificados demonstraram a importância de validar as sugestões da IA na prática, especialmente em configurações de redes, comunicação entre serviços e interpretação de métricas.