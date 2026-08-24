# 브론즈->실버 데이터 파이프라인 구성중 flink에서 오염된 데이터가 걸러져서 저장되는 파이프라인
# 브론즈 => flink => rejecred_kinesis => firehose => s3 rejected/...

# flink에서 전송된 데이터를 획득 -> firehose로 전송
resource "aws_kinesis_stream" "rejected" {
  # 리소스명 수정
  name             = local.rejected_kinesis_stream_name
  # 샤드, 보관일 별도 설정 없어서 공통 적용 -> 리소스별로 상이할수 있음
  shard_count      = var.rejected_kinesis_shard_count
  retention_period = var.silver_kinesis_retention_hour

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = {
    # 태그 수정
    DataLayer = "rejected"
  }
}

# rejected kinesis와 연동되는 firehose
resource "aws_kinesis_firehose_delivery_stream" "rejected" {
  # 이름 교체
  name        = local.rejected_firehose_name
  destination = "extended_s3"

  # 입력소스 (키네시스, 역활 설정)
  kinesis_source_configuration {
    kinesis_stream_arn = aws_kinesis_stream.rejected.arn
    role_arn           = aws_iam_role.firehose_rejected.arn
  }

  # 출력대상
  extended_s3_configuration {
    # 버킷
    bucket_arn = aws_s3_bucket.data.arn
    # 역활
    role_arn = aws_iam_role.firehose_rejected.arn

    # 버퍼 관련 용량, 시간 설정
    buffering_size     = var.firehose_buffer_size     # 1Mib
    buffering_interval = var.firehose_buffer_interval # 60초

    # 데이터를 모아둔상태(버퍼링)에서 기록 -> 포멧
    # 데이터 레코드 압축
    # compression_format = "UNCOMPRESSED" # 1차는 원본 지정, 활성화되지 않음
    compression_format = "GZIP" # GZIP으로 압축, 향후 parquet 저장 x

    # S3 버킷 및 S3 오류 출력 접두사 시간대
    custom_time_zone = "Asia/Seoul"

    # 아래 처럼 구성 => partition pruning => Athena/opensearch/Glue/spark등 열기반으로 데이터 추출 유용
    # S3 버킷 접두사
    # bronze/year=2026/month=08/day=20/hour=11/.. 이렇게 파티션 가능 -> 검색 속도 빨라짐
    prefix = "rejected/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"

    # S3 버킷 오류 출력 접두사
    # 현재는 에러를 단독 구성, 브론즈/실버/골드등 계층 구분 하지 x => 필요시 구성 가능
    # 경로상에 에러애 대한 타입 지정 -> 유형별로 에러가 모이게 작성
    # [실버 수정]
    error_output_prefix = "errors/rejected/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
  }

  # 의존성
  depends_on = [
    # 해당 정책 입력/출력 엑세스 권한 생성된 후에 firehose 생성되도록 설정
    aws_iam_role_policy.firehose_rejected
  ]
}