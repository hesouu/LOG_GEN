# Managed Service for apache flink

locals {
  # flink 앱 경로. flink-silver.zip 파일은 스크립트에서 정의, flink 최종 산출물의 경로
  # ${path.module} => ~/infra (현재 디렉토리 위치)
  flink_artifact_path = "${path.module}/../flink/target/flink-silver.zip"

  # zip 내용에 MD5 해시를 계산하여 코드 변경 여부 식별 용도
  flink_artifact_hash = filemd5(local.flink_artifact_path)
}

# flink_app이란 flink-silver.zip이고, aws s3에 위치해야 함
resource "aws_s3_object" "flink_app" {
  # 버킷 지정
  bucket = aws_s3_bucket.data.id
  # flink 앱 지정 => 키
  key = "flink/applications/flink-silver-${local.flink_artifact_hash}.zip"
  # 로커 -> s3 업로드한 zip 경로
  source = local.flink_artifact_path
  # zip에 대한 해시검사, 소스 변경되면 감지됨
  source_hash = local.flink_artifact_hash
  # 의존성, 사전에 aws_s3_bucket_public_access_block 완료된 후 진행
  depends_on = [
    aws_s3_bucket_public_access_block.data
  ]
}

# flink 자체 내용
resource "aws_kinesisanalyticsv2_application" "silver" {
  # flink 리소스 이름
  name = local.flink_application_name
  # 설명
  description = "Raw(Bronze) Kinesis events to Silver Kinesis using PyFlink"
  # 런타임 환경 -> 1.20
  runtime_environment = var.flink_runtime_environment
  # role
  service_execution_role = aws_iam_role.flink.arn
  # 앱 : true면 즉시 실행, false 생성만 하고 실해은 직접 세팅
  start_application = var.flink_start_application

  application_configuration {
    # 스냅샷 사용 x
    application_snapshot_configuration {
      snapshots_enabled = false
    }

    application_code_configuration {
      # 앱의 실제 위치
      code_content {
        s3_content_location {
          bucket_arn = aws_s3_bucket.data.arn
          file_key   = aws_s3_object.flink_app.key
        }
      }
      # 앱의 타임 zip
      code_content_type = "ZIPFILE"
    }

    environment_properties {
      # raw(bronze) 레베의 kinesis 리소스
      property_group {
        property_group_id = "InputStream0"

        property_map = {
          "stream.arn"                 = aws_kinesis_stream.logs.arn
          "aws.region"                 = var.aws_region
          "flink.source.init.position" = var.flink_source_init_position
        }
      }
      # silver kinesis, flink에서 출력하는 대상
      property_group {
        property_group_id = "OutputStream0"

        property_map = {
          "stream.arn" = aws_kinesis_stream.silver.arn
          "aws.region" = var.aws_region
        }
      }

      property_group {
        # AWS Managed Flink를 인식하는 예약 그룹명 (실행 옵션) -> 고정값
        property_group_id = "kinesis.analytics.flink.run.options"

        property_map = {
          # flink 앱의 엔트리 포인트
          "python" = "main.py"
          # pyFlink에서 kinesis 접근 -> 드라이브(라이브러리) 필요 -> *.jar
          "jarfile" = "lib/pyflink-dependencies.jar"
          # python UDF Worker가 transform.py를 import 하도록 등록
          "pyFiles" = "transform.py"
        }
      }
    }

    # flink 엔진 자체에 대한 설정
    flink_application_configuration {
      # 장애 복구시  checkpoint 설정
      checkpoint_configuration {
        configuration_type = "DEFAULT" # AWS 기본값 따른다
      }
      # flink 로그, 매트릭 수집 수준 설정
      monitoring_configuration {
        configuration_type = "CUSTOM"      # 직접 구성
        log_level          = "INFO"        # 정보 수준
        metrics_level      = "APPLICATION" # 애플리케이션 단위(레벨) 정보
      }
      # 애플리케이션 구동시 병렬 처리, KPU 설정
      parallelism_configuration {
        configuration_type   = "CUSTOM"                      # 직접 설정
        auto_scaling_enabled = true                          # 부하에 따라 자동 조절
        parallelism          = var.flink_parallelism         # 기본값
        parallelism_per_kpu  = var.flink_parallelism_per_kpu # 기본값
      }
    }
  }

  # flink 실행 => 로그 (정상, 에러) => cloudwatch 저장
  cloudwatch_logging_options {
    log_stream_arn = aws_cloudwatch_log_stream.flink.arn
  }

  # 사전에 role 정책 완료, 앱 설정 완료
  depends_on = [
    aws_iam_role_policy.flink,
    aws_s3_object.flink_app
  ]

  tags = {
    DataLayer = "silver"
    Processor = "flink"
  }
}