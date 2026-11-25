
# Parte D — Relação com o projeto Manoa

## 1. Identificação do risco no projeto

Durante a análise do Marketplace Integrador (Manoa), foi identificada uma dependência de configuração entre o backend e o serviço de recomendações.

No arquivo `backend/src/services/recommendation.service.ts`, o backend define o endereço do serviço:

```typescript
const RECOMMENDATION_SERVICE_URL =
  process.env.RECOMMENDATION_SERVICE_URL || "http://localhost:4000";
```

O método `getRecommendations` realiza uma chamada HTTP para o endpoint `/recommendations`, utilizando esse endereço.

No serviço de recomendações, em `recommendation-service/src/server.cjs`, a aplicação utiliza a porta 4000 por padrão e disponibiliza o endpoint `/recommendations`.

Essa integração representa um possível acoplamento de configuração: o backend depende do endereço, da porta e da rota utilizados pelo serviço externo.

Caso os componentes sejam executados em containers separados, utilizar `localhost` como endereço do serviço pode provocar falha de comunicação, pois cada container possui seu próprio contexto de rede.

**Observação:** a análise identifica um risco arquitetural. Não há evidência de que essa falha tenha ocorrido na execução real do projeto.

## 2. Relação com o incidente do Reddit

O incidente do Reddit também envolveu acoplamento de configuração entre componentes independentes.

No caso do Reddit, os seletores do Calico dependiam de labels dos nós do Kubernetes. A alteração desses labels durante a atualização comprometeu a identificação dos nós esperados.

No Manoa, a dependência está no endereço utilizado para comunicação entre o backend e o serviço de recomendações.

Embora os mecanismos técnicos sejam diferentes, ambos demonstram como uma alteração ou configuração incompatível entre componentes pode comprometer a integração do sistema.

## 3. Reprodução em ambiente Docker

Foi criado um experimento isolado com dois containers:

- `recommendation-service`: simula o serviço de recomendações.
- `probe`: simula o componente consumidor que realiza as requisições HTTP.

Os containers foram conectados por uma rede Docker Compose.

### Cenário baseline

O monitor utilizou o endereço:

`http://localhost:4000/recommendations`

Como o endereço apontava para o próprio container do monitor, as requisições falharam.

Resultados:
- Requisições: 10
- Sucessos: 0
- Falhas: 10
- Taxa de erros: 100%

### Cenário mitigado

O endereço foi alterado para:

`http://recommendation-service:4000/recommendations`

O nome do serviço foi resolvido pela rede interna do Docker Compose, permitindo a comunicação entre os containers.

Resultados:
- Requisições: 10
- Sucessos: 10
- Falhas: 0
- Taxa de erros: 0%

## 4. Comparação dos resultados

| Indicador | Baseline | Mitigado |
|---|---:|---:|
| Requisições | 10 | 10 |
| Sucessos | 0 | 10 |
| Falhas | 10 | 0 |
| Taxa de erros | 100% | 0% |

O experimento demonstrou que a configuração correta do endereço de comunicação foi suficiente para restabelecer a integração entre os containers.

## 5. Mitigação proposta

Para o ambiente containerizado do Manoa, recomenda-se:

- Configurar `RECOMMENDATION_SERVICE_URL` por variável de ambiente.
- Utilizar o nome DNS do serviço na rede Docker, em vez de `localhost`.
- Centralizar a configuração de comunicação no ambiente de implantação.
- Validar a disponibilidade do serviço antes de liberar o consumo das recomendações.

A mitigação foi demonstrada em ambiente reduzido, sem modificar o código original do Marketplace Integrador.

## 6. Limitações do experimento

O experimento não executou o backend original do Manoa. Foi utilizado um serviço simplificado e um monitor independente para reproduzir a falha de comunicação.

Foram realizadas dez requisições em cada cenário, em uma única execução por cenário.

Portanto, os resultados demonstram o mecanismo de falha e a eficácia da correção no ambiente simulado, mas não representam uma medição de desempenho do sistema real.
