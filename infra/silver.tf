# 실버 레이어 에서 사용되는 kinesis
# flink에서 전송된 데이터를 획득 -> firehose로 전송
resource "aws_kinesis_stream" "silver" {
  name             = local.silver_kinesis_stream_name
  shard_count      = var.silver_kinesis_shard_count
  retention_period = var.silver_kinesis_retention_hour

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = {
    DataLayer = "silver"
  }
}

# silver 레이어의 kinesis와 연동되는 firehose
resource "aws_kinesis_firehose_delivery_stream" "silver" {
  # 이름
  name        = local.silver_firehose_name
  destination = "extended_s3"

  # 입력소스 (키네시스, 역활 설정)
  kinesis_source_configuration {
    kinesis_stream_arn = aws_kinesis_stream.silver.arn
    role_arn           = aws_iam_role.firehose_silver.arn
  }

  # 출력대상
  extended_s3_configuration {
    # 버킷
    bucket_arn = aws_s3_bucket.data.arn
    # 역활
    role_arn = aws_iam_role.firehose_silver.arn

    # 버퍼 관련 용량, 시간 설정
    buffering_size     = var.firehose_buffer_size     # 1Mib
    buffering_interval = var.firehose_buffer_interval # 60초

    # 데이터를 모아둔상태(버퍼링)에서 기록 -> 포멧
    # [GLUE] Firehose가 JSON을 Parquet로 변환 처리함, S3에 자체 압축 옵션은 UNCOMPRESSED로 표기
    compression_format = "UNCOMPRESSED"
    # 데이터 레코드 압축
    #compression_format = "GZIP" # GZIP으로 압축

    # S3 버킷 및 S3 오류 출력 접두사 시간대
    custom_time_zone = "Asia/Seoul"

    # [GLUE] 컨버전에 대한 구성 설정 (JSON => Glue Schema(사전에 정의된 테이블/스키마 <- 데이터구조/타입) => parquet)
    data_format_conversion_configuration {
      # 구성 정보 사용
      enabled = true
      # 입력원 flink 통해서 나온 JSON임
      input_format_configuration {
        # ser_de (serializer/deserializer)
        deserializer {
          open_x_json_ser_de {
            case_insensitive                         = true
            convert_dots_in_json_keys_to_underscores = false
          }
        }
      }
      # JONS->parquet 변환시 참고할 스키마 (glue-silver.tf에 설정)
      schema_configuration {
        # 데이터베이스 명
        database_name = aws_glue_catalog_database.silver.name
        # 테이블 명
        table_name = aws_glue_catalog_table.silver.name
        # role 리소스명
        role_arn = aws_iam_role.firehose_silver.arn
        # 리전명
        region = var.aws_region
        # 버전
        version_id = "LATEST"
      }
      # 출력 SNAPPY 압축을 통한 Parquet임
      output_format_configuration {
        serializer {
          parquet_ser_de {
            compression = "SNAPPY"
          }
        }
      }
    }

    # 아래 처럼 구성 => partition pruning => Athena/opensearch/Glue/spark등 열기반으로 데이터 추출 유용
    # S3 버킷 접두사
    # bronze/year=2026/month=08/day=20/hour=11/.. 이렇게 파티션 가능 -> 검색 속도 빨라짐
    prefix = "silver/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"

    # S3 버킷 오류 출력 접두사
    # 현재는 에러를 단독 구성, 브론즈/실버/골드등 계층 구분 하지 x => 필요시 구성 가능
    # 경로상에 에러애 대한 타입 지정 -> 유형별로 에러가 모이게 작성
    # [실버 수정]
    error_output_prefix = "errors/silver/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/"
  }

  # 의존성
  depends_on = [
    # 해당 정책 입력/출력 엑세스 권한 생성된 후에 firehose 생성되도록 설정
    aws_iam_role_policy.firehose_silver
  ]
}