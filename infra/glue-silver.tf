# -------------------------------------------------
# sliver layer - AWS Glue Data Catalog
# -------------------------------------------------

# 데이터 구조, 위치등 Meta 데이터를 관리하는 서비스
# aws_glue_catalog_database > Database > de-ai-09-loggen-silver-glue-db

# 1. 데이터베이스 구성
resource "aws_glue_catalog_database" "silver" {
  name = "${lower(replace(var.project_name, "-", "_"))}_silver_glue_db"
  #  name = "${var.project_name}-silver-glue-db"
}

# 2. 테이블 구성, 데이터베이스 내부에 테이블을 수십개 정의 가능
#   s3 silver에 저장되는 parquet 데이터 한개에 대해 논리적인 테이블 정의
#   이 구조를 기반으로 SQL 수행(athena등) => 특정 데이터 획득 (향후 배치 프로세싱에서 airflow 기반으로 처리)
resource "aws_glue_catalog_table" "silver" {
  # 테이블명
  name = "silver_logs_tbl"
  # 테이블의 원소속 (데이터베이스) 설정
  database_name = aws_glue_catalog_database.silver.name
  # 데이터는 glue 외부에 존재함 원데이터는 s3에 저장되어 있음 -> 데이터가 외부에 있으므로
  table_type = "EXTERNAL_TABLE"

  # 파라미터 지정
  parameters = {
    # 실 데이터가 glue 외부에 존재함을 표시
    EXTERNAL = "TRUE"
    # parquet의 압축 방식
    "parquet.compression" = "SNAPPY"
    # 파티션 활성화 (s3://버킷/silver/year=2026/....), 파티션화 되어 저장되어 있음 (partition projection)
    "projection.enabled" = "true"
    # 파티션 정보 -> year, month, day, hour -> 타임, 값 범위 지정
    # year
    "projection.year.tpye"  = "integer"
    "projection.year.range" = "2026,2040" # 뒤에 2040은 설정값, 2026은 현재로 가정
    # month
    # 1 -> 01, 2 -> 02 => digits = 2
    "projection.month.tpye"  = "integer"
    "projection.month.range" = "1,12"
    "projection.month.digits" = "2"     # 2자리수로 맞춤
    # day
    "projection.day.tpye"  = "integer"
    "projection.day.range" = "1,31"
    "projection.day.digits" = "2"
    # hour
    "projection.hour.tpye"  = "integer"
    "projection.hour.range" = "0,23"
    "projection.hour.digits" = "2"

    # 파티션 S3 경로 규칙
    # sql : ~ where year = '2026' ...
    # $${year} => ${year} 자체로 전달하기 위해서 앞에 $ 추가한 표현
    "storage.location.template" = "s3://${aws_s3_bucket.data.bucket}/silver/year=$${year}/month=$${month}/day=$${day}/hour=$${hour}"
  }
}