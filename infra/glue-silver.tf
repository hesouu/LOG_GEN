# ---------------------------------------------
# Silver layer - AWS Glue Data Catalog
# ---------------------------------------------

# 데이터 구조, 위치등 Meta 데이터를 관리하는 서비스
# AWS Glue Data Catalog > database > de-ai-25-loggen-silver-glue-db

# 1. 데이터베이스 구성
resource "aws_glue_catalog_database" "silver" {
  # SQL문 고려하여 _로 표기
  # 디비명
  name = "${lower(replace(var.project_name, "-", "_"))}_silver_glue_db"
  #name = "${var.project_name}-silver-glue-db"
}

# 2. 테이블 구성, 데이터베이스 내부에 테이블을 수십개 정의 가능
#    s3 silver에 저장되는 parquet 데이터 한개에 대해 논리적인 테이블 정의
#    이 구조를 기반으로 SQL 수행(athena등) => 특정(특수 목적) 데이터 획득 (향후 배치 프로세싱에서 airflow기반으로 처리)
resource "aws_glue_catalog_table" "silver" {
  # 테이블명
  name = "silver_logs_tbl"
  # 테이블의 원소속(데이터베이스) 설정
  database_name = aws_glue_catalog_database.silver.name
  # 데이터는 glue 외부에 존재함 원데이터는 s3에 저장되어 있음 -> 데이터가 glue 외부에 있으므로
  table_type = "EXTERNAL_TABLE"

  # 파라미터 지정
  parameters = {
    # 실 데이터가 glue 외부에 존재함을 표시
    EXTERNAL = "TRUE"
    # parquet의 압축 방식
    "parquet.compression" = "SNAPPY"
    # 파티션 활성화 (s3://버킷/silver/year=2026/....), 파티션화 되어 저장되어 있음 (partition projection)
    "projection.enabled" = "true"
    # 파티션 정보 -> year, month, day, hour -> 타입, 값 범위 지정
    # year
    "projection.year.type"  = "integer"
    "projection.year.range" = "2026,2040" # 뒤에 2040는 설정값, 2026은 현재로 가정

    # month
    # 1 -> 01, 2 -> 02 => digits = 2
    "projection.month.type"   = "integer"
    "projection.month.range"  = "1,12"
    "projection.month.digits" = "2" # 2자리수로 맞춤

    # day
    "projection.day.type"   = "integer"
    "projection.day.range"  = "1,31"
    "projection.day.digits" = "2" # 2자리수로 맞춤

    # hour
    "projection.hour.type"   = "integer"
    "projection.hour.range"  = "0,23"
    "projection.hour.digits" = "2" # 2자리수로 맞춤

    # 파티션 S3 경로 규칙
    # sql : ~ where year = '2026' ...
    # $${year} => ${year} 자체로 전달하기 위해서 앞에 $ 추가한 표현
    "storage.location.template" = "s3://${aws_s3_bucket.data.bucket}/silver/year=$${year}/month=$${month}/day=$${day}/hour=$${hour}"
  }

  # 실제 데이터가 어디에 존재, 어떤 파일 형식, 어떤 스키마를 가지는지 구성
  storage_descriptor {
    # 실제 silver 상에 s3 root 경로
    location = "s3://${aws_s3_bucket.data.bucket}/silver/"

    # s3 파일이 parquet 형식임을 알려주는
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    # parquet 내부에서 SNAPPY 압축 활용
    compressed = true

    # parquet 파일과 Glue/Athena등 테이블간 사이에서 데이터 구조 해석하는 역활
    ser_de_info {
      # 식별을 위한 이름
      name = "silver-parquet"
      # 데이터 해석을 위한 parquet ser_de
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    # silver 공통 스키마 (도메인별 동일)
    # { "schema_version":"1.0","record_type":"application_log","event_id":"a7a0a4e9-e71e-4028-b3eb-0f250bc2e713","trace_id":"2ffbd18b722f46dea9bfaf4ad6c59fce","run_id":"loggen-2684615959-10518","occurred_at":"2026-08-25T09:59:31.059+09:00","generated_at_utc":"2026-08-25T00:59:31.059+00:00","domain":"ecommerce","event_type":"product_view", ...}
    # 컬럼 1개씩 세팅 => 자동으로 세팅 (glue crawler)
    columns {
      name = "schema_version"
      type = "string"
    }
    columns {
      name = "record_type"
      type = "string"
    }
    columns {
      name = "event_id"
      type = "string"
    }
    columns {
      name = "trace_id"
      type = "string"
    }
    columns {
      name = "run_id"
      type = "string"
    }
    columns {
      name = "occurred_at"
      type = "string"
    }
    columns {
      name = "generated_at_utc"
      type = "string"
    }
    columns {
      name = "domain"
      type = "string"
    }
    columns {
      name = "event_type"
      type = "string"
    }

    # silver 중첩 스키마 ({ "":{} }) => struct
    # "service":{"name":"commerce-api","environment":"simulation","instance_id":"sim-06"}
    columns {
      name = "service"
      # struct 표기
      type = "struct<name:string,environment:string,instance_id:string>"
    }

    # client 중첩 스키마
    # "client":{"ip":"200.202.139.62","user_agent":"WhitelabelApp/4.8.1 Android","device_id":"367d6a0dffb04145"}
    columns {
      name = "client"
      type = "struct<ip:string,user_agent:string,device_id:string>"
    }

    # request 중첩 스키마
    # "request":{"method":"GET","path":"/api/products/prd_83053","request_bytes":746}0f250bc2e713
    columns {
      name = "request"
      type = "struct<method:string,path:string,request_bytes:bigint>"
    }

    # response 중첩 스키마
    # "response":{"status_code":200,"latency_ms":35,"response_bytes":16686}
    columns {
      name = "response"
      type = "struct<status_code:int,latency_ms:bigint,response_bytes:bigint>"
    }

    # data 중첩 스키마 => 도메인별로 상이=> 모든 도메인의 키를 등록
    # "data":{"user_id":"usr_163397","session_id":"b297a82569a645bc841c","product_id":"prd_83053","category":"home","quantity":1,"unit_price":274300,"currency":"KRW","campaign":"retargeting"}
    columns {
      name = "data"
      type = "struct<user_id:string,session_id:string,product_id:string,category:string,quantity:bigint,unit_price:bigint,currency:string,campaign:string,keyword:string,result_count:bigint,order_id:string,total_amount:bigint,payment_method:string,payment_result:string,transaction_id:string,customer_id:string,account_id:string,channel:string,risk_score:double,amount:bigint,merchant_id:string,merchant_category:string,authorization_result:string,destination_bank:string,destination_account_token:string,transfer_result:string,balance:bigint,auth_method:string,login_result:string,player_id:string,server_region:string,player_level:bigint,ping_ms:bigint,platform:string,match_id:string,mode:string,party_size:bigint,result:string,score:bigint,duration_seconds:bigint,item_id:string,currency_type:string,purchase_result:string,quest_id:string,reward_xp:bigint,reward_gold:bigint,plant_id:string,line_id:string,equipment_id:string,equipment_type:string,message_id:string,temperature_c:double,vibration_mm_s:double,pressure_bar:double,rpm:bigint,state:string,runtime_seconds:bigint,lot_id:string,sample_size:bigint,defect_count:bigint,quality_result:string,alarm_code:string,severity:string,acknowledged:boolean,maintenance_type:string,technician_id:string,downtime_minutes:bigint>"
    }

    # 실버표기
    # "_silver":{"layer":"silver","processor":"apache-flink","schema_version":"1.0","processed_at":"2026-08-25T00:59:31.871588+00:00"}
    columns {
      name = "_silver"
      type = "struct<layer:string,processor:string,schema_version:string,processed_at:string>"
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