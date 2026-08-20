provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project  = var.project_name
      ManageBy = "Terraform"
      Purpose  = "로그 제너레이터"
    }
  }
}

# 가용영역 조회 (a or a,b or .... a,b,c,d)
data "aws_availability_zones" "available" {
  state = "available"
}

# [브론즈 추가] AWS Account ID 조회
data "aws_caller_identity" "current" {}