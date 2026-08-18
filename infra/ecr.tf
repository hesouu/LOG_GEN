# 로그 생성기가 구동되는 컨테이너의 이미지가 저장되는 저장소
# 1. 저장소 생성
resource "aws_ecr_repository" "generator" {
  name = local.repository_name
  # 저장소 삭제될때 -> 남아 있는 이미지가 있다면 -> 삭제 x or 이미지 삭제 + 저장소 삭제 옵션
  force_delete = true # 차후 정책 고민

  # 같은 태그로 이미지 갱신 허용
  image_tag_mutability = "MUTABLE"

  # 이미지 푸시시 자동 검사
  image_scanning_configuration {
    scan_on_push = true
  }
}

# 2. 저장소 저장 비용 관리 정책 결정 -> 오래된 이미지를 언제까지 보관할 것인가
resource "aws_ecr_lifecycle_policy" "generator" {
  repository = aws_ecr_repository.generator.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "keep 20 images"
        selection = {
          tagStatus   = "any"                # 태그 타입 상관 없음
          countType   = "imageCountMoreThan" # 20개 초과되면 액션 시작
          countNumber = 20                   # 20개만 유지
        }
        # 삭제 행동
        action = {
          type = "expire"
        }
      }
    ]
  })
}