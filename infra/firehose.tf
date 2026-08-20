# kinesis -> firehose -> s3
resource "aws_kinesis_firehose_delivery_stream" "logs" {
  # 이름
  name        = local.firehose_name
  destination = "extended_s3"
    
  # 입력소스 (키네시스, 역할 지정)
  kinesis_source_configuration {
    kinesis_stream_arn = aws_kinesis_stream.logs.arn
    role_arn = aws_iam_role.firehose.arn
  }

  # 출력대상
  extended_s3_configuration {
    # 버킷
    bucket_arn = aws_s3_bucket.data.arn
    # 역할
    role_arn = aws_iam_role.firehose.arn

    # 버퍼 관련 용량, 시간 설정
    buffering_size = var.firehose_buffer_size   # 1Mib
    buffering_interval = var.firehose_buffer_interval  # 60초

    # 데이터를 모아둔 상태(버퍼링)에서 기록 -> 포멧
    # 데이터를 레코드 압축
    compression_format = "UNCOMPRESSED" # 1차는 원본 지정
    # compression_format = "GZIP" #GZIP으로 압축

    # S3 버킷 및 S3 오류 출력 접두사 시간대
    custom_time_zone = "Asia/Seoul"

    # 아래처럼 구성 -> partition pruning -> Athena/openserch/Glue/spark등 열기반으로 데이터 추출 유용
    # S3 버킷 접두사
    # bronze/year=2026/month=08/day=20/hour=11/.. 이렇게 파티션 가능 -> 검색 속도 빨라짐
    prefix = "bronze/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"

    # S3 버킷 오류 출력 접두사
    # 현재는 에러를 단독 구성, 브론즈/실버/골드등 계층 구분 하지 x => 필요시 구성
    # 경로상에 에러에 대한 타입 지정
    error_output_prefix =  "error/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
  }

  # 의존성
  depends_on = [ 
    # 해당 정책 입력/출력 엑세스 권한 생성된 후에 firehose 생성되도록 설정
    aws_iam_role_policy.firehose
  ]
}