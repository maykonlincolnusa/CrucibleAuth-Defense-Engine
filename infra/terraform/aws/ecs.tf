resource "aws_ecr_repository" "api" {
  name                 = "${local.name_prefix}-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-api" })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name_prefix}-api"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${local.name_prefix}-ecs-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name               = "${local.name_prefix}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = local.common_tags
}

resource "aws_iam_role_policy" "ecs_task_kafka_access" {
  name = "${local.name_prefix}-ecs-task-kafka"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Action = [
            "kafka-cluster:Connect",
            "kafka-cluster:DescribeCluster",
            "kafka-cluster:DescribeTopic",
            "kafka-cluster:ReadData",
            "kafka-cluster:WriteData",
            "kafka-cluster:DescribeGroup",
            "kafka-cluster:AlterGroup"
          ]
          Resource = ["*"]
        }
      ]
    }
  )
}

resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.common_tags
}

resource "aws_lb" "api" {
  name               = substr("${local.name_prefix}-alb", 0, 32)
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = local.common_tags
}

resource "aws_lb_target_group" "api" {
  name        = substr("${local.name_prefix}-tg", 0, 32)
  port        = var.api_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    path                = "/health"
    matcher             = "200-399"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 20
  }

  tags = local.common_tags
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name_prefix}-api"
  cpu                      = tostring(var.ecs_cpu)
  memory                   = tostring(var.ecs_memory)
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode(
    [
      {
        name      = "api"
        image     = var.container_image
        essential = true
        portMappings = [
          {
            containerPort = var.api_port
            hostPort      = var.api_port
            protocol      = "tcp"
          }
        ]
        environment = [
          { name = "APP_ENV", value = var.environment },
          { name = "APP_PORT", value = tostring(var.api_port) },
          {
            name  = "DATABASE_URL",
            value = "postgresql+psycopg://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
          },
          { name = "KAFKA_ENABLED", value = "true" },
          { name = "KAFKA_BOOTSTRAP_SERVERS", value = aws_msk_serverless_cluster.kafka.bootstrap_brokers_sasl_iam },
          { name = "KAFKA_NETWORK_TOPIC", value = var.kafka_topic },
          { name = "KAFKA_CONSUMER_GROUP", value = "${local.name_prefix}-api" },
          { name = "MLFLOW_TRACKING_URI", value = var.mlflow_tracking_uri },
          { name = "MODEL_DIR", value = "/tmp/artifacts" },
          { name = "METRICS_ENABLED", value = "true" }
        ]
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group         = aws_cloudwatch_log_group.api.name
            awslogs-region        = var.aws_region
            awslogs-stream-prefix = "api"
          }
        }
      }
    ]
  )

  tags = local.common_tags
}

resource "aws_ecs_service" "api" {
  name            = "${local.name_prefix}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  network_configuration {
    assign_public_ip = true
    security_groups  = [aws_security_group.ecs.id]
    subnets          = aws_subnet.public[*].id
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = var.api_port
  }

  depends_on = [aws_lb_listener.http]

  tags = local.common_tags
}

resource "aws_appautoscaling_target" "ecs_service" {
  max_capacity       = 5
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_cpu_target" {
  name               = "${local.name_prefix}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_service.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_service.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 60
    scale_in_cooldown  = 60
    scale_out_cooldown = 60
  }
}
