# 목표
- 실버에서 골드로 파이프라인 구성중 기점으로 lambda 사용
    - 실시간 관점에서는 flink를 거치는게 적절함.
- 구성 조합
    - bronze -> flink/lambda -> Silver : 신뢰할수 있는 데이터를 필터링/구성
        - 데이터 클리닝 작업 -> 레코드 단위로 stream processing 처리(flink 관점)
    - `silver -> flink/lambda -> Gold` : 데이터를 사용할 수 있게 구성 (만든다)
         비즈니스 목적에 맞게 변환 처리
            - flink : 실시간 처리
            - lambda : 이볜트 드라이븐 처리 (실습상 s3에 업로드 이벤트 등 활용 or silver-kinesis에서 lambda로 바로 전송(실시간성 살리는컨셉))

# 목표 시스템
```
Bronze
 JSON/GZIP
    ↓
 Kinesis
    ↓
  Flink
    ↓
Silver Kinesis
    │
    ├── 기존 Firehose
    │       ↓
    │   Parquet
    │       ↓
    │   S3 silver/
    │
    └── [추가] Lambda : 의도적으로 Silver Kinesis에서 이미 정제된 데이터를 실시간으로 받아서 실시간 파이프라인 흐름 유지
              ↓
         비즈니스 가공 (분석용 데이터로 구성, 집계, 통계, ...) -> pandas / polars / spark
              ↓
         Gold Kinesis
              ↓
          Firehose
              ↓
       Glue Schema 참조
              ↓
       Parquet + SNAPPY
              ↓
          S3 gold/
              ↓
         Glue / Athena
```


# 인프라 및 코드 구성
- lambda/lambda_function.py 신규
- infra/gold-lambda.py 신규
- infra/glue-gold.py 신규
- infra/outputs.tf 내용 추가
- lambda 서비스 배포 작업 (필요한 추가파일등 고려)