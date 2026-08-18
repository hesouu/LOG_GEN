# 컨테이너의 실행환경 제공
# 1. 클러스터 생성
resource "aws_ecs_cluster" "this" {
  name = local.cluster_name
}
# 2. Fargate에서 실행할 로그 생성기 컨테이너에 대한 실행시 명세서(률, 설정, ....)
resource "aws_ecs_task_definition" "generator" {
  # 관리단 => family, 소속그룹
  # de-ai-25-loggen-task:1 => de-ai-25-loggen-task:2 => ... 수정발생 => 넘버를 부여하여 새로 생성
  family = local.task_family

  # FARGATE 사용 : task가 어떻게 정의된 실행환경에서 사용한 것인지 지정 -> ec2 x, 
  requires_compatibilities = ["FARGATE"]

  # 네트워크 구성, task가 작동할때마다 a존 or b존에 매번 상이하게 할당
  network_mode = "awsvpc"

  # cpu 사용(자원)
  cpu    = tostring(var.task_cpu)
  memory = tostring(var.task_memory)

  # 권한 (ecs 테스크(기본), push, 로그기록)
  execution_role_arn = aws_iam_role.ecs_execution.arn

  # 서버리스 => 컴퓨팅 자원의 운영쳬게
  runtime_platform {
    operating_system_family = "LINUX"  # 컨테이너 실행 환경
    cpu_architecture        = "X86_64" # 아킥텍쳐
  }

  # 컨테이너 상세 정의서(명세서)
  container_definitions = jsonencode([
    {
      # 컨테이너 이름
      name = "log-generator"
      # 이미지명
      image = "${aws_ecr_repository.generator.repository_url}:${var.image_tag}"
      # 해당 컨테이너가 본 task의 필수 컨테이너다 선언
      essential = true

      # 환경변수 -> 로그 생성기의 구동 설정값(외부에서 통제)
      environment = [
        { name = "DOMAIN", value = "ecommerce" },
        { name = "DURATION_SECONDS", value = "300" },
        { name = "MAX_EVENTS", value = "0" },
        { name = "BASE_RPS", value = "2.0" },
        { name = "TIME_SCALE", value = "1.0" },
        { name = "CORRUPTION_RATE", value = "0.03" },
        { name = "INCLUDE_CORRUPTION_LABEL", value = "false" },
        { name = "OUTPUT_MODE", value = "stdout" },
        { name = "LOG_FILE", value = "/tmp/generated-logs.jsonl" },
        { name = "TIMEZONE", value = "Asia/Seoul" },
        { name = "FAKER_LOCALE", value = "ko_KR" },
        { name = "ENVIRONMENT", value = "simulation" },
        { name = "RUN_ID", value = "manual" }
      ]

      # cloudwatch로 로그 전송 설정
      logConfiguration = {
        # cloudwatch logs용으로 로그 드라이버 지정
        logDriver = "awslogs"

        # 옵션
        options = {
          # /ecs/de-ai-xx-loggen 그룹으로 전달
          "awslogs-group"  = aws_cloudwatch_log_group.generator.name
          "awslogs-region" = var.aws_region
          # generator라는 문자열 프리픽스 세팅
          "awslogs-stream-prefix" = "generator"
        }
      }
    }
  ])
}