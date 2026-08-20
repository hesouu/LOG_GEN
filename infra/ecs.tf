# 컨테이너의 실행환경 제공
# 1. 클러스터 생성
resource "aws_ecs_cluster" "this" {
  name = local.cluster_name
}
# 2. Fargate에서 실행할 로그 생성기 컨테이너에 대한 실행시 명세서(률, 설정, ....)
resource "aws_ecs_task_definition" "generator" {
  # 관리단 => family, 소속그룹
  # de-ai-09-loggen-task:1 => de-ai-09-loggen-task:2 => ... 수정발생 => 넘버를 부여하여 새로 생성
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

  # [브론즈 추가]
  # 컨테이너 내부에서 파이썬으로 로그를 생성 kinesis로 전송하는 권한
  task_role_arn = aws_iam_role.ecs_task_kinesis.arn

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
        # [브론즈 추가]
        # KINESIS 기능 활성화
        { name = "KINESIS_ENABLED", value = "true" },
        # KINESIS 스트림 (KDS) 이름
        { name = "KINESIS_STREAM_NAME", value = aws_kinaesis_stream.logs.name },

        # 로그의 도메인 : 이커머스, 파이낸스, 스마트팩토리, 게임
        { name = "DOMAIN", value = "ecommerce" },
        # 로그를 몇 초 동안 생성할지 지정 300: 5분
        { name = "DURATION_SECONDS", value = "300" },
        # 최대 이벤트 생성 개수, 0:개수 제한 없음
        { name = "MAX_EVENTS", value = "0" },
        # 기본 초당 이벤트 발생량, 2.0 : 초당 2개 로그 발생
        { name = "BASE_RPS", value = "2.0" },
        # 로그 생성 속도에 적용하는 데이터 비율, 1.0:정상, 2.0 빠르게, 0.5 느리게
        { name = "TIME_SCALE", value = "1.0" },
        # 의도적으로 생성하는 오염 데이터 비율, 0.03: 3% 오염 데이터 생성 -> ETL에서 정제 처리 -> 97%만 사용
        { name = "CORRUPTION_RATE", value = "0.03" },
        # 데이터에 오염 여부 구분하는 라벨 표현, 표기 여부, false : 라벨없음 
        { name = "INCLUDE_CORRUPTION_LABEL", value = "false" },
        # 생성된 로그를 어디로ㅓ 출력할지 결정, stdout -> ecs log driver -> cloudwatch
        { name = "OUTPUT_MODE", value = "stdout" },
        # 파일 출력모드인 경우, 저장 경로, 파일명 jsonl
        { name = "LOG_FILE", value = "/tmp/generated-logs.jsonl" },
        # 로그 생성 시간대 타임존
        { name = "TIMEZONE", value = "Asia/Seoul" },
        # 페이커 패키지 인코딩. 힌극향
        { name = "FAKER_LOCALE", value = "ko_KR" },
        # 로그 생성 환경, 시뮬레이션 -> 추가 기능
        { name = "ENVIRONMENT", value = "simulation" },
        # 로그 생성의 실행 단위 구분은, manual, 20260820-001, 20260820-002, ... 이미 부여 가능
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