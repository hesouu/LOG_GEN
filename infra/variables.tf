variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "리소스 이름에 사용할 프로젝트명"
  type        = string
  default     = "de-ai-09-loggen"
}

variable "vpc_cidr" {
  description = "VPC CIDR, fargate 전용"
  type        = string
  # 대역 수정 => 0 => 20
  default = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public Subnet CIDR 목록, fargate task 작동시 매번 다른 가용영역 사용"
  type        = list(string)
  # AZ 가용영역을 2개 사용 염두
  default = ["10.20.1.0/24", "10.20.2.0/24"]

  # 유효성 검사
  validation {
    # 최소 1개이상이면 정상
    condition     = length(var.public_subnet_cidrs) >= 1
    error_message = "최소 1개 퍼블릭 서브넷 CIDR 필수임"
  }
}

# fargate task CPU
variable "task_cpu" {
  description = "cpu unit => 512 == 0.5 vCPU"
  type        = number
  default     = 512
}

# fargate task MEMORY
variable "task_memory" {
  description = "memory Mib"
  type        = number
  default     = 1024
}

# cloudwatch log 보관 일수
variable "log_retention_days" {
  description = "cloudwatch log retention period"
  type        = number
  default     = 7
}

# ECS TASK가 ECR 이미지 사용시 태그 -> latest
variable "image_tag" {
  description = "task가 정의될때 참고하는 태그명, 가징 최신"
  type        = string
  default     = "latest"
}

# [브론즈 추가]
# Kinesis Data Streams : KDS
# 성능 영향 -> shard 개수, 데이터 보관 기간(retention)
# 프로비저닝 방식으로 구성한다 -> 샤드수 직접 지정 <-> 온디맨드 (자율구성)
variable "kinesis_shard_count" {
  description = "KDS's shard count"
  type        = number
  default     = 1
}

# 전송되지 않은 데이터는 하루만 보관하겠다!!
variable "kinesis_retention_hour" {
  description = "KDS's retention period in hours"
  type        = number
  default     = 24
}


# Amazon Data Firehose : ADF
# 최소 1 MiB, 최대 128 MiB입니다. 5 MiB을(를) 권장
# 결과는 빠르게 볼수 있다 -> 향후 조절 필요
variable "firehose_buffer_size" {
  description = "해당 크기만큼 데이터가 쌓이면 강제 전송"
  type        = number
  default     = 1
}
# 최소 0 초, 최대 900 초입니다. 300 초을(를) 권장
variable "firehose_buffer_interval" {
  description = "해당 시간만큼 데이터가 쌓이면 강제 전송"
  type        = number
  default     = 60
}


# [실버 추가]
# 실버 레이어에서 출력용 사용
variable "silver_kinesis_shard_count" {
  description = "KDS's shard count"
  type        = number
  default     = 1
}
# kinesis 에서 미전송된 데이터 보관기간
variable "silver_kinesis_retention_hour" {
  description = "KDS's retention period in hours"
  type        = number
  default     = 24
}

# PyFlink 버전(런타임 환경의 버전) 1.20 사용
variable "flink_runtime_environment" {
  description = "Managed Service for Apache Flink의 런타임 환경버전"
  type        = string
  default     = "FLINK-1_20"
}
# Flink 어플리케이션의 병렬구성수
# 현재는 1을 기본값, 최소 실행 단위
variable "flink_parallelism" {
  description = "Initial Flink application parallelism"
  type        = number
  default     = 1
}
# KPU( kinesis Processing Unit) 하나당 Parallel task 수 설정
# 기본 컴퓨팅의 과금 단위
variable "flink_parallelism_per_kpu" {
  description = "Flink parallel tasks per KPU"
  type        = number
  default     = 3
}
# flink 은 실행 시켜두어야만 실졔 처리 됨
# true : 인프라 적용되면 => 실행 => 실습 편의상 설정
# false: 실제 사용시 사용
variable "flink_start_application" {
  description = "Whether Terraform should start the Managed Flink application"
  type        = bool
  default     = true
}
# Flink를 가동한후 입력쪽(브론즈방향) kinesis에서 데이터를 읽을때 어디서 부터 처리할것인가? 설정
# 데이터는 계쏙해서 전송중 -> 추후 flink 가동 
# -> 가동전에 도달한 데이터도 처리할 것인가? flink 가동 이후 도착한 데이터만 처리할것인가?
# LATEST : flink 가동 후 들어오는 데이터만 처리
# TRIM_HORIZON : kinesis에 남아 있는 과거 로그 데이터 모두 처리 -> 재처리/테스트/전체 데이터 처리

variable "flink_source_init_poisition" {
  description = "flink가 데이터 처리시 입력왼쪽의 어디서부터 처리할 것인가 설정"
  type        = string
  default     = "LATEST"
  
  # 변수의 값으로 올수 있는 내용들을 제약
  validation {
    condition = contains([
      "LATEST",
      "TRIM_HORIZON"
    ], var.flink_source_init_poisition)
    error_message = "flink_source_init_poisition is only LATEST or TRIM_HORIZON"
  }
}
