# 🔥 CrucibleAuth Defense Engine

**The ultimate authentication security laboratory & real-time defense platform.**

Simulate sophisticated login attacks (brute-force, credential stuffing, password spraying, sequence mutations) in a fully controlled environment — then **defend instantly** with a cutting-edge ML/DL pipeline and autonomous response engine.

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white&style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white&style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white&style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white&style=for-the-badge)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?logo=terraform&logoColor=white&style=for-the-badge)
![Kafka](https://img.shields.io/badge/Kafka-231F20?logo=apachekafka&logoColor=white&style=for-the-badge)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white&style=for-the-badge)
![Grafana](https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=white&style=for-the-badge)

---

## ✨ Why CrucibleAuth?

- **Realistic Attack Simulation** — Generate thousands of login attempts with realistic patterns
- **Multi-Model Anomaly Detection** — Isolation Forest, One-Class SVM, LSTM+GRU, Transformer, RNN+Markov+Embeddings
- **Autonomous Defense** — Deep Q-Network (DQN) agent that decides block / challenge / allow in real time
- **Live Telemetry Streaming** — Kafka/Redpanda for high-throughput event processing
- **Beautiful Real-Time Dashboard** — WebSocket-powered drill-down views with live metrics
- **Auto-Retraining with Rollback** — MLflow-tracked models that improve themselves safely
- **Production-Ready** — Docker Compose + full AWS Terraform infrastructure (ECS Fargate, RDS, MSK, WAF, GuardDuty)

---

## 🏗 Architecture

┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Attack Sim    │───▶│   FastAPI Backend   │───▶│  PostgreSQL + Alembic│
│ (Locust + Chaos)│    │   (v1/auth, telemetry)│    │   (risk scores, logs)│
└─────────────────┘    └─────────────────────┘    └─────────────────────┘
│
▼
┌─────────────────────┐
│   ML/DL Pipeline    │
│ • Isolation Forest   │
│ • LSTM+GRU           │
│ • Transformer        │
│ • DQN Agent          │
└─────────────────────┘
│
┌───────────┴───────────┐
│                       │
Kafka/Redpanda             MLflow
│                       │
▼                       ▼
┌─────────────────────┐   ┌─────────────────────┐
│  Prometheus + OTEL  │   │   Grafana Dashboard │
└─────────────────────┘   └─────────────────────┘

---

## 🚀 Quick Start (Local)

```bash
# 1. Clone the repo
git clone https://github.com/maykonlincolnusa/CrucibleAuth-Defense-Engine.git
cd CrucibleAuth-Defense-Engine

# 2. Start the entire stack
docker compose up --build -d

# 3. Run initial migrations
docker compose exec api python scripts/migrate.py

Access Points
Service
URL
Credentials
API + Dashboard
http://localhost:8000
—
Swagger UI
http://localhost:8000/docs
—
Grafana
http://localhost:3000
admin / admin
Prometheus
http://localhost:9090
—
MLflow
http://localhost:5000
—
PostgreSQL
localhost:5432
see .env
Redpanda Console
http://localhost:8080
—
📊 Live Dashboard
Real-time KPIs: login volume, risk score, blocked attacks, model confidence
Hourly trends with beautiful charts
Top risky users / IPs / attack signatures
Drill-down tables with one-click investigation
Live updates via WebSocket (/ws/monitoring)
🔬 Core Endpoints
Authentication & Telemetry
POST /api/v1/auth/register
POST /api/v1/auth/login ← monitored & scored
POST /api/v1/telemetry/network
POST /api/v1/telemetry/network/stream ← Kafka producer
POST /api/v1/telemetry/attack-sequence
Defense & Monitoring
GET /api/v1/defense/risk/{user_id}
POST /api/v1/models/train-bootstrap
POST /api/v1/models/auto-retrain
GET /api/v1/monitoring/overview
GET /api/v1/monitoring/drilldown
GET /metrics (Prometheus)
GET /ws/monitoring (WebSocket live feed)
🤖 ML & Auto-Retraining
The engine continuously improves:
AUTO_RETRAIN_ENABLED=true
AUTO_RETRAIN_INTERVAL_MINUTES=30
RETRAIN_MIN_EVENTS=250
RETRAIN_ACCEPTANCE_THRESHOLD=0.55
Flow:
Candidate pipeline generated
Evaluated against historical data
Compared with baseline
Accepted → deployed + logged in MLflow
Rejected → automatic rollback
☁️ Deploy to AWS (Production-Ready)
cd infra/terraform/aws
cp terraform.tfvars.example terraform.tfvars
make tf-apply   # or terraform apply
Provisions:
ECS Fargate (API + Dashboard)
RDS PostgreSQL
MSK Serverless (managed Kafka)
ALB + WAF
S3 artifacts
GuardDuty enabled
🧪 Testing & Resilience
# Load test (100 users)
locust -f load/locustfile.py --headless --users 100 --spawn-rate 10 --run-time 2m

# Chaos engineering (DB restart)
./scripts/chaos_db_restart.ps1 -DowntimeSeconds 20

# Unit tests
pytest -q
📁 Project Structure
CrucibleAuth-Defense-Engine/
├── app/                 # FastAPI application
│   ├── api/             # REST routes
│   ├── core/            # config & security
│   ├── db/              # models & sessions
│   ├── ml/              # all ML/DL models + DQN agent
│   ├── services/        # orchestration, streaming, monitoring
│   └── web/             # dashboard frontend
├── infra/terraform/aws/ # AWS IaC
├── observability/       # Prometheus + Grafana dashboards
├── load/                # Locust scenarios
├── tests/chaos/         # resilience tests
├── alembic/             # DB migrations
├── scripts/             # helpers & chaos
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── .env.example
🛠 Tech Stack (Full)
Backend: FastAPI + Uvicorn
Database: PostgreSQL + SQLAlchemy + Alembic
ML/DL: scikit-learn, TensorFlow/PyTorch (Isolation Forest, One-Class SVM, LSTM+GRU, Transformer, RNN+Markov, DQN)
Streaming: Redpanda / Kafka
Observability: Prometheus, Grafana, OpenTelemetry, MLflow
Infrastructure: Docker, Terraform (AWS)
Testing: Locust, pytest, PowerShell chaos scripts
Made with ❤️ for the cybersecurity & AI community
⭐ Star the repo if you love battle-tested auth defense!
🐛 Found a bug? Open an issue — contributions welcome!
License: MIT
Author: Maykon Lincoln
Version: 1.0.0 (Feb 2026)

