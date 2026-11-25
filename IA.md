# Uso de Inteligência Artificial

## 1. Prompts utilizados

Os prompts abaixo representam cinco solicitações-chave utilizadas como apoio durante o desenvolvimento, a reprodução dos incidentes e a análise dos resultados.

1. **Análise do incidente:** "Analise o postmortem do Reddit, identifique o mecanismo da falha, organize uma linha do tempo dos acontecimentos e relacione o incidente aos conceitos estudados na disciplina."

2. **Planejamento da reprodução:** "Proponha uma arquitetura com Docker Compose para simular a dependência entre os labels dos nós Kubernetes e os seletores utilizados pelo Calico, considerando os serviços e as redes necessários."

3. **Implementação e execução:** "Auxilie na criação dos serviços, Dockerfiles, redes e configurações necessárias para executar a simulação do incidente utilizando containers."

4. **Coleta de métricas:** "Desenvolva uma sonda para registrar requisições, falhas, percentual de erros, tempo até a falha e tempo de recuperação, armazenando os resultados em arquivos para análise."

5. **Análise do projeto Manoa:** "Analise a comunicação entre o backend e o serviço de recomendações do projeto Manoa, identifique o possível problema relacionado ao uso de localhost entre containers e proponha uma reprodução em miniatura com uma estratégia de mitigação."

## 2. Decisões aceitas, modificadas e rejeitadas

### Decisões aceitas

- Utilizar Docker Compose para executar os serviços em containers separados.
- Separar os serviços de simulação, aplicação e monitoramento.
- Registrar os resultados em arquivos JSONL e JSON para permitir a análise posterior.
- Utilizar métricas de percentual de erros, tempo até a falha e tempo de recuperação.
- Utilizar o DNS interno do Docker para comunicação entre containers na reprodução do caso Manoa.

### Decisões modificadas

- A configuração inicial das redes foi modificada para permitir que a sonda acessasse os serviços necessários. Durante a execução, foi identificado que o container de monitoramento não estava conectado à rede `control-net`, impossibilitando a comunicação com o serviço `k8s-sim`.
- O cálculo das métricas foi revisado para diferenciar o tempo total de indisponibilidade do tempo de propagação da recuperação após a intervenção manual.
- A reprodução do Manoa foi organizada em um laboratório separado, sem modificar o código original do marketplace.
- A organização dos arquivos de evidência foi corrigida após a identificação de que os resultados do cenário mitigado haviam sido armazenados na pasta destinada ao baseline. Os registros foram separados nas pastas oficiais `logs/baseline/` e `logs/mitigated/`.
- A análise dos resultados de uma execução preliminar do baseline foi revisada após a identificação de uma inconsistência no evento final do JSONL. O resumo foi recalculado a partir dos registros individuais das requisições. Na execução oficial posterior, os valores do evento `experiment_finished` e do arquivo `summary.json` passaram a apresentar os mesmos resultados.

### Decisões rejeitadas

- Não tratar a simulação como uma reprodução fiel de um cluster Kubernetes ou do funcionamento interno do Calico, pois os serviços implementados são simplificações.
- Não apresentar os resultados do laboratório como se fossem métricas reais do incidente do Reddit.
- Não considerar o uso de `localhost` como endereço adequado para comunicação entre containers diferentes na arquitetura simulada do Manoa.
- Não considerar os 8 segundos programados de interrupção como uma recuperação espontânea ou automática do sistema.

## 3. Erros identificados durante o desenvolvimento com IA

### Erro 1 — Rede ausente no Docker Compose

**Problema:** a configuração inicial não conectava o container da sonda à rede `control-net`. Por isso, a sonda não conseguia acessar o serviço `k8s-sim`.

**Identificação:** durante a execução dos testes, a comunicação com o serviço de simulação falhou, evidenciando que a sonda não possuía acesso à rede necessária.

**Correção:** o container da sonda foi conectado também à rede `control-net`, permitindo o acesso aos endpoints necessários.

**Resultado:** a sonda passou a conseguir consultar os serviços e executar a coleta de métricas.

### Erro 2 — Interpretação incorreta do tempo de recuperação

**Problema:** uma versão inicial da análise tratava o intervalo entre a intervenção de recuperação e a primeira requisição bem-sucedida como se fosse o tempo total de recuperação do incidente.

**Identificação:** ao comparar os registros de tempo da sonda, foi observado que esse intervalo não representava todo o período de indisponibilidade.

**Correção:** as métricas foram separadas em:

- **Tempo até a falha (TTF):** intervalo entre o início da atualização simulada e a primeira falha detectada.
- **Tempo de recuperação (TTR):** intervalo entre a primeira falha e a primeira requisição bem-sucedida após a intervenção.
- **Propagação da recuperação:** intervalo entre a intervenção manual e a primeira requisição bem-sucedida.

**Resultado:** a análise passou a distinguir o período total de indisponibilidade do tempo necessário para a propagação da recuperação. Na execução oficial do baseline, o TTR foi de 8,032 segundos e a propagação da recuperação foi de 0,032 segundo.

### Erro 3 — Inconsistência no registro final das métricas

**Problema:** em uma execução preliminar, o evento `experiment_finished` do arquivo JSONL registrava `time_to_recovery_seconds` com um valor que representava apenas o intervalo entre a intervenção manual e a primeira resposta bem-sucedida, em vez do tempo total entre a primeira falha e a recuperação.

**Identificação:** a comparação do evento final com os registros individuais das requisições mostrou que o valor não correspondia ao intervalo esperado para o TTR.

**Correção:** foi utilizado o script auxiliar `analyze.py` para recalcular as métricas diretamente a partir do arquivo `probe.jsonl`. Posteriormente, a implementação da função `calculate_metrics()` no `probe.py` foi conferida para garantir a distinção entre TTF, TTR e propagação da recuperação.

**Resultado:** na execução oficial de 25/11, o próprio `probe.py` calculou e registrou os seguintes valores:

- Tempo até a falha (TTF): 0,017 segundo.
- Tempo de recuperação (TTR): 8,032 segundos.
- Propagação da recuperação: 0,032 segundo.

O evento `experiment_finished` do arquivo `probe.jsonl` e o arquivo `summary.json` apresentam os mesmos valores, garantindo a consistência entre os registros brutos e o resumo consolidado.

## 4. Considerações finais

A inteligência artificial foi utilizada como ferramenta de apoio à análise, implementação e documentação. As sugestões não foram aceitas automaticamente: as configurações e os resultados foram conferidos por meio da execução dos containers, inspeção dos logs e testes de comunicação.

Os erros identificados demonstraram a importância de validar as sugestões da IA na prática, especialmente em configurações de redes, comunicação entre serviços, organização das evidências e interpretação de métricas.

A validação dos resultados permitiu corrigir inconsistências e manter os valores apresentados no relatório vinculados aos registros das execuções realizadas.