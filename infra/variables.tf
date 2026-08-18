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