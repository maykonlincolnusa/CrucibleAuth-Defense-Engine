variable "aws_region" {
  description = "AWS region for deployment."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project prefix for resource naming."
  type        = string
  default     = "security-defense"
}

variable "environment" {
  description = "Environment tag and naming suffix."
  type        = string
  default     = "prod"
}

variable "tags" {
  description = "Additional tags for all resources."
  type        = map(string)
  default     = {}
}

variable "vpc_cidr" {
  description = "CIDR block for VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs."
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs."
  type        = list(string)
  default     = ["10.20.11.0/24", "10.20.12.0/24"]
}

variable "container_image" {
  description = "Container image URI pushed to ECR."
  type        = string
}

variable "api_port" {
  description = "Container and service port for FastAPI."
  type        = number
  default     = 8000
}

variable "ecs_cpu" {
  description = "Task CPU units."
  type        = number
  default     = 1024
}

variable "ecs_memory" {
  description = "Task memory in MiB."
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Desired number of ECS tasks."
  type        = number
  default     = 2
}

variable "db_name" {
  description = "RDS database name."
  type        = string
  default     = "security_lab"
}

variable "db_username" {
  description = "RDS master username."
  type        = string
  default     = "security"
}

variable "db_password" {
  description = "RDS master password."
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.medium"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage (GB)."
  type        = number
  default     = 100
}

variable "db_engine_version" {
  description = "PostgreSQL engine version."
  type        = string
  default     = "16.3"
}

variable "log_retention_days" {
  description = "CloudWatch retention for API logs."
  type        = number
  default     = 14
}

variable "kafka_topic" {
  description = "Kafka topic consumed by the app."
  type        = string
  default     = "security.network.flows"
}

variable "mlflow_tracking_uri" {
  description = "MLflow tracking URI injected in ECS."
  type        = string
  default     = "file:/tmp/mlruns"
}

variable "enable_waf" {
  description = "Enable AWS WAF on top of ALB."
  type        = bool
  default     = true
}

variable "enable_guardduty" {
  description = "Enable AWS GuardDuty detector."
  type        = bool
  default     = true
}
