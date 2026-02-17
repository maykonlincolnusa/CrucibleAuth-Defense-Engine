locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.tags
  )

  artifacts_bucket_name = lower(
    "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-${var.aws_region}-artifacts"
  )
}
