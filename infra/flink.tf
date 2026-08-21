locals {
    # flink 앱 경로
  flink_artifact_path = "${path.module}/../flink/target/flink-silver.zip"
  flink_artifact_hash = filemd5(local.flink_artifact_path)
}

resource "aws_s3_object" "flink_app" {
  bucket = aws_s3_bucket.data.id
  key    = "flink/applications/flink-silver-${local.flink_artifact_hash}.zip"

  source      = local.flink_artifact_path
  source_hash = local.flink_artifact_hash

  depends_on = [
    aws_s3_bucket_public_access_block.data
  ]
}

resource "aws_kinesisanalyticsv2_application" "silver" {
  name                   = local.flink_application_name
  description            = "Raw Kinesis events to Silver Kinesis using PyFlink"
  runtime_environment    = var.flink_runtime_environment
  service_execution_role = aws_iam_role.flink.arn
  start_application      = var.flink_start_application

  application_configuration {
    application_snapshot_configuration {
      snapshots_enabled = false
    }

    application_code_configuration {
      code_content {
        s3_content_location {
          bucket_arn = aws_s3_bucket.data.arn
          file_key   = aws_s3_object.flink_app.key
        }
      }

      code_content_type = "ZIPFILE"
    }

    environment_properties {
      property_group {
        property_group_id = "InputStream"

        property_map = {
          "stream.arn"                 = aws_kinesis_stream.bronze.arn
          "aws.region"                 = var.aws_region
          "flink.source.init.position" = var.flink_source_init_position
        }
      }

      property_group {
        property_group_id = "OutputStream"

        property_map = {
          "stream.arn" = aws_kinesis_stream.silver.arn
          "aws.region" = var.aws_region
        }
      }

      property_group {
        property_group_id = "kinesis.analytics.flink.run.options"

        property_map = {
          "python"  = "main.py"
          "jarfile" = "lib/pyflink-dependencies.jar"
          "pyFiles" = "transform.py"
        }
      }
    }

    flink_application_configuration {
      checkpoint_configuration {
        configuration_type = "DEFAULT"
      }

      monitoring_configuration {
        configuration_type = "CUSTOM"
        log_level          = "INFO"
        metrics_level      = "APPLICATION"
      }

      parallelism_configuration {
        configuration_type   = "CUSTOM"
        auto_scaling_enabled = true
        parallelism          = var.flink_parallelism
        parallelism_per_kpu  = var.flink_parallelism_per_kpu
      }
    }
  }

  cloudwatch_logging_options {
    log_stream_arn = aws_cloudwatch_log_stream.flink.arn
  }

  depends_on = [
    aws_iam_role_policy.flink,
    aws_s3_object.flink_app
  ]

  tags = {
    DataLayer = "silver"
    Processor = "flink"
  }
}