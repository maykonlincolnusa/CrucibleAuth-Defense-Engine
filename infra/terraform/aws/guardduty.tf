resource "aws_guardduty_detector" "main" {
  count = var.enable_guardduty ? 1 : 0

  enable = true
  tags   = local.common_tags
}
