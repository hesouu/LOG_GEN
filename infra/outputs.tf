# terraform apply 후 다른 스크립트/사용자가 참조할 주요 리소스 정보 출력

# 생성된 VPC ID
output "vpc_id" {
  value = aws_vpc.this.id
}

# Fargate Task 실행에 사용할 Public Subnet 목록
output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

# Fargate Task에 적용할 Security Group ID
output "security_group_id" {
  value = aws_security_group.fargate.id
}

# 로그 생성기 ECS Cluster 이름
output "ecs_cluster_name" {
  value = aws_ecs_cluster.this.name
}

# 등록된 Task Definition ARN
output "ecs_task_definition_arn" {
  value = aws_ecs_task_definition.generator.arn
}

# Task Definition Family 이름
output "ecs_task_family" {
  value = aws_ecs_task_definition.generator.family
}

# Docker Push/Pull에 사용할 ECR Repository URL
output "ecr_repository_url" {
  value = aws_ecr_repository.generator.repository_url
}

# 로그 확인에 사용할 CloudWatch Log Group 이름
output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.generator.name
}