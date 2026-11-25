# Laboratório de Reprodução de Incidentes com Containers

Projeto desenvolvido para a disciplina de Fundamentos de Computação Concorrente, Paralela e Distribuída — Computação em Nuvem.

O objetivo é reproduzir, em ambiente controlado com Docker Compose, mecanismos de falha relacionados à comunicação e ao acoplamento entre serviços, registrar métricas e avaliar estratégias de mitigação.

## 1. Incidente de referência: Reddit

**Fonte:** [Reddit Engineering — Postmortem](https://www.reddit.com/r/RedditEng/comments/11xx5o0/)

O incidente ocorreu durante uma atualização do Kubernetes da versão 1.23 para a 1.24. A remoção do label legado `node-role.kubernetes.io/master` fez com que os seletores `nodeSelector` e `peerSelector` utilizados pelo Calico deixassem de identificar os nós esperados, comprometendo a distribuição de rotas e a conectividade.

**Conceito da disciplina relacionado: acoplamento.** A configuração do Calico dependia implicitamente dos labels definidos pelo Kubernetes. Uma alteração em um componente afetou o funcionamento do outro.

## 2. Laboratório 1 — Simulação do incidente Reddit

### Arquitetura

O laboratório utiliza quatro serviços:

| Container | Responsabilidade |
|---|---|
| `k8s-sim` | Simula os nós, labels e atualização do Kubernetes |
| `calico-sim` | Simula os seletores e a disponibilidade de rotas |
| `application` | Representa a aplicação que recebe as requisições |
| `probe` | Executa as requisições, orquestra os experimentos e registra métricas |

São utilizadas três redes Docker isoladas:

- `control-net`: comunicação de controle.
- `backend-net`: comunicação com a aplicação.
- `client-net`: comunicação com a sonda.

### Pré-requisitos

- Docker Desktop em execução.
- Docker Compose.
- Terminal PowerShell ou equivalente.

### Executando o cenário baseline

Na pasta raiz do repositório, execute:

```powershell
$env:SCENARIO="baseline"
docker compose --profile experiment up --build --abort-on-container-exit
```

Esse cenário reproduz a falha após a atualização simulada. A remoção do label legado faz com que os seletores do Calico deixem de identificar os nós esperados, provocando a indisponibilidade da comunicação.

A recuperação é realizada por uma intervenção manual de laboratório que reintroduz o label legado.

Após a execução, finalize os containers:

```powershell
docker compose down
```

### Executando o cenário mitigated

Ainda na pasta raiz, execute:

```powershell
$env:SCENARIO="mitigated"
docker compose --profile experiment up --build --abort-on-container-exit
```

Nesse cenário, os labels atuais são preparados e os seletores do Calico são ajustados antes da atualização simulada, evitando a interrupção da conectividade no modelo reproduzido.

Ao terminar:

```powershell
docker compose down
```

### Resultados experimentais

Os resultados abaixo correspondem às execuções registradas nos arquivos JSONL e consolidados nos arquivos `summary.json`.

| Métrica | Baseline | Mitigated |
|---|---:|---:|
| Total de requisições | 64 | 64 |
| Requisições com erro | 32 | 0 |
| Percentual global de erros | 50% | 0% |
| Taxa de erros durante a interrupção | 100% (32 de 32 requisições) | Não houve interrupção |
| Erros após a atualização | 66,67% | 0% |
| Tempo de atualização simulada | 4,011 s | 4,033 s |
| Tempo até a primeira falha (TTF) | 0,017 s | Não houve falha |
| Tempo até a recuperação (TTR) | 8,032 s | Não se aplica |
| Propagação da recuperação | 0,032 s | Não se aplica |

No cenário baseline, os 32 erros ocorreram durante a fase de interrupção. O percentual global de 50% considera também as requisições bem-sucedidas realizadas durante o aquecimento e a recuperação. Por isso, a taxa global não representa isoladamente a intensidade da falha.

O tempo até a primeira falha (TTF) foi de 0,017 segundo. Esse resultado indica que a falha foi detectada rapidamente pela sonda, pois a aplicação verifica a disponibilidade da comunicação a cada requisição, sem depender de um longo intervalo de detecção.

O tempo até a recuperação (TTR), de 8,032 segundos, corresponde ao intervalo entre a primeira falha detectada e a primeira requisição bem-sucedida após a intervenção manual. Esse período inclui os 8 segundos de interrupção programada no experimento. Portanto, não representa um tempo de recuperação espontânea do Kubernetes nem a duração do incidente real do Reddit.

A propagação da recuperação, de 0,032 segundo, representa o intervalo entre a intervenção manual e a primeira resposta bem-sucedida da aplicação.

No cenário mitigado, não foram observadas falhas nas 64 requisições, incluindo as 48 realizadas após a atualização simulada. Isso indica que a preparação dos labels e a adequação dos seletores evitaram a interrupção no modelo reproduzido.

### Arquivos de evidência

```text
logs/
├── baseline/
│   ├── probe.jsonl
│   └── summary.json
└── mitigated/
    ├── probe.jsonl
    └── summary.json
```

Os arquivos `probe.jsonl` contêm os registros individuais das requisições e eventos. Os arquivos `summary.json` apresentam os resultados consolidados.

## 3. Laboratório 2 — Acoplamento na comunicação entre serviços do Manoa

O segundo laboratório utiliza como referência o projeto Marketplace Integrador (Manoa).

No projeto original, o serviço de recomendações é chamado pelo backend por meio de uma URL configurável pela variável `RECOMMENDATION_SERVICE_URL`, cujo valor padrão é `http://localhost:4000`.

Quando os serviços são executados em containers separados, utilizar `localhost` como endereço do serviço de recomendações pode provocar falhas, pois cada container possui seu próprio ambiente de rede.

A reprodução em miniatura demonstra esse problema e sua mitigação utilizando o DNS interno do Docker.

### Arquitetura

| Container | Responsabilidade |
|---|---|
| `recommendation-service` | Simula o serviço de recomendações |
| `probe` | Envia requisições HTTP e registra os resultados |

Os dois containers compartilham a rede `manoa-net`.

### Executando o cenário baseline

Entre na pasta do laboratório:

```powershell
cd .\manoa-coupling-lab
```

Configure o endereço incorreto para a comunicação entre containers:

```powershell
$env:TARGET_URL="http://localhost:4000/recommendations"
$env:SCENARIO="baseline"
docker compose up --build --abort-on-container-exit
```

Nesse cenário, a sonda tenta acessar a própria interface de rede, em vez de acessar o container do serviço de recomendações.

### Executando o cenário mitigated

Configure o endereço utilizando o nome do serviço no Docker Compose:

```powershell
$env:TARGET_URL="http://recommendation-service:4000/recommendations"
$env:SCENARIO="mitigated"
docker compose up --build --abort-on-container-exit
```

Nesse cenário, a comunicação ocorre por meio do DNS interno da rede Docker.

### Resultados

Cada cenário foi executado com dez requisições, conforme os registros disponíveis nos arquivos de log.

| Métrica | Baseline | Mitigated |
|---|---:|---:|
| Total de requisições | 10 | 10 |
| Requisições com erro | 10 | 0 |
| Requisições bem-sucedidas | 0 | 10 |
| Percentual de erros | 100% | 0% |

No cenário baseline, as dez requisições falharam porque a sonda tentou acessar `localhost`, que representa o próprio container, e não o serviço de recomendações.

No cenário mitigado, as dez requisições foram concluídas com sucesso utilizando o nome `recommendation-service`, resolvido pelo DNS interno do Docker.

A reprodução demonstra a diferença entre utilizar `localhost` e o nome DNS do serviço na comunicação entre containers. Os resultados devem ser interpretados como evidência da simulação, não como medição de desempenho do marketplace completo.

## 4. Limitações da simulação

As reproduções são modelos simplificados e não representam integralmente os ambientes reais.

### Laboratório Reddit

- Não utiliza um cluster Kubernetes real.
- Não implementa o funcionamento completo do protocolo BGP nem sessões reais de Route Reflector.
- O estado dos serviços simulados é mantido em memória.
- A recuperação baseline é uma intervenção manual de laboratório, não o procedimento real de recuperação do Reddit.
- A topologia e a quantidade de requisições são reduzidas em comparação com um ambiente de produção.
- O tempo de interrupção é programado para fins de experimentação e não corresponde à duração do incidente real.

### Laboratório Manoa

- Não executa o backend original do Marketplace Integrador.
- O serviço de recomendações é uma implementação simplificada.
- A sonda executa dez requisições por cenário, com uma execução registrada para cada cenário.
- Os resultados demonstram a falha de comunicação na arquitetura simulada, não uma falha comprovada em produção no projeto original.

## 5. Organização do repositório

```text
reddit-piday-lab/
├── docker-compose.yml
├── README.md
├── IA.md
├── services/
│   ├── k8s_sim/
│   ├── calico_sim/
│   ├── application/
│   └── probe/
├── logs/
│   ├── baseline/
│   ├── baseline_backup_2211/
│   ├── baseline_failed_2511/
│   └── mitigated/
└── manoa-coupling-lab/
    ├── docker-compose.yml
    ├── recommendation-service/
    ├── probe/
    ├── logs/
    └── analise-acoplamento-manoa.md
```

As pastas `baseline_backup_2211` e `baseline_failed_2511` são registros auxiliares de execuções anteriores e não devem ser utilizadas como evidências oficiais dos resultados apresentados neste documento.

Os resultados oficiais utilizados na análise estão nas pastas `logs/baseline` e `logs/mitigated`.

## 6. Documentação complementar

- `IA.md`: prompts utilizados, decisões aceitas, modificadas e rejeitadas, erros identificados e correções.
- `manoa-coupling-lab/analise-acoplamento-manoa.md`: análise do acoplamento no projeto Manoa, reprodução em miniatura, mitigação e limitações.
- `logs/`: evidências das execuções e métricas coletadas.

## 7. Reprodutibilidade

Para reproduzir os experimentos, é necessário ter o Docker Desktop em execução e seguir os comandos indicados para cada cenário.

Os resultados apresentados neste repositório correspondem às execuções registradas nos arquivos de log. As métricas devem ser interpretadas considerando as limitações de cada simulação.