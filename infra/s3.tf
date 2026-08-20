# 브론즈/실버/골드 데이터가 저장될 데이터 레이크(s3 사용) 정의
resource "aws_s3_bucket" "data" {
  # 버킷을 1개 구성, 하위에 브론즈, 실버, 골드 레이어 관리
  bucket = "${var.project_name}-s3-bk-${data.aws_caller_identity.current.account_id}"

  # 버킷 삭제될때 내부 데이터도 같이 삭제되게 할것인가?
  force_destroy = true # 저장된 객체 모두 삭제 처리(일단 구성)
}

# 외부 public 접근 차단 (내부에서만, 권한 있는 경우에만 접근)
resource "aws_s3_bucket_public_access_block" "data" {
  # 버킷 지정
  bucket = aws_s3_bucket.data.id

  # 정책 설정
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}