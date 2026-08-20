# 개요
- Bronze (raw 데이터 저장, 모은 단위 중요)
  - log generator => kinesis => firehose(1Mib/60s) => s3 bronze (raw data, GZIP)
- Silver (raw 데이터 -> 정제/전처리등 데이터 조작 -> 저장)
  - Streaming Ingestion => `Streamning Processing + Medalion Archetecher`
  - step 1
    - log generator => kinesis(input) => flink(자바,파이썬(pyflink), pom.xml,maven) => kinesis(outut) => firehose => s3 silver
  - step 2
    - log generator => kinesis(input) => lambda => kinesis(outut) => firehose => s3 silver

# Flink
- 실시간으로 스트리밍 데이터에서 실행 가능한 분석 정보를 확보
    - 실시간 데이터를 전처리/정제등 작업 가능 -> 거의 지연 없다

- 실시간일 필요 없다면 -> Airflow or step Function(AWS) 이용하여 Batch Processing 처리
- silver layer에 저장하는 방법
    - 실시간 -> fling, lambda
    - 배치   -> Airflow or step Fucntion(AWS)