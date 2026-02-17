# Terraform AWS Stack

Infraestrutura recomendada para este projeto em AWS:

- VPC com subnets publicas/privadas
- ECS Fargate para API/Dashboard
- Application Load Balancer
- PostgreSQL gerenciado em RDS (Multi-AZ)
- Kafka gerenciado em MSK Serverless
- S3 para artefatos e evidencias forenses
- WAF no ALB (protecoes gerenciadas)
- GuardDuty (deteccao nativa de ameacas)

## Pre-requisitos

1. Terraform `>= 1.5`
2. AWS CLI autenticado (`aws configure` ou role)
3. Imagem da API publicada no ECR

## Uso

```bash
cd infra/terraform/aws
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

## Passos de deploy da imagem

1. `terraform apply` inicial para criar ECR
2. Fazer login no ECR:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com
```

3. Build e push da imagem:

```bash
docker build -t security-defense-api .
docker tag security-defense-api:latest <ECR_REPO_URL>:latest
docker push <ECR_REPO_URL>:latest
```

4. Atualizar `container_image` em `terraform.tfvars` e aplicar novamente.

## Outputs principais

- `app_url`
- `alb_dns_name`
- `rds_endpoint`
- `msk_bootstrap_brokers_sasl_iam`
- `artifacts_bucket_name`
- `waf_web_acl_arn`
- `guardduty_detector_id`

## Observacoes de seguranca

- `db_password` deve ser forte e gerenciado por secret manager em producao.
- RDS esta em subnets privadas e sem acesso publico.
- Trafego externo entra apenas pelo ALB + WAF.
- GuardDuty habilita deteccao gerenciada no nivel da conta.
