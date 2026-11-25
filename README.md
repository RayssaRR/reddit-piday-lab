# Laboratório de Reprodução de Incidentes com Containers

Projeto desenvolvido para a disciplina de Fundamentos de Computação Concorrente, Paralela e Distribuída — Computação em Nuvem.

O objetivo é reproduzir, em ambiente controlado com Docker Compose, mecanismos de falha relacionados à comunicação e ao acoplamento entre serviços, registrar métricas e avaliar estratégias de mitigação.

## 1. Incidente de referência: Reddit

**Fonte:** [Reddit Engineering — Postmortem](https://www.reddit.com/r/RedditEng/comments/11xx5o0/)

O incidente ocorreu durante uma atualização do Kubernetes da versão 1.23 para a 1.24. A remoção do label legado `node-role.kubernetes.io/master` fez com que os seletores `nodeSelector` e `peerSelector` utilizados pelo Calico deixassem de identificar os nós esperados, comprometendo a distribuição de rotas e a conectividade.

**Conceito da disciplina relacionado:** acoplamento. A configuração do Calico dependia implicitamente dos labels definidos pelo Kubernetes. Uma alteração em um componente afetou o funcionamento do outro.

## 2. Laboratório 1 — Simulação do incidente Reddit

### Arquitetura

O laboratório utiliza quatro serviços:

| Container | Responsabilidade |
|---|---|
| `k8s-sim` | Simula os nós, labels e atualização do Kubernetes |
| `calico-sim` | Simula os seletores e a disponibilidade de rotas |
| `application` | Representa a aplicação que recebe as requisições |
| `probe` | Executa as requisições e registra métricas |

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
$env:LOG_DIR="/logs/baseline"
docker compose --profile experiment up --build --abort-on-container-exit
```

Esse cenário reproduz a falha após a atualização simulada. A recuperação é realizada por uma intervenção manual que reintroduz o label legado no laboratório.

Após a execução, finalize os containers:

```powershell
docker compose down
```

### Executando o cenário mitigated

Ainda na pasta raiz, execute:

```powershell
$env:SCENARIO="mitigated"
$env:LOG_DIR="/logs/mitigated"
docker compose --profile experiment up --build --abort-on-container-exit
```

Nesse cenário, os labels atuais são preparados e os seletores do Calico são ajustados antes da atualização simulada.

Ao terminar:

```powershell
docker compose down
```

### Métricas coletadas

A sonda registra:

- Total de requisições.
- Quantidade e percentual de erros.
- Percentual de erros durante a indisponibilidade.
- Percentual de erros após a atualização.
- Tempo até a primeira falha detectada.
- Tempo entre a primeira falha e a primeira requisição bem-sucedida.
- Tempo de propagação da recuperação após a intervenção.

Os resultados são armazenados em:

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

Os resultados são registrados em:

```text
manoa-coupling-lab/
└── logs/
    ├── baseline/
    │   ├── probe.jsonl
    │   └── summary.json
    └── mitigated/
        ├── probe.jsonl
        └── summary.json
```

## 4. Limitações da simulação

As reproduções são modelos simplificados e não representam integralmente os ambientes reais.

### Laboratório Reddit

- Não utiliza um cluster Kubernetes real.
- Não implementa o funcionamento completo do protocolo BGP nem sessões reais de Route Reflector.
- O estado dos serviços simulados é mantido em memória.
- A recuperação baseline é uma intervenção manual de laboratório, não o procedimento real de recuperação do Reddit.

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
│   ├── baseline_preliminary/
│   └── mitigated/
└── manoa-coupling-lab/
    ├── docker-compose.yml
    ├── recommendation-service/
    ├── probe/
    ├── logs/
    └── analise-acoplamento-manoa.md
```

## 6. Documentação complementar

- `IA.md`: prompts utilizados, decisões aceitas, modificadas e rejeitadas, erros identificados e correções.
- `manoa-coupling-lab/analise-acoplamento-manoa.md`: análise do acoplamento no projeto Manoa, reprodução em miniatura, mitigação e limitações.
- `logs/`: evidências das execuções e métricas coletadas.

## 7. Reprodutibilidade

Para reproduzir os experimentos, é necessário ter o Docker Desktop em execução e seguir os comandos indicados para cada cenário.

Os resultados apresentados neste repositório correspondem às execuções registradas nos arquivos de log. As métricas devem ser interpretadas considerando as limitações de cada simulação.