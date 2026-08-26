# ---------------------------------------------
# Gold layer - AWS Glue Data Catalog
# ---------------------------------------------
# 1. 데이터베이스 구성
resource "aws_glue_catalog_database" "gold" {
  name = "${lower(replace(var.project_name, "-", "_"))}_gold_glue_db"
}

# 2. 테이블 구성
resource "aws_glue_catalog_table" "gold" {
  # 테이블명
  name = "gold_logs_tbl"
  # 테이블의 원소속(데이터베이스) 설정
  database_name = aws_glue_catalog_database.gold.name
  # 데이터는 glue 외부에 존재함 원데이터는 s3에 저장되어 있음 -> 데이터가 glue 외부에 있으므로
  table_type = "EXTERNAL_TABLE"

  # 파라미터 지정
  parameters = {
    "classification"             = "parquet"
    "EXTERNAL"                  = "TRUE"
    "parquet.compression"       = "SNAPPY"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2026,2040"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.month.digits"   = "2"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "projection.day.digits"     = "2"
    "projection.hour.type"      = "integer"
    "projection.hour.range"     = "0,23"
    "projection.hour.digits"    = "2"
    "storage.location.template" = "s3://${aws_s3_bucket.data.bucket}/gold/year=$${year}/month=$${month}/day=$${day}/hour=$${hour}"
  }

  # 실제 데이터가 어디에 존재, 어떤 파일 형식, 어떤 스키마를 가지는지 구성
  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data.bucket}/gold/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    compressed    = true

    # parquet 파일과 Glue/Athena등 테이블간 사이에서 데이터 구조 해석하는 역활
    ser_de_info {
      name                  = "gold-parquet"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    # gold 스키마 구성 -> 컬럼 배치 -> 최종 목표 데이터 형태를 고려하여 구성
    # 실버 => 아테나 sql 수행하여 어떤것들 가능한지 체크
    columns {
      name = "processed_at"
      type = "string"
    }
    columns {
      name = "domain"
      type = "string"
    }
    columns {
      name = "event_count"
      type = "bigint"
    }
    columns {
      name = "success_count"
      type = "bigint"
    }
    columns {
      name = "error_count"
      type = "bigint"
    }
    columns {
      name = "avg_latency_ms"
      type = "double"
    }
    columns {
      name = "min_latency_ms"
      type = "bigint"
    }
    columns {
      name = "max_latency_ms"
      type = "bigint"
    }
    columns {
      name = "result"
      type = "string"
    }
    columns {
      name = "gold_schema_version"
      type = "string"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
  partition_keys {
    name = "month"
    type = "string"
  }
  partition_keys {
    name = "day"
    type = "string"
  }
  partition_keys {
    name = "hour"
    type = "string"
  }
}