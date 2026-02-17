resource "aws_msk_serverless_cluster" "kafka" {
  cluster_name = "${local.name_prefix}-msk-serverless"

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.msk.id]
  }

  client_authentication {
    sasl {
      iam {
        enabled = true
      }
    }
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-msk-serverless" })
}
