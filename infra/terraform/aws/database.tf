resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-db-subnets" })
}

resource "aws_db_instance" "postgres" {
  identifier             = "${local.name_prefix}-postgres"
  engine                 = "postgres"
  engine_version         = var.db_engine_version
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage
  storage_type           = "gp3"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  port                   = 5432
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = true
  skip_final_snapshot    = true
  backup_retention_period = 7
  deletion_protection     = false

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-postgres" })
}
