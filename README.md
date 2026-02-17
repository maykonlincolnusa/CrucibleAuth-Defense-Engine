# Password Cracking Lab + Defense System

Plataforma completa para simulacao/deteccao/defesa de ataques de autenticacao com:

- API `FastAPI`
- Banco robusto `PostgreSQL` com migracoes Alembic
- Pipeline de IA:
  - Isolation Forest (anomalias de login)
  - One-Class SVM (trafego malicioso)
  - LSTM + GRU (series temporais)
  - Transformer (mutacao de ataque)
  - RNN + Markov + Embeddings (sequencia hibrida)
  - DQN (resposta autonoma)
- Streaming `Kafka/Redpanda`
- Observabilidade `Prometheus + Grafana + OpenTelemetry`
- Tracking de treino `MLflow`
- Dashboard web com drill-down e atualizacao via WebSocket

## Arquitetura

- `app/api`: rotas REST
- `app/core`: configuracao
- `app/db`: modelos, sessao, init e migracao
- `app/ml`: modelos de deteccao/antecipacao/resposta
- `app/services`: orquestracao, monitoramento, lifecycle, streaming
- `app/web`: frontend dashboard
- `alembic`: migracoes
- `observability`: Prometheus e Grafana provisioning
- `load`: cenarios de carga (Locust)
- `tests/chaos`: testes de caos/resiliencia

## Subir stack completa

```bash
docker compose up --build
```

Servicos:

- API + Dashboard: `http://localhost:8000/`
- Swagger: `http://localhost:8000/docs`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin`)
- MLflow: `http://localhost:5000`
- PostgreSQL: `localhost:5432`
- Redpanda Kafka: `localhost:9092`

## Deploy em nuvem com Terraform (AWS)

Infra pronta em `infra/terraform/aws` com:

- ECS Fargate (API/Dashboard)
- ALB
- RDS PostgreSQL
- MSK Serverless (Kafka gerenciado)
- S3 para artefatos
- WAF (servico adicional de seguranca)
- GuardDuty (deteccao de ameaca na conta)

Passos:

```bash
cd infra/terraform/aws
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

Atalhos no `Makefile`:

- `make tf-init`
- `make tf-plan`
- `make tf-apply`

## Banco e migracoes

```bash
python scripts/migrate.py
```

Migracao inicial: `alembic/versions/20260217_0001_initial_schema.py`

## Endpoints principais

1. Registro: `POST /api/v1/auth/register`
2. Login monitorado: `POST /api/v1/auth/login`
3. Telemetria rede (sync): `POST /api/v1/telemetry/network`
4. Telemetria rede (stream): `POST /api/v1/telemetry/network/stream`
5. Telemetria series temporais: `POST /api/v1/telemetry/timeseries`
6. Attack sequence: `POST /api/v1/telemetry/attack-sequence`
7. Risco por usuario: `GET /api/v1/defense/risk/{user_id}`
8. Treino + validacao + rollback: `POST /api/v1/models/train-bootstrap`
9. Auto-retrain manual: `POST /api/v1/models/auto-retrain`
10. Modelos ativos: `GET /api/v1/models/active`
11. Monitoring overview: `GET /api/v1/monitoring/overview`
12. Monitoring timeseries: `GET /api/v1/monitoring/timeseries`
13. Monitoring drilldown: `GET /api/v1/monitoring/drilldown`
14. Prometheus metrics: `GET /metrics`
15. WebSocket live: `GET /ws/monitoring`

## Frontend

Dashboard em `http://localhost:8000/` mostra:

- KPIs de login/rede/defesa/modelos
- Series por hora (volume, risco, bloqueios, anomalias)
- Drill-down:
  - top usuarios por risco
  - top IPs de origem
  - top assinaturas de ataque
- Atualizacao:
  - WebSocket live (`/ws/monitoring`)
  - fallback por polling

## Retreino automatico com rollback

Configuracao em `.env`:

- `AUTO_RETRAIN_ENABLED=true`
- `AUTO_RETRAIN_INTERVAL_MINUTES=30`
- `RETRAIN_MIN_EVENTS=250`
- `RETRAIN_ACCEPTANCE_THRESHOLD=0.55`

Fluxo:

1. Gera pipeline candidato
2. Avalia qualidade em dados historicos
3. Compara com baseline/threshold
4. Se aceito: ativa novo pipeline
5. Se reprovado: rollback automatico
6. Loga parametros e metricas no MLflow

## Streaming Kafka/Redpanda

- Producer: endpoint `POST /api/v1/telemetry/network/stream`
- Consumer: background job da API processa topico `KAFKA_NETWORK_TOPIC`

## Observabilidade

- Prometheus scrape: `observability/prometheus/prometheus.yml`
- Grafana datasource/dashboard provisionados:
  - `observability/grafana/provisioning/datasources/prometheus.yml`
  - `observability/grafana/dashboards/security_lab_overview.json`
- OTel opcional:
  - `OTEL_ENABLED=true`
  - `OTEL_EXPORTER_OTLP_ENDPOINT=http://...`

## Carga e caos

Load test:

```bash
locust -f load/locustfile.py --headless --host http://localhost:8000 --users 100 --spawn-rate 10 --run-time 2m
```

PowerShell helper:

```powershell
./scripts/run_load_test.ps1
```

Chaos (restart do DB):

```powershell
./scripts/chaos_db_restart.ps1 -DowntimeSeconds 20
```

## Testes

```bash
pytest -q
```

Obs: no ambiente atual, os testes podem falhar se dependencias Python nao estiverem instaladas (`python-jose`, etc.).
