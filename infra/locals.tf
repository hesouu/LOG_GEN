locals {
  # 자동으로 계산하여 AZ 영역 결정 => a, b 선택될 것임
  availability_zones = slice(
    data.aws_availability_zones.available.names, # 사용가능한 az 목록
    0,                                           # 시작인덱스
    length(var.public_subnet_cidrs)              # 끝인덱스 => 2
  )

  # 기타 이름 설정
  cluster_name    = "${var.project_name}-cluster"
  task_family     = "${var.project_name}-task"
  repository_name = "${var.project_name}-repo"
  log_group_name  = "/ecs/${var.project_name}"
}