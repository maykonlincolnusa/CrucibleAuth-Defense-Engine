output "alb_dns_name" {
  description = "Public ALB DNS name."
  value       = aws_lb.api.dns_name
}

output "app_url" {
  description = "HTTP URL for API and dashboard."
  value       = "http://${aws_lb.api.dns_name}"
}

output "ecr_repository_url" {
  description = "ECR repository URI where app image should be pushed."
  value       = aws_ecr_repository.api.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.api.name
}

output "rds_endpoint" {
  description = "PostgreSQL endpoint."
  value       = aws_db_instance.postgres.address
}

output "artifacts_bucket_name" {
  description = "S3 bucket for model artifacts and forensic payloads."
  value       = aws_s3_bucket.artifacts.bucket
}

output "msk_bootstrap_brokers_sasl_iam" {
  description = "MSK Serverless bootstrap brokers for IAM auth."
  value       = aws_msk_serverless_cluster.kafka.bootstrap_brokers_sasl_iam
}

output "waf_web_acl_arn" {
  description = "WAF ARN attached to ALB."
  value       = try(aws_wafv2_web_acl.api[0].arn, null)
}

output "guardduty_detector_id" {
  description = "GuardDuty detector ID."
  value       = try(aws_guardduty_detector.main[0].id, null)
}
